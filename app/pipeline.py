"""収集 → 選定 → 保存 → 通知 の1回分。"""
import threading
from concurrent.futures import ThreadPoolExecutor

from . import curate, db, notify, settings
from .collect import collect
from .fetch import fetch_body
from .log import log

_running = threading.Lock()


def is_running():
    return _running.locked()


def run(trigger="manual", dry_run=False):
    """1回実行して、選んだ記事のリストを返す。既に実行中なら None。dry_run は保存も通知もしない。"""
    if not _running.acquire(blocking=False):
        log("[run] 既に実行中")
        return None
    day = db.today()
    run_id = None if dry_run else db.start_run(day, trigger)
    collected = 0
    try:
        s = settings.load()
        seen = db.seen_urls()
        arts = [a for a in collect(s["sources"]) if a["url"] not in seen]
        collected = len(arts)
        log(f"[run] 収集 {collected}件（配信済みを除く）")
        if not arts:
            if run_id:
                db.finish_run(run_id, "empty", 0, 0, "新しい記事がありません")
            return []
        ctx = curate.user_context(s["interests"])
        cands = curate.shortlist(arts, ctx, s["sources"], s["llm"])
        log(f"[run] 候補 {len(cands)}本")
        if not cands:
            if run_id:
                db.finish_run(run_id, "empty", collected, 0, "候補が0本でした")
            return []
        with ThreadPoolExecutor(8) as pool:
            cands = list(pool.map(fetch_body, cands))
        log(f"[run] 本文あり {sum(bool(a.get('body')) for a in cands)}本")
        picks = curate.finalize(cands, ctx, s["sources"], int(s["per_day"]), s["llm"])
        if dry_run:
            return picks
        db.save_articles(picks, day)
        db.mark_seen(u for p in picks for u in (p["url"], p.get("gnews_url")))
        notify.send(picks, day, s["discord_webhook"])
        db.finish_run(run_id, "ok" if picks else "empty", collected, len(picks))
        log(f"[run] 配信 {len(picks)}本")
        return picks
    except Exception as e:
        log(f"[run] 失敗: {e}")
        if run_id:
            db.finish_run(run_id, "error", collected, 0, str(e))
        raise
    finally:
        _running.release()
