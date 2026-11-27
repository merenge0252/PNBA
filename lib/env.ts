import "server-only";

function env(name: string): string {
  return (process.env[name] ?? "").trim();
}

export const config = {
  databaseUrl: env("DATABASE_URL") || env("POSTGRES_URL"),
  password: env("PNBA_PASSWORD"),
  sessionSecret: env("PNBA_SESSION_SECRET"),
  tz: env("PNBA_TZ") || "Asia/Tokyo",
  githubToken: env("PNBA_GITHUB_TOKEN"),
  githubRepo:
    env("PNBA_GITHUB_REPO") ||
    (env("VERCEL_GIT_REPO_OWNER") && env("VERCEL_GIT_REPO_SLUG")
      ? `${env("VERCEL_GIT_REPO_OWNER")}/${env("VERCEL_GIT_REPO_SLUG")}`
      : ""),
  githubRef: env("PNBA_GITHUB_REF") || "main",
  githubApi: env("PNBA_GITHUB_API") || "https://api.github.com",
  envWebhook: Boolean(env("PNBA_DISCORD_WEBHOOK_URL")),
};
