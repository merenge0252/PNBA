// 設定の検査（サーバー関数とテストの共通部分）

export type Sources = {
  locale?: { hl?: string; gl?: string };
  categories: Record<
    string,
    {
      about?: string;
      rss?: { name?: string; url: string }[];
      google_news?: string[];
      zenn_topics?: string[];
      github_trending_keywords?: string[];
    }
  >;
};

export type Settings = {
  interests: string;
  sources: Sources;
  per_day: number;
  schedule_enabled: boolean;
  discord_webhook: string;
};

export class SettingsError extends Error {}

const LIST_KEYS = ["google_news", "zenn_topics", "github_trending_keywords"] as const;

export function validateSources(text: string): Sources {
  let src: unknown;
  try {
    src = JSON.parse(text);
  } catch (e) {
    throw new SettingsError(`情報源の JSON が読めません: ${(e as Error).message}`);
  }
  const cats = (src as Sources | null)?.categories;
  if (!cats || typeof cats !== "object" || Array.isArray(cats) || Object.keys(cats).length === 0) {
    throw new SettingsError("情報源には categories（カテゴリ名 → 設定）が1つ以上必要です");
  }
  for (const [name, c] of Object.entries(cats)) {
    if (!c || typeof c !== "object" || Array.isArray(c)) {
      throw new SettingsError(`カテゴリ「${name}」の形が正しくありません`);
    }
    for (const key of LIST_KEYS) {
      const v = c[key];
      if (v !== undefined && !(Array.isArray(v) && v.every((x) => typeof x === "string"))) {
        throw new SettingsError(`カテゴリ「${name}」の ${key} は文字列のリストにしてください`);
      }
    }
    if (c.rss !== undefined) {
      if (!Array.isArray(c.rss)) throw new SettingsError(`カテゴリ「${name}」の rss はリストにしてください`);
      for (const feed of c.rss) {
        if (!feed || typeof feed.url !== "string" || !/^https?:\/\//.test(feed.url)) {
          throw new SettingsError(`カテゴリ「${name}」の rss に http(s) の url が無いものがあります`);
        }
      }
    }
  }
  return src as Sources;
}

export function parseSettingsForm(form: {
  interests?: string;
  per_day?: string;
  schedule_enabled?: string | null;
  discord_webhook?: string;
  sources?: string;
}): Settings {
  const perDay = Number(form.per_day ?? "");
  if (!Number.isInteger(perDay) || perDay < 1 || perDay > 50) {
    throw new SettingsError("1日の本数は 1〜50 の整数にしてください");
  }
  const hook = (form.discord_webhook ?? "").trim();
  if (hook && !/^https:\/\/(discord\.com|discordapp\.com)\/api\/webhooks\//.test(hook)) {
    throw new SettingsError("Discord Webhook は https://discord.com/api/webhooks/ で始まる URL にしてください");
  }
  const interests = (form.interests ?? "").trim();
  if (interests.length > 20000) throw new SettingsError("関心は 20000 字以内にしてください");
  return {
    interests,
    per_day: perDay,
    schedule_enabled: Boolean(form.schedule_enabled),
    discord_webhook: hook,
    sources: validateSources(form.sources ?? ""),
  };
}
