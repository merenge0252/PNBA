"""Gemini API の呼び出し。"""
import json
import re
import time

import requests

from . import config
from .log import log


class LLMError(RuntimeError):
    pass


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def generate(prompt, data="", retries=4):
    """prompt（指示）と data（記事などの材料）を渡し、返答の文字列を返す。"""
    if not config.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY が設定されていません（GitHub の Secrets に入れてください）")
    body = {
        "systemInstruction": {"parts": [{"text": prompt}]},
        "contents": [{"role": "user", "parts": [{"text": data or "（材料なし）"}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
    }
    url = GEMINI_URL.format(model=config.GEMINI_MODEL)
    wait = 20
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, headers={"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"},
                              json=body, timeout=config.LLM_TIMEOUT)
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(wait)
                continue
            raise LLMError(f"Gemini API に接続できません: {e}")
        if r.status_code == 200:
            out = r.json()
            try:
                return "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"])
            except (KeyError, IndexError):
                raise LLMError(f"Gemini API の返答が空です: {json.dumps(out, ensure_ascii=False)[:500]}")
        if (r.status_code == 429 or r.status_code >= 500) and attempt < retries:
            log(f"[llm] Gemini API {r.status_code}、{wait}秒待って再試行")
            time.sleep(wait)
            wait = min(wait * 2, 300)
            continue
        raise LLMError(f"Gemini API エラー {r.status_code}: {r.text[:500]}")
    raise LLMError("Gemini API の再試行が尽きました")


def extract_json(text, opener="{"):
    """返答から JSON を取り出す（```json ブロック、または最初の { から最後の } まで）。"""
    closer = "]" if opener == "[" else "}"
    m = re.search(r"```(?:json)?\s*(\%s.*?\%s)\s*```" % (opener, closer), text, re.S)
    raw = m.group(1) if m else text[text.find(opener): text.rfind(closer) + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMError(f"AI の返答が JSON として読めません: {e}: {text[:300]}")
