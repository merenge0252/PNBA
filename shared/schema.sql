-- PNBA のテーブル。Web（Vercel）とパイプライン（GitHub Actions）の両方が起動時に流す（何度流しても同じ結果）。
CREATE TABLE IF NOT EXISTS pnba_articles (
    id          TEXT PRIMARY KEY,
    day         TEXT NOT NULL,
    url         TEXT NOT NULL,
    gnews_url   TEXT NOT NULL DEFAULT '',
    title       TEXT NOT NULL,
    headline    TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT '',
    source      TEXT NOT NULL DEFAULT '',
    publisher   TEXT NOT NULL DEFAULT '',
    published   TEXT NOT NULL DEFAULT '',
    facts       TEXT NOT NULL DEFAULT '',
    why_me      TEXT NOT NULL DEFAULT '',
    action      TEXT NOT NULL DEFAULT '',
    deadline    TEXT NOT NULL DEFAULT '',
    score       INTEGER NOT NULL DEFAULT 0,
    top         BOOLEAN NOT NULL DEFAULT FALSE,
    feedback    TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS pnba_articles_day ON pnba_articles(day);

CREATE TABLE IF NOT EXISTS pnba_seen_urls (
    url         TEXT PRIMARY KEY,
    seen_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pnba_settings (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS pnba_runs (
    id          SERIAL PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    day         TEXT NOT NULL,
    trigger     TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'running',
    collected   INTEGER NOT NULL DEFAULT 0,
    picked      INTEGER NOT NULL DEFAULT 0,
    message     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS pnba_login_attempts (
    ip          TEXT PRIMARY KEY,
    fails       INTEGER NOT NULL DEFAULT 0,
    first_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
