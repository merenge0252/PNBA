import "server-only";
import type postgres from "postgres";
import { readFile } from "node:fs/promises";
import { db, sharedFile } from "./db";
import type { Settings } from "./settings-core";

export type Article = {
  id: string;
  day: string;
  url: string;
  title: string;
  headline: string;
  category: string;
  source: string;
  publisher: string;
  facts: string;
  why_me: string;
  action: string;
  deadline: string;
  score: number;
  top: boolean;
  feedback: "" | "up" | "down";
};

export type Run = {
  id: number;
  started_at: string;
  finished_at: string | null;
  day: string;
  trigger: string;
  status: "running" | "ok" | "empty" | "error";
  collected: number;
  picked: number;
  message: string;
};

const ARTICLE_COLS =
  "id, day, url, title, headline, category, source, publisher, facts, why_me, action, deadline, score, top, feedback";

export async function articlesForDay(day: string): Promise<Article[]> {
  const sql = await db();
  return sql.unsafe<Article[]>(
    `SELECT ${ARTICLE_COLS} FROM pnba_articles WHERE day = $1 ORDER BY top DESC, score DESC`,
    [day],
  );
}

export async function articleDays(limit = 60): Promise<{ day: string; n: number }[]> {
  const sql = await db();
  return sql<{ day: string; n: number }[]>`
    SELECT day, COUNT(*)::int AS n FROM pnba_articles GROUP BY day ORDER BY day DESC LIMIT ${limit}`;
}

function likePattern(q: string): string {
  return "%" + q.replace(/[\\%_]/g, (c) => "\\" + c) + "%";
}

export async function searchArticles(opts: {
  feedback?: string;
  category?: string;
  q?: string;
  limit?: number;
}): Promise<Article[]> {
  const sql = await db();
  const where: string[] = [];
  const args: string[] = [];
  if (opts.feedback) {
    args.push(opts.feedback);
    where.push(`feedback = $${args.length}`);
  }
  if (opts.category) {
    args.push(opts.category);
    where.push(`category = $${args.length}`);
  }
  if (opts.q) {
    args.push(likePattern(opts.q));
    const n = args.length;
    where.push(`(headline ILIKE $${n} OR title ILIKE $${n} OR facts ILIKE $${n})`);
  }
  const limit = Math.min(Math.max(Math.floor(opts.limit ?? 200), 1), 500);
  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";
  return sql.unsafe<Article[]>(
    `SELECT ${ARTICLE_COLS} FROM pnba_articles ${whereSql} ORDER BY day DESC, top DESC, score DESC LIMIT ${limit}`,
    args,
  );
}

export async function categories(): Promise<string[]> {
  const sql = await db();
  const rows = await sql<{ category: string }[]>`
    SELECT DISTINCT category FROM pnba_articles WHERE category <> '' ORDER BY category`;
  return rows.map((r) => r.category);
}

export async function setFeedback(id: string, value: "" | "up" | "down"): Promise<boolean> {
  const sql = await db();
  const r = await sql`UPDATE pnba_articles SET feedback = ${value} WHERE id = ${id}`;
  return r.count > 0;
}

export async function lastRuns(n = 10): Promise<Run[]> {
  const sql = await db();
  const rows = await sql`SELECT * FROM pnba_runs ORDER BY id DESC LIMIT ${n}`;
  return rows.map((r) => ({
    id: r.id,
    day: r.day,
    trigger: r.trigger,
    status: r.status,
    collected: r.collected,
    picked: r.picked,
    message: r.message,
    started_at: new Date(r.started_at).toISOString(),
    finished_at: r.finished_at ? new Date(r.finished_at).toISOString() : null,
  }));
}

export async function loadSettings(): Promise<Settings> {
  const sql = await db();
  const rows = await sql<{ key: string; value: unknown }[]>`SELECT key, value FROM pnba_settings`;
  const s = Object.fromEntries(rows.map((r) => [r.key, r.value])) as Record<string, unknown>;
  return {
    interests: String(s.interests ?? ""),
    sources: (s.sources as Settings["sources"]) ?? { categories: {} },
    per_day: Number(s.per_day ?? 12),
    schedule_enabled: s.schedule_enabled !== false,
    discord_webhook: String(s.discord_webhook ?? ""),
  };
}

export async function saveSettings(s: Settings): Promise<void> {
  const sql = await db();
  await sql.begin(async (tx) => {
    for (const [key, value] of Object.entries(s)) {
      await tx`INSERT INTO pnba_settings(key, value) VALUES(${key}, ${sql.json(value as postgres.JSONValue)})
               ON CONFLICT(key) DO UPDATE SET value = excluded.value`;
    }
  });
}

// ---------- ログイン試行の制限 ----------

export const MAX_FAILS = 5;
export const LOCK_MINUTES = 15;

export async function loginLocked(ip: string): Promise<boolean> {
  const sql = await db();
  const [r] = await sql<{ fails: number }[]>`
    SELECT fails FROM pnba_login_attempts
    WHERE ip = ${ip} AND first_at > now() - make_interval(mins => ${LOCK_MINUTES})`;
  return Boolean(r && r.fails >= MAX_FAILS);
}

export async function recordLoginFail(ip: string): Promise<void> {
  const sql = await db();
  await sql`
    INSERT INTO pnba_login_attempts(ip, fails, first_at) VALUES(${ip}, 1, now())
    ON CONFLICT(ip) DO UPDATE SET
      fails = CASE WHEN pnba_login_attempts.first_at > now() - make_interval(mins => ${LOCK_MINUTES})
                   THEN pnba_login_attempts.fails + 1 ELSE 1 END,
      first_at = CASE WHEN pnba_login_attempts.first_at > now() - make_interval(mins => ${LOCK_MINUTES})
                      THEN pnba_login_attempts.first_at ELSE now() END`;
  await sql`DELETE FROM pnba_login_attempts WHERE first_at < now() - interval '1 day'`;
}

export async function clearLoginFails(ip: string): Promise<void> {
  const sql = await db();
  await sql`DELETE FROM pnba_login_attempts WHERE ip = ${ip}`;
}

export async function everSucceeded(): Promise<boolean> {
  const sql = await db();
  const [r] = await sql`SELECT 1 AS x FROM pnba_runs WHERE status IN ('ok', 'empty') LIMIT 1`;
  return Boolean(r);
}

export async function interestsAreDefault(): Promise<boolean> {
  const sql = await db();
  const [r] = await sql<{ value: unknown }[]>`SELECT value FROM pnba_settings WHERE key = 'interests'`;
  const current = String(r?.value ?? "").trim();
  const def = (await readFile(sharedFile("defaults", "interests.md"), "utf8")).trim();
  return current === "" || current === def;
}
