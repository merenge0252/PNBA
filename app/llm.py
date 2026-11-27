"""AI の呼び出し。Gemini API（GEMINI_API_KEY）を優先し、無ければ agy -p を使う。"""
import json
import os
import re
import shutil
import subprocess
import time
import uuid

import requests

from . import config
from .log import log


class LLMError(RuntimeError):
    pass


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RATE_RE = re.compile(r"429|RESOURCE_EXHAUSTED|rate.?limit|quota", re.I)


def backend(choice="auto"):
    """実際に使うバックエンド名を返す。"""
    if choice == "gemini_api" or (choice == "auto" and config.GEMINI_API_KEY):
        if not config.GEMINI_API_KEY:
            raise LLMError("GEMINI_API_KEY が設定されていません")
        return "gemini_api"
    if not shutil.which(config.AGY_CMD):
        raise LLMError(f"GEMINI_API_KEY が無く、{config.AGY_CMD} コマンドも見つかりません。どちらかを用意してください")
    return "agy"


def generate(prompt, data="", choice="auto"):
    """prompt（指示）と data（記事などの材料）を渡し、返答の文字列を返す。"""
    b = backend(choice)
    if b == "gemini_api":
        return _gemini_api(prompt, data)
    return _agy(prompt, data)


def _gemini_api(prompt, data, retries=4):
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


def _agy_env():
    """agy に渡す環境変数。鍵らしいものは落とす。"""
    return {k: v for k, v in os.environ.items()
            if not re.search(r"TOKEN|SECRET|WEBHOOK|API_KEY|PASSWORD", k, re.I)}


AGY_NOTE = ("\n\n【実行環境の制約】このモードではコマンドの実行やファイルの書き込みはできない（試すと拒否されて回答が失われる）。"
            "材料はこのディレクトリの input.md にある。読むだけにして、答えそのもの（JSON）を最後のメッセージに直接書け。")


def _agy(prompt, data, retries=3):
    # agy -p は標準入力を読まないので、作業ディレクトリにファイルで置いて読ませる
    work = config.WORK_DIR / f"agy-{uuid.uuid4().hex[:8]}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        (work / "input.md").write_text(data, encoding="utf-8")
        cmd = [shutil.which(config.AGY_CMD) or config.AGY_CMD, "-p", prompt + AGY_NOTE,
               "--output-format", "json", "--mode", "plan", "--print-timeout", f"{config.LLM_TIMEOUT}s"]
        if config.AGY_MODEL:
            cmd += ["--model", config.AGY_MODEL]
        wait = 60
        for attempt in range(retries + 1):
            try:
                p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   timeout=config.LLM_TIMEOUT + 60, env=_agy_env())
            except subprocess.TimeoutExpired:
                raise LLMError("agy がタイムアウトしました")
            text = (p.stdout or "") + (p.stderr or "")
            if p.returncode == 0:
                try:
                    out = json.loads(p.stdout)
                except json.JSONDecodeError:
                    return p.stdout
                if out.get("status", "SUCCESS") == "SUCCESS" and out.get("response"):
                    return out["response"]
                text = json.dumps(out, ensure_ascii=False)
                if out.get("status", "SUCCESS") == "SUCCESS" and attempt < retries:
                    continue  # 返事が空（拒否された操作で止まった等）なら取り直す
            if RATE_RE.search(text) and attempt < retries:
                log(f"[llm] agy のレート制限、{wait}秒待って再試行")
                time.sleep(wait)
                wait = min(wait * 2, 1800)
                continue
            raise LLMError(f"agy エラー: {text[-1000:]}")
        raise LLMError("agy の再試行が尽きました")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def extract_json(text, opener="{"):
    """返答から JSON を取り出す（```json ブロック、または最初の { から最後の } まで）。"""
    closer = "]" if opener == "[" else "}"
    m = re.search(r"```(?:json)?\s*(\%s.*?\%s)\s*```" % (opener, closer), text, re.S)
    raw = m.group(1) if m else text[text.find(opener): text.rfind(closer) + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMError(f"AI の返答が JSON として読めません: {e}: {text[:300]}")
