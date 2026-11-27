"""利用者が設定画面で変える値（DB に保存）。初期値は examples/ から読む。"""
import json
import re

from . import config, db

LLM_CHOICES = {"auto": "自動（API キーがあれば Gemini API、無ければ agy）", "gemini_api": "Gemini API", "agy": "agy -p"}


def _example(name):
    return (config.EXAMPLES_DIR / name).read_text(encoding="utf-8")


def defaults():
    return {
        "interests": _example("interests.md"),
        "sources": json.loads(_example("sources.json")),
        "per_day": 12,
        "run_time": "07:00",
        "schedule_enabled": True,
        "llm": "auto",
        "discord_webhook": "",
    }


def load():
    d = defaults()
    return {k: db.get_setting(k, v) for k, v in d.items()}


def get(key):
    return db.get_setting(key, defaults()[key])


class SettingsError(ValueError):
    pass


def validate_sources(text_or_obj):
    """情報源の JSON を検査して dict を返す。"""
    try:
        src = json.loads(text_or_obj) if isinstance(text_or_obj, str) else text_or_obj
    except json.JSONDecodeError as e:
        raise SettingsError(f"情報源の JSON が読めません: {e}")
    cats = src.get("categories") if isinstance(src, dict) else None
    if not isinstance(cats, dict) or not cats:
        raise SettingsError("情報源には categories（カテゴリ名 → 設定）が1つ以上必要です")
    for name, c in cats.items():
        if not isinstance(c, dict):
            raise SettingsError(f"カテゴリ「{name}」の形が正しくありません")
        for key in ("rss", "google_news", "zenn_topics", "github_trending_keywords"):
            if key in c and not isinstance(c[key], list):
                raise SettingsError(f"カテゴリ「{name}」の {key} はリストにしてください")
        for feed in c.get("rss", []):
            url = feed.get("url", "") if isinstance(feed, dict) else ""
            if not re.match(r"^https?://", url):
                raise SettingsError(f"カテゴリ「{name}」の RSS に http(s) の url がありません: {feed}")
    return src


def save(form):
    """設定画面の入力を検査して保存する。"""
    per_day = int(form.get("per_day") or 12)
    if not 1 <= per_day <= 50:
        raise SettingsError("1日の本数は 1〜50 にしてください")
    run_time = (form.get("run_time") or "").strip()
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", run_time):
        raise SettingsError("配信時刻は HH:MM で入力してください")
    llm = form.get("llm") or "auto"
    if llm not in LLM_CHOICES:
        raise SettingsError("AI の選択が正しくありません")
    hook = (form.get("discord_webhook") or "").strip()
    if hook and not re.match(r"^https://(discord\.com|discordapp\.com)/api/webhooks/", hook):
        raise SettingsError("Discord Webhook の URL は https://discord.com/api/webhooks/ で始まるものにしてください")
    src = validate_sources(form.get("sources") or "")
    interests = (form.get("interests") or "").strip()
    if len(interests) > 20000:
        raise SettingsError("関心は 20000 字以内にしてください")
    db.set_setting("interests", interests)
    db.set_setting("sources", src)
    db.set_setting("per_day", per_day)
    db.set_setting("run_time", run_time)
    db.set_setting("schedule_enabled", bool(form.get("schedule_enabled")))
    db.set_setting("llm", llm)
    db.set_setting("discord_webhook", hook)
