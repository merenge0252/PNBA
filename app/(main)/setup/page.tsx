import Link from "next/link";
import CopyButton from "@/components/CopyButton";
import SetupNotice from "@/components/SetupNotice";
import { everSucceeded, interestsAreDefault, lastRuns, loadSettings } from "@/lib/data";
import { SetupError } from "@/lib/db";
import { config } from "@/lib/env";
import { formatTime } from "@/lib/format";
import { canDispatch, latestWorkflowRun } from "@/lib/github";
import { requireLogin } from "@/lib/session";
import { diagnoseRunError, githubLinks, maskDatabaseUrl, runCheck, type CheckState } from "@/lib/setup-core";

export const metadata = { title: "セットアップ確認 - PNBA" };

const MARK: Record<CheckState, string> = { ok: "✅", todo: "❌", warn: "⚠️", optional: "➖" };

function Step({ state, title, children }: { state: CheckState; title: string; children?: React.ReactNode }) {
  return (
    <li className="step">
      <span className="mark" aria-label={state}>
        {MARK[state]}
      </span>
      <h3>{title}</h3>
      {children && <div className="body">{children}</div>}
    </li>
  );
}

export default async function SetupPage() {
  await requireLogin();
  let runs, succeeded, defaultInterests, settings;
  try {
    [runs, succeeded, defaultInterests, settings] = await Promise.all([
      lastRuns(1),
      everSucceeded(),
      interestsAreDefault(),
      loadSettings(),
    ]);
  } catch (e) {
    if (e instanceof SetupError) return <SetupNotice message={e.message} />;
    throw e;
  }
  const last = runs[0];
  const gh = config.githubRepo ? githubLinks(config.githubRepo) : null;
  const ghRun = await latestWorkflowRun();
  const runState = runCheck(last, succeeded);
  const diag = last?.status === "error" ? diagnoseRunError(last.message) : null;
  const required: CheckState[] = ["ok", "ok", runState];
  const done = required.filter((s) => s === "ok").length;

  return (
    <>
      <h1>セットアップ確認</h1>
      <p className="progress">
        必須 {done} / {required.length} 完了{done === required.length && "。準備ができています 🎉"}
      </p>

      <section className="card">
        <ol className="steps">
          <Step state="ok" title="ログインのパスワード（Vercel）">
            <p>設定済みです。変えるときは Vercel の Environment Variables の PNBA_PASSWORD を書き換えて Redeploy します。</p>
          </Step>

          <Step state="ok" title="データベース（Neon）">
            <p>つながっています。</p>
          </Step>

          <Step state={runState} title="毎朝の収集（GitHub Actions）">
            {runState === "ok" && (
              <p>
                動いています。前回: {last && formatTime(last.started_at, config.tz)}
                {last?.status === "ok" && `（${last.picked}本）`}
                {last?.status === "empty" && "（新着なし）"}
                {last?.status === "running" && "（実行中）"}
              </p>
            )}
            {last?.status === "running" && !succeeded && <p>いま実行中です。数分後にこの画面を再読み込みしてください。</p>}
            {diag && (
              <>
                <p className="error">
                  <b>{diag.title}</b>（{formatTime(last!.started_at, config.tz)}）
                </p>
                <p>{diag.fix}</p>
                <p className="help">エラー内容: {last!.message.slice(0, 300)}</p>
              </>
            )}
            {!last && (
              <>
                <p>まだ一度も記録がありません。GitHub に鍵を2つ入れて、1回実行してください。</p>
                <ol>
                  <li>
                    GitHub の Secrets の画面を開く
                    {gh ? (
                      <>
                        {" "}
                        <a className="linkbtn" href={gh.newSecret} target="_blank" rel="noopener noreferrer">
                          Secrets を開く
                        </a>
                      </>
                    ) : (
                      "（自分のリポジトリの Settings → Secrets and variables → Actions → New repository secret）"
                    )}
                  </li>
                  <li>
                    Name に <code>DATABASE_URL</code>、Secret に下の値を貼って <b>Add secret</b>
                    <div className="copyrow">
                      <code>{maskDatabaseUrl(config.databaseUrl)}</code>
                      <CopyButton value={config.databaseUrl} label="値をコピー" />
                    </div>
                  </li>
                  <li>
                    もう一度 <b>New repository secret</b> を押し、Name に <code>GEMINI_API_KEY</code>、Secret に Gemini の API キーを貼って{" "}
                    <b>Add secret</b>（キーは{" "}
                    <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer">
                      Google AI Studio
                    </a>{" "}
                    で作れます）
                  </li>
                  <li>
                    Actions の画面で <b>Run workflow</b> → 緑の <b>Run workflow</b> を押す
                    {gh && (
                      <>
                        {" "}
                        <a className="linkbtn" href={gh.workflow} target="_blank" rel="noopener noreferrer">
                          Actions を開く
                        </a>
                      </>
                    )}
                  </li>
                  <li>3〜5 分待ってから、この画面を再読み込みする</li>
                </ol>
                {ghRun?.conclusion === "failure" && (
                  <p className="error">
                    GitHub の最新の実行が失敗しています（{formatTime(ghRun.created_at, config.tz)}）。鍵の名前と値を見直してください。{" "}
                    <a href={ghRun.html_url} target="_blank" rel="noopener noreferrer">
                      ログを見る
                    </a>
                  </p>
                )}
                <p className="help">
                  記録が出ないまま失敗するときは、DATABASE_URL の名前か値が違っていることが多いです。Actions の画面で赤い × の実行を開くと原因が出ています。
                </p>
              </>
            )}
            {diag && gh && (
              <p>
                <a className="linkbtn" href={gh.secrets} target="_blank" rel="noopener noreferrer">
                  Secrets を開く
                </a>
                <a className="linkbtn" href={gh.workflow} target="_blank" rel="noopener noreferrer">
                  Actions を開く
                </a>
              </p>
            )}
          </Step>

          <Step state={defaultInterests ? "warn" : "ok"} title="あなたの関心">
            {defaultInterests ? (
              <p>
                例の文章のままです。<Link href="/settings">設定</Link> で自分のことに書き換えると、選ばれる記事が良くなります。
              </p>
            ) : (
              <p>書き換え済みです。</p>
            )}
          </Step>

          <Step state={canDispatch() ? "ok" : "optional"} title="画面の「今すぐ集める」（任意）">
            {canDispatch() ? (
              <p>使えます。</p>
            ) : (
              <>
                <p>無くても毎朝自動で届きます。画面から好きなときに集めたい場合だけ設定します。</p>
                <ol>
                  <li>
                    <a
                      href="https://github.com/settings/personal-access-tokens/new"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      GitHub のトークン作成画面
                    </a>{" "}
                    で、Repository access を <b>Only select repositories</b> にしてこのリポジトリを選ぶ
                  </li>
                  <li>
                    Permissions の <b>Actions</b> を <b>Read and write</b> にして <b>Generate token</b>
                  </li>
                  <li>
                    出てきたトークンを Vercel の Environment Variables に <code>PNBA_GITHUB_TOKEN</code> として入れ、Redeploy
                  </li>
                </ol>
              </>
            )}
          </Step>

          <Step state={settings.discord_webhook || config.envWebhook ? "ok" : "optional"} title="Discord への通知（任意）">
            <p>
              {settings.discord_webhook || config.envWebhook ? "設定済みです。" : ""}
              <Link href="/settings">設定</Link> の「Discord Webhook」に URL を入れると、届いたときに知らせます。
            </p>
          </Step>
        </ol>
      </section>
    </>
  );
}
