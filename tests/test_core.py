import datetime
import json

import feedparser
import pytest

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>新しい記事 - 日経</title><link>https://news.google.com/rss/articles/abc</link>
<pubDate>{now}</pubDate><description>x</description></item>
<item><title>古い記事</title><link>https://example.com/old</link><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item>
<item><title>普通の記事</title><link>https://example.com/a</link><pubDate>{now}</pubDate>
<description>&lt;p&gt;本文の&lt;b&gt;説明&lt;/b&gt;&lt;/p&gt;</description></item>
</channel></rss>"""


def _now_rfc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


def test_parse_feed(env):
    from app.collect import parse_feed
    arts = parse_feed(feedparser.parse(RSS.format(now=_now_rfc())), "src", "AI")
    assert [a["url"] for a in arts] == ["https://news.google.com/rss/articles/abc", "https://example.com/a"]
    g, a = arts
    assert g["title"] == "新しい記事" and g["publisher"] == "日経" and g["desc"] == ""
    assert a["desc"] == "本文の 説明" and a["category"] == "AI"


def test_parse_trending(env):
    from app.collect import parse_trending
    html = """<article class="Box-row"><h2><a href="/foo/llm-kit">foo / llm-kit</a></h2><p>An LLM toolkit</p></article>
              <article class="Box-row"><h2><a href="/bar/game">bar / game</a></h2><p>A game</p></article>"""
    arts = parse_trending(html, ["LLM"], "テック")
    assert len(arts) == 1 and arts[0]["url"] == "https://github.com/foo/llm-kit"


def test_jobs_and_dedupe(env):
    from app.collect import dedupe, google_news_url, jobs
    src = json.loads((env.parent / "x.json").read_text()) if False else {
        "locale": {"hl": "en-US", "gl": "US"},
        "categories": {"A": {"rss": [{"url": "https://e.com/f"}], "google_news": ["a b"], "zenn_topics": ["py"],
                             "github_trending_keywords": ["ai"]}}}
    assert len(jobs(src)) == 4
    assert google_news_url("a b", src["locale"]).endswith("q=a%20b&hl=en-US&gl=US&ceid=US:en")
    assert len(dedupe([{"url": "u"}, {"url": "u"}, {"url": "v"}])) == 2


def test_extract_json(env):
    from app.llm import LLMError, extract_json
    assert extract_json('前置き ```json\n{"a": 1}\n``` 後') == {"a": 1}
    assert extract_json('xx {"urls": ["u"]} yy') == {"urls": ["u"]}
    with pytest.raises(LLMError):
        extract_json("no json")


def test_backend_selection(env, monkeypatch):
    from app import config, llm
    assert llm.backend("auto") == "gemini_api"
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "AGY_CMD", "definitely-not-installed-agy")
    with pytest.raises(llm.LLMError):
        llm.backend("auto")
    with pytest.raises(llm.LLMError):
        llm.backend("gemini_api")


def test_gemini_api_call(env, monkeypatch):
    from app import llm

    class R:
        status_code = 200

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": '{"urls": []}'}]}}]}

    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, body=json)
        return R()

    monkeypatch.setattr(llm.requests, "post", fake_post)
    assert llm.generate("指示", "材料") == '{"urls": []}'
    assert seen["headers"]["x-goog-api-key"] == "test-key" and "key=" not in seen["url"]
    assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "指示"


def test_normalize_picks(env):
    from app.curate import normalize_picks
    cands = [{"url": "https://e.com/1", "title": "t1", "category": "A", "source": "s", "body": "b", "desc": "d"},
             {"url": "https://e.com/2", "title": "t2", "category": "B", "source": "s"}]
    picks = [{"url": "https://e.com/2", "headline": "h2", "score": "70", "deadline": "2026-12-01"},
             {"url": "https://fake.example/", "headline": "作り話"},
             {"url": "https://e.com/1", "headline": "h1", "score": 999, "top": True, "deadline": "来週"},
             {"url": "https://e.com/1", "headline": "重複"}, "bad"]
    out = normalize_picks(picks, cands, 10)
    assert [p["headline"] for p in out] == ["h1", "h2"]
    assert out[0]["score"] == 100 and out[0]["deadline"] == "" and "body" not in out[0]
    assert out[1]["deadline"] == "2026-12-01" and out[1]["category"] == "B"
    assert len(normalize_picks(picks, cands, 1)) == 1


def test_settings_validation(env):
    from app import settings
    base = {"per_day": "10", "run_time": "08:30", "llm": "auto", "interests": "AI",
            "sources": json.dumps({"categories": {"A": {"about": "x", "rss": [{"url": "https://e.com/f"}]}}})}
    settings.save(base)
    assert settings.get("per_day") == 10 and settings.get("run_time") == "08:30"
    assert settings.get("schedule_enabled") is False  # チェック無し
    for bad in ({"run_time": "25:00"}, {"per_day": "0"}, {"llm": "x"}, {"sources": "{"},
                {"sources": '{"categories": {}}'}, {"sources": '{"categories": {"A": {"rss": [{"url": "file:///etc"}]}}}'},
                {"discord_webhook": "https://evil.example/hook"}):
        with pytest.raises(settings.SettingsError):
            settings.save({**base, **bad})


def test_default_settings_are_valid(env):
    from app import settings
    settings.validate_sources(settings.defaults()["sources"])


def _fake_pipeline(monkeypatch, picks_urls):
    from app import curate, pipeline
    arts = [{"url": f"https://e.com/{i}", "title": f"t{i}", "category": "AI", "source": "s", "publisher": "p"}
            for i in range(5)]
    monkeypatch.setattr(pipeline, "collect", lambda src: arts)
    monkeypatch.setattr(pipeline, "fetch_body", lambda a: {**a, "body": "本文"})
    calls = []

    def fake_generate(prompt, data, choice="auto"):
        calls.append(data)
        if "今日の記事一覧" in data:
            return json.dumps({"urls": [a["url"] for a in arts]})
        return json.dumps({"picks": [{"url": u, "headline": f"H{u[-1]}", "score": 50, "top": u.endswith("0")}
                                     for u in picks_urls]})

    monkeypatch.setattr(curate.llm, "generate", fake_generate)
    return calls


def test_pipeline_run_saves_and_dedupes(env, monkeypatch):
    from app import db, pipeline
    calls = _fake_pipeline(monkeypatch, ["https://e.com/0", "https://e.com/3"])
    picks = pipeline.run(trigger="manual")
    assert [p["headline"] for p in picks] == ["H0", "H3"]
    day = db.today()
    assert [a["headline"] for a in db.articles_for_day(day)] == ["H0", "H3"]
    assert db.succeeded_on(day)
    assert "https://e.com/0" in db.seen_urls()
    # 2回目は配信済みが一覧から外れる
    pipeline.run(trigger="manual")
    assert "https://e.com/0" not in calls[-2]


def test_pipeline_feedback_in_context(env, monkeypatch):
    from app import db, pipeline
    calls = _fake_pipeline(monkeypatch, ["https://e.com/1"])
    pipeline.run()
    aid = db.articles_for_day(db.today())[0]["id"]
    assert db.set_feedback(aid, "up")
    pipeline.run()
    assert "H1" in calls[-1].split("過去に 👍 した記事")[1].split("過去に 👎")[0]


def test_pipeline_error_recorded(env, monkeypatch):
    from app import db, pipeline
    _fake_pipeline(monkeypatch, [])
    monkeypatch.setattr(pipeline.curate, "shortlist", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        pipeline.run()
    r = db.last_runs(1)[0]
    assert r["status"] == "error" and "boom" in r["message"]
    assert not pipeline.is_running()


def test_dry_run_does_not_save(env, monkeypatch):
    from app import db, pipeline
    _fake_pipeline(monkeypatch, ["https://e.com/2"])
    assert len(pipeline.run(dry_run=True)) == 1
    assert db.articles_for_day(db.today()) == [] and db.last_runs() == []


def test_scheduler_due(env, monkeypatch):
    from app import config, db, scheduler, settings
    db.set_setting("run_time", "07:00")
    day = datetime.datetime(2026, 11, 27, tzinfo=config.TZ)
    assert not scheduler.due(day.replace(hour=6, minute=59))
    assert scheduler.due(day.replace(hour=7))
    # 失敗後30分は待つ、3回で諦める
    with db.connect() as con:
        con.execute("INSERT INTO runs(started_at, day, trigger, status) VALUES(?, '2026-11-27', 'schedule', 'error')",
                    (day.replace(hour=7).isoformat(),))
    assert not scheduler.due(day.replace(hour=7, minute=10))
    assert scheduler.due(day.replace(hour=7, minute=31))
    db.set_setting("schedule_enabled", False)
    assert not scheduler.due(day.replace(hour=9))
    db.set_setting("schedule_enabled", True)
    with db.connect() as con:
        con.execute("INSERT INTO runs(started_at, day, trigger, status) VALUES(?, '2026-11-27', 'manual', 'ok')",
                    (day.replace(hour=8).isoformat(),))
    assert not scheduler.due(day.replace(hour=9))


def test_notify_message(env):
    from app.notify import build_message
    picks = [{"headline": f"h{i}", "title": "t", "category": "A", "top": i == 0} for i in range(7)]
    msg = build_message(picks, "2026-11-27", "https://news.example/")
    assert "⭐ [A] h0" in msg and "ほか 2 本" in msg and msg.endswith("https://news.example/?day=2026-11-27")
