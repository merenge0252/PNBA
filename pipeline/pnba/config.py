"""設定（環境変数）。GitHub Actions では Secrets から渡す。"""
import os
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_DIR = REPO_ROOT / "shared"
SCHEMA_SQL = SHARED_DIR / "schema.sql"
DEFAULTS_DIR = SHARED_DIR / "defaults"


def _load_dotenv(path: Path) -> None:
    """ローカル実行用の簡易 .env 読み込み（設定済みの環境変数は上書きしない）。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(REPO_ROOT / ".env")
_load_dotenv(REPO_ROOT / ".env.local")


def _env(name, default=""):
    v = os.environ.get(name, "")
    return v.strip() if v.strip() else default


DATABASE_URL = _env("DATABASE_URL") or _env("POSTGRES_URL")
TZ = ZoneInfo(_env("PNBA_TZ", "Asia/Tokyo"))

GEMINI_API_KEY = _env("GEMINI_API_KEY")
GEMINI_MODEL = _env("PNBA_GEMINI_MODEL", "gemini-flash-latest")
LLM_TIMEOUT = int(_env("PNBA_LLM_TIMEOUT", "300"))

DISCORD_WEBHOOK_URL = _env("PNBA_DISCORD_WEBHOOK_URL")
PUBLIC_URL = _env("PNBA_PUBLIC_URL")

WINDOW_H = 48          # 何時間以内の記事を集めるか
SHORTLIST = 30         # 1段目で残す候補数
BODY_CHARS = 3500      # 2段目に渡す本文の長さ
MAX_LISTING = 400      # 1段目に渡す記事数の上限
