import "server-only";
import { readFile } from "node:fs/promises";
import path from "node:path";
import postgres from "postgres";
import { config } from "./env";

export class SetupError extends Error {}

type Sql = ReturnType<typeof postgres>;

const g = globalThis as unknown as { __pnbaSql?: Sql; __pnbaReady?: Promise<void> };

function client(): Sql {
  if (!config.databaseUrl) {
    throw new SetupError("DATABASE_URL が設定されていません。Vercel で Neon（Postgres）を連携してください。");
  }
  // prepare: false は Neon の接続プーラー（PgBouncer）でも動くように
  g.__pnbaSql ??= postgres(config.databaseUrl, { prepare: false, max: 3, idle_timeout: 20, connect_timeout: 15 });
  return g.__pnbaSql;
}

export function sharedFile(...parts: string[]): string {
  return path.join(process.cwd(), "shared", ...parts);
}

async function prepare(sql: Sql): Promise<void> {
  const schema = await readFile(sharedFile("schema.sql"), "utf8");
  await sql.unsafe(schema);
  const interests = await readFile(sharedFile("defaults", "interests.md"), "utf8");
  const sources = JSON.parse(await readFile(sharedFile("defaults", "sources.json"), "utf8"));
  const defaults: Record<string, postgres.JSONValue> = {
    interests,
    sources,
    per_day: 12,
    schedule_enabled: true,
    discord_webhook: "",
  };
  for (const [key, value] of Object.entries(defaults)) {
    await sql`INSERT INTO pnba_settings(key, value) VALUES(${key}, ${sql.json(value)})
              ON CONFLICT(key) DO NOTHING`;
  }
}

/** テーブルと初期設定を用意した DB クライアントを返す（プロセスごとに1回だけ用意する）。 */
export async function db(): Promise<Sql> {
  const sql = client();
  g.__pnbaReady ??= prepare(sql).catch((e) => {
    g.__pnbaReady = undefined;
    throw e;
  });
  await g.__pnbaReady;
  return sql;
}
