"""SQLite。記事・配信履歴・フィードバック・設定・実行記録。"""
import datetime
import json
import sqlite3
import threading
from contextlib import contextmanager

from . import config

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id          TEXT PRIMARY KEY,
    day         TEXT NOT NULL,
    url         TEXT NOT NULL,
    gnews_url   TEXT NOT NULL DEFAULT '',
    title       TEXT NOT NULL,
    headline    TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT '',
    source      TEXT NOT NULL DEFAULT '',
    publisher   TEXT NOT NULL DEFAULT '',
    published   TEXT NOT NULL DEFAULT '',
    facts       TEXT NOT NULL DEFAULT '',
    why_me      TEXT NOT NULL DEFAULT '',
    action      TEXT NOT NULL DEFAULT '',
    deadline    TEXT NOT NULL DEFAULT '',
    score       INTEGER NOT NULL DEFAULT 0,
    top         INTEGER NOT NULL DEFAULT 0,
    feedback    TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS articles_day ON articles(day);
CREATE TABLE IF NOT EXISTS seen_urls (
    url         TEXT PRIMARY KEY,
    seen_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    day         TEXT NOT NULL,
    trigger     TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'running',
    collected   INTEGER NOT NULL DEFAULT 0,
    picked      INTEGER NOT NULL DEFAULT 0,
    message     TEXT NOT NULL DEFAULT ''
);
"""


def now_iso() -> str:
    return datetime.datetime.now(config.TZ).isoformat(timespec="seconds")


def today() -> str:
    return datetime.datetime.now(config.TZ).date().isoformat()


@contextmanager
def connect():
    config.ensure_dirs()
    with _lock:
        con = sqlite3.connect(config.DB_PATH)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()


def init() -> None:
    with connect() as con:
        con.executescript(SCHEMA)


# ---------- 設定 ----------

def get_setting(key, default=None):
    with connect() as con:
        r = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return json.loads(r["value"]) if r else default


def set_setting(key, value) -> None:
    with connect() as con:
        con.execute("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, json.dumps(value, ensure_ascii=False)))


# ---------- 配信履歴 ----------

def seen_urls() -> set:
    with connect() as con:
        return {r["url"] for r in con.execute("SELECT url FROM seen_urls")}


def mark_seen(urls) -> None:
    ts = now_iso()
    with connect() as con:
        con.executemany("INSERT OR IGNORE INTO seen_urls(url, seen_at) VALUES(?, ?)", [(u, ts) for u in urls if u])
        # 古い履歴は捨てる（RSS は 48 時間分しか見ないので十分）
        con.execute("DELETE FROM seen_urls WHERE url NOT IN (SELECT url FROM seen_urls ORDER BY seen_at DESC LIMIT 20000)")


# ---------- 記事 ----------

ARTICLE_FIELDS = ("id", "day", "url", "gnews_url", "title", "headline", "category", "source", "publisher", "published",
                  "facts", "why_me", "action", "deadline", "score", "top")


def save_articles(picks, day) -> None:
    ts = now_iso()
    with connect() as con:
        for p in picks:
            row = {k: p.get(k, "") for k in ARTICLE_FIELDS}
            row.update(day=day, score=int(p.get("score") or 0), top=1 if p.get("top") else 0, created_at=ts)
            cols = ", ".join(row)
            con.execute(f"INSERT INTO articles({cols}) VALUES({', '.join('?' * len(row))}) "
                        f"ON CONFLICT(id) DO NOTHING", tuple(row.values()))


def _row(r):
    d = dict(r)
    d["top"] = bool(d["top"])
    return d


def articles_for_day(day):
    with connect() as con:
        rows = con.execute("SELECT * FROM articles WHERE day=? ORDER BY top DESC, score DESC", (day,)).fetchall()
    return [_row(r) for r in rows]


def article_days(limit=60):
    with connect() as con:
        rows = con.execute("SELECT day, COUNT(*) n FROM articles GROUP BY day ORDER BY day DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]


def search_articles(feedback="", category="", q="", limit=200):
    sql, args = "SELECT * FROM articles WHERE 1=1", []
    if feedback:
        sql += " AND feedback=?"
        args.append(feedback)
    if category:
        sql += " AND category=?"
        args.append(category)
    if q:
        sql += " AND (headline LIKE ? OR title LIKE ? OR facts LIKE ?)"
        args += [f"%{q}%"] * 3
    sql += " ORDER BY day DESC, top DESC, score DESC LIMIT ?"
    args.append(limit)
    with connect() as con:
        return [_row(r) for r in con.execute(sql, args)]


def categories():
    with connect() as con:
        return [r["category"] for r in con.execute("SELECT DISTINCT category FROM articles ORDER BY category")]


def get_article(aid):
    with connect() as con:
        r = con.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
    return _row(r) if r else None


def set_feedback(aid, value) -> bool:
    if value not in ("up", "down", ""):
        raise ValueError(value)
    with connect() as con:
        cur = con.execute("UPDATE articles SET feedback=? WHERE id=?", (value, aid))
        return cur.rowcount > 0


def feedback_examples(n=15):
    """過去の 👍/👎 のタイトルを新しい順に n 件ずつ。"""
    with connect() as con:
        ups = [r[0] for r in con.execute(
            "SELECT COALESCE(NULLIF(headline,''), title) FROM articles WHERE feedback='up' ORDER BY day DESC LIMIT ?", (n,))]
        downs = [r[0] for r in con.execute(
            "SELECT COALESCE(NULLIF(headline,''), title) FROM articles WHERE feedback='down' ORDER BY day DESC LIMIT ?", (n,))]
    return ups, downs


# ---------- 実行記録 ----------

def start_run(day, trigger) -> int:
    with connect() as con:
        cur = con.execute("INSERT INTO runs(started_at, day, trigger) VALUES(?, ?, ?)", (now_iso(), day, trigger))
        return cur.lastrowid


def finish_run(run_id, status, collected=0, picked=0, message="") -> None:
    with connect() as con:
        con.execute("UPDATE runs SET finished_at=?, status=?, collected=?, picked=?, message=? WHERE id=?",
                    (now_iso(), status, collected, picked, message[:2000], run_id))


def last_runs(n=10):
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (n,))]


def succeeded_on(day) -> bool:
    """その日の定時実行が成功（0件含む）したか。"""
    with connect() as con:
        r = con.execute("SELECT 1 FROM runs WHERE day=? AND status IN ('ok','empty') LIMIT 1", (day,)).fetchone()
    return r is not None


def mark_stale_runs() -> None:
    """前回プロセスが落ちて running のまま残った実行を失敗扱いにする。"""
    with connect() as con:
        con.execute("UPDATE runs SET status='error', message='中断された', finished_at=? WHERE status='running'",
                    (now_iso(),))
