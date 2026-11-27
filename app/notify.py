"""Discord Webhook への通知（任意）。"""
import requests

from . import config
from .log import log


def build_message(picks, day, public_url=""):
    lines = [f"📰 **{day} のニュース（{len(picks)}本）**"]
    for p in picks[:5]:
        mark = "⭐ " if p.get("top") else "・"
        lines.append(f"{mark}[{p.get('category', '')}] {p.get('headline') or p['title']}")
    if len(picks) > 5:
        lines.append(f"ほか {len(picks) - 5} 本")
    if public_url:
        lines.append(f"{public_url.rstrip('/')}/?day={day}")
    return "\n".join(lines)[:1900]


def send(picks, day, webhook=""):
    url = config.DISCORD_WEBHOOK_URL or webhook
    if not url or not picks:
        return False
    try:
        r = requests.post(url, json={"content": build_message(picks, day, config.PUBLIC_URL),
                                     "allowed_mentions": {"parse": []}}, timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        log(f"[notify] Discord への送信失敗: {str(e)[:200]}")
        return False
