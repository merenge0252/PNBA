"""収集 → 選定 → 保存 → 通知 の1回分。"""
from concurrent.futures import ThreadPoolExecutor

from . import curate, db, notify, settings
from .collect import collect
from .fetch import fetch_body
from .log import log


def run(trigger="manual", dry_run=False):
    """1回実行して、選んだ記事のリストを返す。

    trigger="schedule" のときは、自動配信が止められている日・今日の分がもう成功している日は何もせず None を返す。
    dry_run は保存も通知もしない。
    """
    day = db.today()
    if not dry_run:
        db.init()
        settings.seed()
        db.mark_stale_runs()
        if trigger == "schedule":
            if not settings.get("schedule_enabled"):
                log("[run] 自動配信は止められています")
                return None
            if db.succeeded_on(day):
                log("[run] 今日の分は配信済み")
                return None
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
        cands = curate.shortlist(arts, ctx, s["sources"])
        log(f"[run] 候補 {len(cands)}本")
        if not cands:
            if run_id:
                db.finish_run(run_id, "empty", collected, 0, "候補が0本でした")
            return []
        with ThreadPoolExecutor(8) as pool:
            cands = list(pool.map(fetch_body, cands))
        log(f"[run] 本文あり {sum(bool(a.get('body')) for a in cands)}本")
        picks = curate.finalize(cands, ctx, s["sources"], int(s["per_day"]))
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
