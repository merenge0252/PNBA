"""候補記事の本文を取る。Google ニュースのリンクは元記事の URL に戻す。"""
import json
import re
import urllib.parse

import requests
import trafilatura

from . import config
from .collect import UA
from .log import log


def decode_google_news(url):
    """Google ニュースの記事リンク（news.google.com/rss/articles/…）を元記事の URL に戻す。失敗したら元のまま。"""
    aid = urllib.parse.urlparse(url).path.split("/")[-1]
    html = requests.get(f"https://news.google.com/rss/articles/{aid}", headers=UA, timeout=15).text
    sg = re.search(r'data-n-a-sg="([^"]+)"', html)
    ts = re.search(r'data-n-a-ts="([^"]+)"', html)
    if not (sg and ts):
        return url
    inner = (f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],'
             f'"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{aid}",{ts.group(1)},"{sg.group(1)}"]')
    r = requests.post("https://news.google.com/_/DotsSplashUi/data/batchexecute",
                      headers={**UA, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
                      data="f.req=" + urllib.parse.quote(json.dumps([[["Fbv4je", inner]]])), timeout=15)
    body = json.loads(r.text.split("\n\n")[1])[:-2]
    real = json.loads(body[0][2])[1]
    return real if isinstance(real, str) and real.startswith("http") else url


def fetch_body(a):
    """本文を body に入れた新しい dict を返す。元の Google ニュース URL は gnews_url に残す（配信済みの判定用）。"""
    a = dict(a)
    try:
        if "news.google.com" in a["url"]:
            real = decode_google_news(a["url"])
            if real != a["url"]:
                a["gnews_url"], a["url"] = a["url"], real
        r = requests.get(a["url"], headers=UA, timeout=20)
        html = r.text if r.ok else ""
        text = trafilatura.extract(html, include_comments=False, include_tables=False) if html else ""
        a["body"] = (text or "")[:config.BODY_CHARS]
    except Exception as e:
        log(f"[fetch] 本文の取得失敗 {a['url'][:80]}: {str(e)[:120]}")
        a["body"] = ""
    return a
