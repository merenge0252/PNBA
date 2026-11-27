"""テストは本物の Postgres を使う。TEST_DATABASE_URL が無ければ DB を使うテストは飛ばす。"""
import importlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEST_DB = os.environ.get("TEST_DATABASE_URL", "")
TABLES = ("pnba_articles", "pnba_seen_urls", "pnba_settings", "pnba_runs", "pnba_login_attempts")


@pytest.fixture()
def env(monkeypatch):
    """毎テスト設定を読み込み直し、DB を空にする。"""
    monkeypatch.setenv("DATABASE_URL", TEST_DB)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("PNBA_DISCORD_WEBHOOK_URL", raising=False)
    import pnba.config
    importlib.reload(pnba.config)
    for name in ("db", "settings", "llm", "collect", "fetch", "curate", "notify", "pipeline"):
        importlib.reload(importlib.import_module(f"pnba.{name}"))
    if TEST_DB:
        import pnba.db
        pnba.db.init()
        with pnba.db.connect() as con:
            con.execute(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY")
    return TEST_DB


@pytest.fixture()
def dbenv(env):
    if not TEST_DB:
        pytest.skip("TEST_DATABASE_URL が無いので DB のテストは飛ばす")
    return env
