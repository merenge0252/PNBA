"use client";

import { startTransition, useActionState } from "react";
import { updateSettings, type FormState } from "@/app/actions";

type Initial = {
  interests: string;
  per_day: number;
  schedule_enabled: boolean;
  discord_webhook: string;
  sources: string;
};

export default function SettingsForm({ initial, envWebhook }: { initial: Initial; envWebhook: boolean }) {
  const [state, action, pending] = useActionState<FormState, FormData>(updateSettings, {});

  return (
    // action 属性で送ると React が送信後に入力を初期値へ戻すので、保存に失敗しても入力が消えないよう自分で送る
    <form
      className="settings"
      onSubmit={(e) => {
        e.preventDefault();
        const data = new FormData(e.currentTarget);
        startTransition(() => action(data));
      }}
    >
      {state.error && <p className="card error">{state.error}</p>}
      {state.ok && <p className="card ok">{state.ok}</p>}

      <section className="card">
        <h2>あなたの関心</h2>
        <p className="help">
          AI はここを読んで記事を選びます。仕事・趣味・今の予定・困っていること・読みたくない話題など、具体的に書くほど精度が上がります。
        </p>
        <textarea name="interests" rows={12} defaultValue={initial.interests} />
      </section>

      <section className="card">
        <h2>配信</h2>
        <label>
          1日の本数
          <input type="number" name="per_day" min={1} max={50} defaultValue={initial.per_day} required />
        </label>
        <label className="check">
          <input type="checkbox" name="schedule_enabled" value="1" defaultChecked={initial.schedule_enabled} />
          毎朝自動で集める
        </label>
        <label>
          Discord Webhook（任意）
          <input
            type="url"
            name="discord_webhook"
            defaultValue={initial.discord_webhook}
            placeholder="https://discord.com/api/webhooks/..."
            autoComplete="off"
          />
        </label>
        <p className="help">
          届いたときに「今日の N 本」を Discord に送ります。
          {envWebhook && " GitHub の Secrets に PNBA_DISCORD_WEBHOOK_URL があるので、そちらが優先されます。"}
        </p>
      </section>

      <section className="card">
        <h2>情報源</h2>
        <p className="help">
          カテゴリごとに <code>about</code>（どんな記事が欲しいか）と、<code>rss</code> / <code>google_news</code>
          （検索語）/ <code>zenn_topics</code> / <code>github_trending_keywords</code> を書きます。書き方は README を参照。
        </p>
        <textarea name="sources" rows={20} className="mono" spellCheck={false} defaultValue={initial.sources} />
      </section>

      <button className="primary sticky" disabled={pending}>
        {pending ? "保存中…" : "保存"}
      </button>
    </form>
  );
}
