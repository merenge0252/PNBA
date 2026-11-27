import importlib
import re

import pytest
from fastapi.testclient import TestClient


def _client(env, monkeypatch, password=""):
    import app.config
    monkeypatch.setattr(app.config, "PASSWORD", password)
    import app.web
    return TestClient(app.web.create_app(start_scheduler=False))


def _csrf(html):
    return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)


def _seed():
    from app import db
    db.save_articles([{"id": "a1", "url": "https://e.com/1", "title": "t1", "headline": "見出し<script>", "category": "AI",
                       "source": "s", "facts": "事実", "why_me": "理由", "score": 90, "top": True},
                      {"id": "a2", "url": "https://e.com/2", "title": "t2", "headline": "二本目", "category": "お金",
                       "source": "s", "score": 50}], db.today())


def test_index_and_feedback(env, monkeypatch):
    with _client(env, monkeypatch) as c:
        _seed()
        r = c.get("/")
        assert r.status_code == 200 and "見出し&lt;script&gt;" in r.text and "まず読む" in r.text
        assert "Content-Security-Policy" in r.headers
        token = _csrf(r.text)
        assert c.post("/api/feedback/a1", json={"value": "up"}).status_code == 403  # CSRF 無し
        r = c.post("/api/feedback/a1", json={"value": "up"}, headers={"X-CSRF-Token": token})
        assert r.json() == {"id": "a1", "feedback": "up"}
        assert c.post("/api/feedback/zz", json={"value": "up"}, headers={"X-CSRF-Token": token}).status_code == 404
        assert c.post("/api/feedback/a1", json={"value": "x"}, headers={"X-CSRF-Token": token}).status_code == 400
        r = c.get("/archive?feedback=up")
        assert "見出し" in r.text and "二本目" not in r.text
        assert "二本目" in c.get("/archive?q=二本").text


def test_login_required(env, monkeypatch):
    with _client(env, monkeypatch, password="s3cret") as c:
        r = c.get("/", follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login"
        assert c.get("/healthz").status_code == 200
        assert c.post("/api/run").status_code == 401
        page = c.get("/login")
        token = _csrf(page.text)
        r = c.post("/login", data={"password": "wrong", "csrf": token})
        assert "パスワードが違います" in r.text
        r = c.post("/login", data={"password": "s3cret", "csrf": token}, follow_redirects=False)
        assert r.status_code == 303
        assert c.get("/").status_code == 200


def test_login_lockout(env, monkeypatch):
    with _client(env, monkeypatch, password="s3cret") as c:
        token = _csrf(c.get("/login").text)
        for _ in range(5):
            c.post("/login", data={"password": "bad", "csrf": token})
        r = c.post("/login", data={"password": "s3cret", "csrf": token})
        assert "15分" in r.text


def test_settings_save(env, monkeypatch):
    from app import settings
    with _client(env, monkeypatch) as c:
        r = c.get("/settings")
        token = _csrf(r.text)
        assert "あなたの関心" in r.text
        form = {"csrf": token, "interests": "猫", "per_day": "5", "run_time": "06:15", "llm": "auto",
                "schedule_enabled": "1", "discord_webhook": "",
                "sources": '{"categories": {"猫": {"about": "猫", "google_news": ["猫"]}}}'}
        r = c.post("/settings", data=form, follow_redirects=False)
        assert r.status_code == 303
        assert settings.get("interests") == "猫" and settings.get("per_day") == 5
        r = c.post("/settings", data={**form, "run_time": "99:99", "interests": "犬"})
        assert "HH:MM" in r.text and "犬" in r.text
        assert settings.get("interests") == "猫"
        assert c.post("/settings", data={**form, "csrf": "bad"}).status_code == 403


def test_run_endpoint(env, monkeypatch):
    import app.pipeline
    started = []
    monkeypatch.setattr(app.pipeline, "run", lambda trigger: started.append(trigger))
    with _client(env, monkeypatch) as c:
        token = _csrf(c.get("/").text)
        assert c.post("/api/run", headers={"X-CSRF-Token": token}).json() == {"status": "started"}
        assert c.get("/api/status").json()["running"] is False


def test_serve_refuses_public_without_password(env, monkeypatch):
    import app.__main__ as m
    import app.config
    monkeypatch.setattr(app.config, "PASSWORD", "")
    with pytest.raises(SystemExit):
        m.main(["serve", "--host", "0.0.0.0"])


def test_logout_requires_csrf(env, monkeypatch):
    with _client(env, monkeypatch, password="s3cret") as c:
        token = _csrf(c.get("/login").text)
        c.post("/login", data={"password": "s3cret", "csrf": token})
        assert c.post("/logout", data={"csrf": "bad"}).status_code == 403
        assert c.get("/", follow_redirects=False).status_code == 200
        c.post("/logout", data={"csrf": _csrf(c.get("/").text)})
        assert c.get("/", follow_redirects=False).status_code == 303
