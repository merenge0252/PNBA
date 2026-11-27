"""Web 画面（FastAPI）。"""
import datetime
import json
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import __version__, auth, config, db, llm, pipeline, settings
from .log import log

HERE = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(HERE, "templates"))
OPEN_PATHS = ("/login", "/static/", "/healthz")
WEEKDAYS = "月火水木金土日"


def _fmt_day(day):
    try:
        d = datetime.date.fromisoformat(day)
    except (TypeError, ValueError):
        return day
    return f"{d.month}/{d.day}（{WEEKDAYS[d.weekday()]}）"


templates.env.filters["day"] = _fmt_day


def create_app(start_scheduler=True):
    @asynccontextmanager
    async def lifespan(app):
        db.init()
        db.mark_stale_runs()
        sched = None
        if start_scheduler:
            from .scheduler import Scheduler
            sched = Scheduler()
            sched.start()
        yield
        if sched:
            sched.stop()

    app = FastAPI(title="PNBA", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None,
                  openapi_url=None)

    @app.middleware("http")
    async def require_login(request: Request, call_next):
        path = request.url.path
        if auth.auth_enabled() and not path.startswith(OPEN_PATHS) and not request.session.get("user"):
            if request.method == "GET":
                return RedirectResponse("/login", status_code=303)
            return JSONResponse({"error": "login required"}, status_code=401)
        # API（JSON）はヘッダーで CSRF を確かめる。フォームの POST は各ハンドラで確かめる
        if request.method == "POST" and path.startswith("/api/"):
            if not auth.csrf_ok(request.session, request.headers.get("x-csrf-token")):
                return JSONResponse({"error": "invalid csrf token"}, status_code=403)
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Content-Security-Policy",
                                "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
                                "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        return resp

    # SessionMiddleware は require_login より外側に置く（後から add したものが外側）
    app.add_middleware(SessionMiddleware, secret_key=auth.secret_key(), session_cookie="pnba_session",
                       max_age=60 * 60 * 24 * 30, same_site="lax", https_only=config.SECURE_COOKIE)
    app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")

    def render(request, name, **ctx):
        ctx.update(csrf=auth.csrf_token(request.session), auth_enabled=auth.auth_enabled(),
                   running=pipeline.is_running(), version=__version__)
        return templates.TemplateResponse(request, name, ctx)

    def client_ip(request):
        if config.TRUST_PROXY and request.headers.get("x-forwarded-for"):
            # 最後の値が信頼できるプロキシが付けたもの（先頭は利用者が自由に書ける）
            return request.headers["x-forwarded-for"].split(",")[-1].strip()
        return request.client.host if request.client else "?"

    # ---------- ログイン ----------

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request):
        if not auth.auth_enabled() or request.session.get("user"):
            return RedirectResponse("/", status_code=303)
        return render(request, "login.html", error="")

    @app.post("/login")
    def login(request: Request, password: str = Form(""), csrf: str = Form("")):
        ip = client_ip(request)
        if not auth.csrf_ok(request.session, csrf):
            return render(request, "login.html", error="もう一度お試しください")
        if auth.locked(ip):
            return render(request, "login.html", error="失敗が続いたので15分ほど待ってください")
        if not auth.check_password(password):
            auth.record_fail(ip)
            log(f"[auth] ログイン失敗 {ip}")
            return render(request, "login.html", error="パスワードが違います")
        auth.clear_fails(ip)
        request.session.clear()
        request.session["user"] = "owner"
        return RedirectResponse("/", status_code=303)

    @app.post("/logout")
    def logout(request: Request, csrf: str = Form("")):
        if not auth.csrf_ok(request.session, csrf):
            return JSONResponse({"error": "invalid csrf token"}, status_code=403)
        request.session.clear()
        return RedirectResponse("/login" if auth.auth_enabled() else "/", status_code=303)

    # ---------- 記事 ----------

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, day: str = ""):
        days = db.article_days()
        if not day:
            day = days[0]["day"] if days else db.today()
        arts = db.articles_for_day(day)
        idx = next((i for i, d in enumerate(days) if d["day"] == day), None)
        prev_day = days[idx + 1]["day"] if idx is not None and idx + 1 < len(days) else ""
        next_day = days[idx - 1]["day"] if idx else ""
        return render(request, "index.html", day=day, articles=arts, top=[a for a in arts if a["top"]],
                      rest=[a for a in arts if not a["top"]], prev_day=prev_day, next_day=next_day,
                      is_today=day == db.today(), last_run=(db.last_runs(1) or [None])[0])

    @app.get("/archive", response_class=HTMLResponse)
    def archive(request: Request, feedback: str = "", category: str = "", q: str = ""):
        if feedback not in ("", "up", "down"):
            feedback = ""
        arts = db.search_articles(feedback=feedback, category=category, q=q.strip()[:100])
        return render(request, "archive.html", articles=arts, feedback=feedback, category=category, q=q,
                      categories=db.categories(), days=db.article_days())

    @app.post("/api/feedback/{aid}")
    async def feedback(aid: str, request: Request):
        body = await request.json()
        value = body.get("value", "")
        if value not in ("up", "down", ""):
            return JSONResponse({"error": "bad value"}, status_code=400)
        if not db.set_feedback(aid, value):
            return JSONResponse({"error": "not found"}, status_code=404)
        return {"id": aid, "feedback": value}

    # ---------- 実行 ----------

    @app.post("/api/run")
    def run_now():
        if pipeline.is_running():
            return JSONResponse({"status": "running"}, status_code=409)

        def job():
            try:
                pipeline.run(trigger="manual")
            except Exception:
                pass  # 失敗は runs テーブルに残る

        threading.Thread(target=job, name="pnba-manual-run", daemon=True).start()
        return {"status": "started"}

    @app.get("/api/status")
    def status():
        last = (db.last_runs(1) or [None])[0]
        return {"running": pipeline.is_running(), "last_run": last}

    # ---------- 設定 ----------

    def settings_ctx(**extra):
        s = settings.load()
        try:
            backend, backend_error = llm.backend(s["llm"]), ""
        except llm.LLMError as e:
            backend, backend_error = "", str(e)
        return dict(s=s, sources_text=json.dumps(s["sources"], ensure_ascii=False, indent=2),
                    llm_choices=settings.LLM_CHOICES, backend=backend, backend_error=backend_error,
                    env_webhook=bool(config.DISCORD_WEBHOOK_URL), runs=db.last_runs(10), tz=str(config.TZ),
                    **extra)

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request, saved: str = ""):
        return render(request, "settings.html", **settings_ctx(error="", saved=bool(saved)))

    @app.post("/settings")
    async def settings_save(request: Request):
        form = dict(await request.form())
        if not auth.csrf_ok(request.session, form.get("csrf")):
            return JSONResponse({"error": "invalid csrf token"}, status_code=403)
        try:
            settings.save(form)
        except (settings.SettingsError, ValueError) as e:
            ctx = settings_ctx(error=str(e), saved=False)
            # 入力した値を消さずに戻す
            ctx["s"].update({k: form.get(k, ctx["s"][k]) for k in ("interests", "per_day", "run_time", "llm",
                                                                   "discord_webhook")})
            ctx["s"]["schedule_enabled"] = bool(form.get("schedule_enabled"))
            ctx["sources_text"] = form.get("sources", ctx["sources_text"])
            return render(request, "settings.html", **ctx)
        return RedirectResponse("/settings?saved=1", status_code=303)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app
