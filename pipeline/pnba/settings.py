"""利用者が Web の設定画面で変える値（DB に保存）。初期値は shared/defaults/ から読む。"""
import json

from . import config, db


def defaults():
    return {
        "interests": (config.DEFAULTS_DIR / "interests.md").read_text(encoding="utf-8"),
        "sources": json.loads((config.DEFAULTS_DIR / "sources.json").read_text(encoding="utf-8")),
        "per_day": 12,
        "schedule_enabled": True,
        "discord_webhook": "",
    }


def load():
    return {k: db.get_setting(k, v) for k, v in defaults().items()}


def get(key):
    return db.get_setting(key, defaults()[key])


def seed() -> None:
    """まだ無い設定を初期値で入れる（Web で設定を開く前に Actions が動いた場合のため）。"""
    for k, v in defaults().items():
        if db.get_setting(k) is None:
            db.set_setting(k, v)
