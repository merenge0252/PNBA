import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """毎テスト新しいデータディレクトリで app を読み込み直す。"""
    monkeypatch.setenv("PNBA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PNBA_PASSWORD", "")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("PNBA_DISCORD_WEBHOOK_URL", raising=False)
    import app.config
    importlib.reload(app.config)
    for name in ("db", "settings", "llm", "collect", "fetch", "curate", "notify", "pipeline", "scheduler", "auth",
                 "web"):
        mod = importlib.import_module(f"app.{name}")
        importlib.reload(mod)
    import app.db
    app.db.init()
    return tmp_path
