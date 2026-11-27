"""パスワードログイン・CSRF・ログイン試行の制限。"""
import hmac
import secrets
import threading
import time

from . import config

MAX_FAILS = 5
LOCK_SEC = 15 * 60
_fails = {}
_fails_lock = threading.Lock()


def auth_enabled():
    return bool(config.PASSWORD)


def secret_key():
    """Cookie の署名鍵。PNBA_SECRET_KEY が無ければ data/secret_key に作って使い回す。"""
    import os
    if os.environ.get("PNBA_SECRET_KEY"):
        return os.environ["PNBA_SECRET_KEY"]
    config.ensure_dirs()
    f = config.SECRET_KEY_FILE
    if not f.exists():
        f.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        try:
            f.chmod(0o600)
        except OSError:
            pass
    return f.read_text(encoding="utf-8").strip()


def check_password(pw):
    return hmac.compare_digest((pw or "").encode("utf-8"), config.PASSWORD.encode("utf-8"))


def locked(ip, now=None):
    now = now or time.time()
    with _fails_lock:
        n, since = _fails.get(ip, (0, now))
        if now - since > LOCK_SEC:
            _fails.pop(ip, None)
            return False
        return n >= MAX_FAILS


def record_fail(ip, now=None):
    now = now or time.time()
    with _fails_lock:
        n, since = _fails.get(ip, (0, now))
        if now - since > LOCK_SEC:
            n, since = 0, now
        _fails[ip] = (n + 1, since)


def clear_fails(ip):
    with _fails_lock:
        _fails.pop(ip, None)


def csrf_token(session):
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]


def csrf_ok(session, token):
    return bool(token) and "csrf" in session and hmac.compare_digest(session["csrf"], token)
