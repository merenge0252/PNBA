import SetupNotice from "@/components/SetupNotice";
import SettingsForm from "@/components/SettingsForm";
import { lastRuns, loadSettings } from "@/lib/data";
import { SetupError } from "@/lib/db";
import { config } from "@/lib/env";
import { formatTime } from "@/lib/format";
import { canDispatch } from "@/lib/github";
import { requireLogin } from "@/lib/session";

const STATUS: Record<string, string> = { ok: "成功", empty: "新着なし", error: "失敗", running: "実行中" };
const TRIGGER: Record<string, string> = { schedule: "定時", web: "画面", manual: "手動" };

export default async function SettingsPage() {
  await requireLogin();
  let settings, runs;
  try {
    [settings, runs] = await Promise.all([loadSettings(), lastRuns(10)]);
  } catch (e) {
    if (e instanceof SetupError) return <SetupNotice message={e.message} />;
    throw e;
  }

  return (
    <>
      <h1>設定</h1>
      <SettingsForm
        initial={{
          interests: settings.interests,
          per_day: settings.per_day,
          schedule_enabled: settings.schedule_enabled,
          discord_webhook: settings.discord_webhook,
          sources: JSON.stringify(settings.sources, null, 2),
        }}
        envWebhook={config.envWebhook}
      />

      <section className="card">
        <h2>配信の時刻と実行</h2>
        <p className="help">
          毎朝 6:17（日本時間）ごろに GitHub Actions が集めます。時刻はリポジトリの{" "}
          <code>.github/workflows/daily.yml</code> の cron で変えられます（GitHub の混み具合で数十分遅れることがあります）。
        </p>
        <p className="help">
          画面の「今すぐ集める」: {canDispatch() ? "使えます" : "PNBA_GITHUB_TOKEN が未設定なので使えません"}
          {config.githubRepo && `（${config.githubRepo}）`}
        </p>
      </section>

      <section className="card">
        <h2>実行の記録</h2>
        <table className="runs">
          <thead>
            <tr>
              <th>開始</th>
              <th>種類</th>
              <th>結果</th>
              <th>収集</th>
              <th>配信</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  まだ実行していません
                </td>
              </tr>
            )}
            {runs.flatMap((r) => [
              <tr key={r.id}>
                <td>{formatTime(r.started_at, config.tz)}</td>
                <td>{TRIGGER[r.trigger] ?? r.trigger}</td>
                <td className={r.status === "error" ? "error" : ""}>{STATUS[r.status] ?? r.status}</td>
                <td>{r.collected}</td>
                <td>{r.picked}</td>
              </tr>,
              r.status === "error" && r.message ? (
                <tr key={`${r.id}-msg`} className="msg">
                  <td colSpan={5}>{r.message.slice(0, 300)}</td>
                </tr>
              ) : null,
            ])}
          </tbody>
        </table>
      </section>
    </>
  );
}
