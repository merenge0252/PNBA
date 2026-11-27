"""Postgres（Neon など）。Web と同じテーブルを使う。"""
import datetime
import json
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import config


class DBError(RuntimeError):
    pass


def now():
    return datetime.datetime.now(config.TZ)


def today() -> str:
    return now().date().isoformat()


@contextmanager
def connect():
    if not config.DATABASE_URL:
        raise DBError("DATABASE_URL が設定されていません（GitHub の Secrets に入れてください）")
    # prepare_threshold=None: Neon の接続プーラー（PgBouncer）でも動くように
    with psycopg.connect(config.DATABASE_URL, row_factory=dict_row, prepare_threshold=None,
                         connect_timeout=30) as con:
        yield con


def init() -> None:
    with connect() as con:
        con.execute(config.SCHEMA_SQL.read_text(encoding="utf-8"))


# ---------- 設定 ----------

def get_setting(key, default=None):
    with connect() as con:
        r = con.execute("SELECT value FROM pnba_settings WHERE key=%s", (key,)).fetchone()
    return r["value"] if r else default


def set_setting(key, value) -> None:
    with connect() as con:
        con.execute("INSERT INTO pnba_settings(key, value) VALUES(%s, %s) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, Jsonb(value)))


# ---------- 配信履歴 ----------

def seen_urls() -> set:
    with connect() as con:
        return {r["url"] for r in con.execute("SELECT url FROM pnba_seen_urls")}


def mark_seen(urls) -> None:
    urls = [u for u in urls if u]
    with connect() as con:
        with con.cursor() as cur:
            cur.executemany("INSERT INTO pnba_seen_urls(url) VALUES(%s) ON CONFLICT DO NOTHING", [(u,) for u in urls])
        # 古い履歴は捨てる（RSS は 48 時間分しか見ないので十分）
        con.execute("DELETE FROM pnba_seen_urls WHERE seen_at < now() - interval '60 days'")


# ---------- 記事 ----------

ARTICLE_FIELDS = ("id", "url", "gnews_url", "title", "headline", "category", "source", "publisher", "published",
                  "facts", "why_me", "action", "deadline")


def save_articles(picks, day) -> None:
    with connect() as con:
        with con.cursor() as cur:
            for p in picks:
                row = {k: str(p.get(k) or "") for k in ARTICLE_FIELDS}
                row.update(day=day, score=int(p.get("score") or 0), top=bool(p.get("top")))
                cols = ", ".join(row)
                cur.execute(f"INSERT INTO pnba_articles({cols}) VALUES({', '.join(['%s'] * len(row))}) "
                            f"ON CONFLICT(id) DO NOTHING", tuple(row.values()))


def articles_for_day(day):
    with connect() as con:
        return con.execute("SELECT * FROM pnba_articles WHERE day=%s ORDER BY top DESC, score DESC",
                           (day,)).fetchall()


def set_feedback(aid, value) -> bool:
    if value not in ("up", "down", ""):
        raise ValueError(value)
    with connect() as con:
        return con.execute("UPDATE pnba_articles SET feedback=%s WHERE id=%s", (value, aid)).rowcount > 0


def feedback_examples(n=15):
    """過去の 👍/👎 の見出しを新しい順に n 件ずつ。"""
    q = ("SELECT COALESCE(NULLIF(headline,''), title) AS t FROM pnba_articles WHERE feedback=%s "
         "ORDER BY day DESC, created_at DESC LIMIT %s")
    with connect() as con:
        ups = [r["t"] for r in con.execute(q, ("up", n))]
        downs = [r["t"] for r in con.execute(q, ("down", n))]
    return ups, downs


# ---------- 実行記録 ----------

def start_run(day, trigger) -> int:
    with connect() as con:
        return con.execute("INSERT INTO pnba_runs(day, trigger) VALUES(%s, %s) RETURNING id",
                           (day, trigger)).fetchone()["id"]


def finish_run(run_id, status, collected=0, picked=0, message="") -> None:
    with connect() as con:
        con.execute("UPDATE pnba_runs SET finished_at=now(), status=%s, collected=%s, picked=%s, message=%s "
                    "WHERE id=%s", (status, collected, picked, message[:2000], run_id))


def last_runs(n=10):
    with connect() as con:
        return con.execute("SELECT * FROM pnba_runs ORDER BY id DESC LIMIT %s", (n,)).fetchall()


def succeeded_on(day) -> bool:
    """その日の実行が成功（新着なしを含む）したか。"""
    with connect() as con:
        return con.execute("SELECT 1 FROM pnba_runs WHERE day=%s AND status IN ('ok','empty') LIMIT 1",
                           (day,)).fetchone() is not None


def mark_stale_runs(hours=2) -> None:
    """途中で落ちて running のまま残った実行を失敗扱いにする。"""
    with connect() as con:
        con.execute("UPDATE pnba_runs SET status='error', message='中断された', finished_at=now() "
                    "WHERE status='running' AND started_at < now() - make_interval(hours => %s)", (hours,))


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, default=str)
