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
    from pnba.collect import parse_feed
    arts = parse_feed(feedparser.parse(RSS.format(now=_now_rfc())), "src", "AI")
    assert [a["url"] for a in arts] == ["https://news.google.com/rss/articles/abc", "https://example.com/a"]
    g, a = arts
    assert g["title"] == "新しい記事" and g["publisher"] == "日経" and g["desc"] == ""
    assert a["desc"] == "本文の 説明" and a["category"] == "AI"


def test_parse_trending(env):
    from pnba.collect import parse_trending
    html = """<article class="Box-row"><h2><a href="/foo/llm-kit">foo / llm-kit</a></h2><p>An LLM toolkit</p></article>
              <article class="Box-row"><h2><a href="/bar/game">bar / game</a></h2><p>A game</p></article>"""
    arts = parse_trending(html, ["LLM"], "テック")
    assert len(arts) == 1 and arts[0]["url"] == "https://github.com/foo/llm-kit"


def test_jobs_and_dedupe(env):
    from pnba.collect import dedupe, google_news_url, jobs
    src = {
        "locale": {"hl": "en-US", "gl": "US"},
        "categories": {"A": {"rss": [{"url": "https://e.com/f"}], "google_news": ["a b"], "zenn_topics": ["py"],
                             "github_trending_keywords": ["ai"]}}}
    assert len(jobs(src)) == 4
    assert google_news_url("a b", src["locale"]).endswith("q=a%20b&hl=en-US&gl=US&ceid=US:en")
    assert len(dedupe([{"url": "u"}, {"url": "u"}, {"url": "v"}])) == 2


def test_extract_json(env):
    from pnba.llm import LLMError, extract_json
    assert extract_json('前置き ```json\n{"a": 1}\n``` 後') == {"a": 1}
    assert extract_json('xx {"urls": ["u"]} yy') == {"urls": ["u"]}
    with pytest.raises(LLMError):
        extract_json("no json")




def test_gemini_api_call(env, monkeypatch):
    from pnba import llm

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
    from pnba.curate import normalize_picks
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






def _fake_pipeline(monkeypatch, picks_urls):
    from pnba import curate, pipeline
    arts = [{"url": f"https://e.com/{i}", "title": f"t{i}", "category": "AI", "source": "s", "publisher": "p"}
            for i in range(5)]
    monkeypatch.setattr(pipeline, "collect", lambda src: arts)
    monkeypatch.setattr(pipeline, "fetch_body", lambda a: {**a, "body": "本文"})
    calls = []

    def fake_generate(prompt, data):
        calls.append(data)
        if "今日の記事一覧" in data:
            return json.dumps({"urls": [a["url"] for a in arts]})
        return json.dumps({"picks": [{"url": u, "headline": f"H{u[-1]}", "score": 50, "top": u.endswith("0")}
                                     for u in picks_urls]})

    monkeypatch.setattr(curate.llm, "generate", fake_generate)
    return calls


def test_pipeline_run_saves_and_dedupes(dbenv, monkeypatch):
    from pnba import db, pipeline
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


def test_pipeline_feedback_in_context(dbenv, monkeypatch):
    from pnba import db, pipeline
    calls = _fake_pipeline(monkeypatch, ["https://e.com/1"])
    pipeline.run()
    aid = db.articles_for_day(db.today())[0]["id"]
    assert db.set_feedback(aid, "up")
    pipeline.run()
    assert "H1" in calls[-1].split("過去に 👍 した記事")[1].split("過去に 👎")[0]


def test_pipeline_error_recorded(dbenv, monkeypatch):
    from pnba import db, pipeline
    _fake_pipeline(monkeypatch, [])
    monkeypatch.setattr(pipeline.curate, "shortlist", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        pipeline.run()
    r = db.last_runs(1)[0]
    assert r["status"] == "error" and "boom" in r["message"]


def test_dry_run_does_not_save(dbenv, monkeypatch):
    from pnba import db, pipeline
    _fake_pipeline(monkeypatch, ["https://e.com/2"])
    assert len(pipeline.run(dry_run=True)) == 1
    assert db.articles_for_day(db.today()) == [] and db.last_runs() == []




def test_notify_message(env):
    from pnba.notify import build_message
    picks = [{"headline": f"h{i}", "title": "t", "category": "A", "top": i == 0} for i in range(7)]
    msg = build_message(picks, "2026-11-27", "https://news.example/")
    assert "⭐ [A] h0" in msg and "ほか 2 本" in msg and msg.endswith("https://news.example/?day=2026-11-27")


def test_schedule_skips_when_done_or_disabled(dbenv, monkeypatch):
    from pnba import db, pipeline
    _fake_pipeline(monkeypatch, ["https://e.com/0"])
    assert pipeline.run(trigger="schedule") is not None
    assert pipeline.run(trigger="schedule") is None  # 今日の分は済んでいる
    assert len(db.last_runs()) == 1
    with db.connect() as con:
        con.execute("DELETE FROM pnba_runs")
    db.set_setting("schedule_enabled", False)
    assert pipeline.run(trigger="schedule") is None
    assert pipeline.run(trigger="manual") is not None  # 手動は止めない


def test_settings_seed_and_defaults(dbenv):
    from pnba import db, settings
    settings.seed()
    assert db.get_setting("per_day") == 12
    assert "categories" in db.get_setting("sources")
    db.set_setting("per_day", 5)
    settings.seed()
    assert settings.get("per_day") == 5  # 既存の値は上書きしない


def test_stale_runs(dbenv):
    from pnba import db
    with db.connect() as con:
        con.execute("INSERT INTO pnba_runs(day, started_at) VALUES('2026-01-01', now() - interval '3 hours')")
        con.execute("INSERT INTO pnba_runs(day) VALUES('2026-01-01')")
    db.mark_stale_runs()
    assert [r["status"] for r in db.last_runs()] == ["running", "error"]


def test_missing_database_url(env, monkeypatch):
    from pnba import config, db
    monkeypatch.setattr(config, "DATABASE_URL", "")
    with pytest.raises(db.DBError):
        db.init()


def test_missing_api_key(env, monkeypatch):
    from pnba import config, llm
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with pytest.raises(llm.LLMError):
        llm.generate("x", "y")


def test_collect_all_failed_raises(env, monkeypatch):
    from pnba import collect
    monkeypatch.setattr(collect, "_rss", lambda *a: None)
    src = {"categories": {"A": {"rss": [{"url": "https://e.com/f"}], "google_news": ["q"]}}}
    with pytest.raises(collect.CollectError):
        collect.collect(src)
    calls = iter([None, [{"url": "u", "title": "t", "category": "A", "source": "s"}]])
    monkeypatch.setattr(collect, "_rss", lambda *a: next(calls))
    assert [a["url"] for a in collect.collect(src)] == ["u"]
