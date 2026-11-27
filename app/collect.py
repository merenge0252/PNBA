"""情報源から記事を集める（RSS / Google ニュース検索 / Zenn トピック / GitHub Trending）。"""
import datetime
import hashlib
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import feedparser
import requests
from bs4 import BeautifulSoup

from . import config
from .log import log

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/130 Safari/537.36"}


def article_id(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


def _recent(entry, now=None):
    t = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not t:
        return True
    now = now or datetime.datetime.now(datetime.timezone.utc)
    pub = datetime.datetime(*t[:6], tzinfo=datetime.timezone.utc)
    return now - pub <= datetime.timedelta(hours=config.WINDOW_H)


def parse_feed(feed, source, category):
    """feedparser の結果を記事 dict のリストにする。"""
    out = []
    for e in feed.entries:
        link = getattr(e, "link", "")
        if not (link and _recent(e)):
            continue
        title = getattr(e, "title", "") or link
        publisher = getattr(getattr(e, "source", None), "title", "") or ""
        if "news.google.com" in link:
            m = re.match(r"^(.*) - ([^-]{1,40})$", title)
            if m:
                title, publisher = m.group(1).strip(), publisher or m.group(2).strip()
            desc = ""  # Google ニュースの説明文はタイトルの繰り返しなので使わない
        else:
            desc = BeautifulSoup(getattr(e, "summary", "") or "", "html.parser").get_text(" ", strip=True)[:300]
        out.append({"title": title, "url": link, "published": getattr(e, "published", ""), "source": source,
                    "publisher": publisher or source, "desc": desc, "category": category})
    return out


def _rss(url, source, category):
    try:
        r = requests.get(url, headers=UA, timeout=20)
        r.raise_for_status()
        return parse_feed(feedparser.parse(r.content), source, category)
    except Exception as e:
        log(f"[collect] RSS 失敗 {source}: {str(e)[:200]}")
        return []


def parse_trending(html, keywords, category):
    out = []
    keywords = [k.lower() for k in keywords]
    for art in BeautifulSoup(html, "html.parser").find_all("article", class_="Box-row"):
        a = art.select_one("h2 a")
        if not a:
            continue
        name = re.sub(r"\s+", "", a.text)
        desc = art.find("p").text.strip() if art.find("p") else ""
        if any(k in f"{name} {desc}".lower() for k in keywords):
            out.append({"title": f"GitHub Trending: {name} - {desc}", "url": "https://github.com" + a["href"],
                        "published": "", "source": "GitHub Trending", "publisher": "GitHub", "desc": desc,
                        "category": category})
    return out


def _github_trending(keywords, category):
    if not keywords:
        return []
    try:
        html = requests.get("https://github.com/trending", headers=UA, timeout=20).text
    except Exception as e:
        log(f"[collect] GitHub Trending 失敗: {e}")
        return []
    return parse_trending(html, keywords, category)


def google_news_url(query, locale):
    hl, gl = locale.get("hl", "ja"), locale.get("gl", "JP")
    lang = hl.split("-")[0]
    return (f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}"
            f"&hl={hl}&gl={gl}&ceid={gl}:{lang}")


def jobs(sources):
    """収集の仕事（関数, 引数）のリスト。"""
    locale = sources.get("locale", {})
    out = []
    for cat, c in sources["categories"].items():
        for feed in c.get("rss", []):
            out.append((_rss, (feed["url"], feed.get("name", feed["url"]), cat)))
        for topic in c.get("zenn_topics", []):
            out.append((_rss, (f"https://zenn.dev/topics/{urllib.parse.quote(topic)}/feed", f"Zenn ({topic})", cat)))
        for q in c.get("google_news", []):
            out.append((_rss, (google_news_url(q, locale), f"Google News ({q})", cat)))
        if c.get("github_trending_keywords"):
            out.append((_github_trending, (c["github_trending_keywords"], cat)))
    return out


def dedupe(articles):
    seen, uniq = set(), []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            uniq.append(a)
    return uniq


def collect(sources):
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda j: j[0](*j[1]), jobs(sources)))
    return dedupe([a for r in results for a in r])
