"""毎朝の定時実行。アプリ内のスレッドで1分ごとに確認し、止まっていた日は起動後に回収する。"""
import datetime
import threading

from . import config, db, pipeline, settings
from .log import log

MAX_TRIES = 3
RETRY_MIN = 30


def due(now=None):
    """今日の分がまだで、配信時刻を過ぎていれば True。失敗は30分おきに3回まで再試行。"""
    now = now or datetime.datetime.now(config.TZ)
    if not settings.get("schedule_enabled"):
        return False
    hh, mm = map(int, settings.get("run_time").split(":"))
    if (now.hour, now.minute) < (hh, mm):
        return False
    day = now.date().isoformat()
    if db.succeeded_on(day):
        return False
    tries = [r for r in db.last_runs(20) if r["day"] == day and r["trigger"] == "schedule"]
    if len(tries) >= MAX_TRIES:
        return False
    if tries:
        last = datetime.datetime.fromisoformat(tries[0]["started_at"])
        if now - last < datetime.timedelta(minutes=RETRY_MIN):
            return False
    return True


class Scheduler:
    def __init__(self, interval=60):
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, name="pnba-scheduler", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        wait = 5  # 起動直後に一度確認する（止まっていた日の回収）
        while not self._stop.wait(wait):
            wait = self.interval
            try:
                if not pipeline.is_running() and due():
                    log("[schedule] 定時実行を開始")
                    pipeline.run(trigger="schedule")
            except Exception as e:
                log(f"[schedule] 失敗: {e}")
