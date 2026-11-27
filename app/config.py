"""設定（環境変数）。秘密の値は環境変数か .env にだけ置き、DB やリポジトリには入れない。"""
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """依存を増やさない簡易 .env 読み込み（既に設定済みの環境変数は上書きしない）。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.environ.get("PNBA_DATA_DIR", ROOT / "data")).resolve()
DB_PATH = DATA_DIR / "pnba.sqlite3"
WORK_DIR = DATA_DIR / "work"
EXAMPLES_DIR = ROOT / "examples"

TZ = ZoneInfo(os.environ.get("PNBA_TZ", "Asia/Tokyo"))

# AI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("PNBA_GEMINI_MODEL", "gemini-flash-latest")
AGY_CMD = os.environ.get("PNBA_AGY_CMD", "agy")
AGY_MODEL = os.environ.get("PNBA_AGY_MODEL", "")
LLM_TIMEOUT = int(os.environ.get("PNBA_LLM_TIMEOUT", "600"))

# Web
HOST = os.environ.get("PNBA_HOST", "127.0.0.1")
PORT = int(os.environ.get("PNBA_PORT", "8000"))
PASSWORD = os.environ.get("PNBA_PASSWORD", "")
SECRET_KEY_FILE = DATA_DIR / "secret_key"
def _flag(name):
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


SECURE_COOKIE = _flag("PNBA_SECURE_COOKIE")
TRUST_PROXY = _flag("PNBA_TRUST_PROXY")

# 通知（設定画面の値より優先）
DISCORD_WEBHOOK_URL = os.environ.get("PNBA_DISCORD_WEBHOOK_URL", "")
PUBLIC_URL = os.environ.get("PNBA_PUBLIC_URL", "")

# 選定
WINDOW_H = 48          # 何時間以内の記事を集めるか
SHORTLIST = 30         # 1段目で残す候補数
BODY_CHARS = 3500      # 2段目に渡す本文の長さ
MAX_LISTING = 400      # 1段目に渡す記事数の上限


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)


def is_local_host(host: str) -> bool:
    return host in ("127.0.0.1", "localhost", "::1")
