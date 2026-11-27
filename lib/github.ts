import "server-only";
import { config } from "./env";

export function canDispatch(): boolean {
  return Boolean(config.githubToken && config.githubRepo);
}

/** GitHub Actions の daily ワークフローを起動する（「今すぐ集める」）。 */
export async function dispatchRun(): Promise<void> {
  if (!canDispatch()) {
    throw new Error("PNBA_GITHUB_TOKEN が設定されていません");
  }
  const res = await fetch(`${config.githubApi}/repos/${config.githubRepo}/actions/workflows/daily.yml/dispatches`, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${config.githubToken}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ref: config.githubRef, inputs: { trigger: "web" } }),
    cache: "no-store",
  });
  if (!res.ok) {
    const text = (await res.text()).slice(0, 300);
    throw new Error(`GitHub が起動を受け付けませんでした（${res.status}）: ${text}`);
  }
}

export type WorkflowRun = { status: string; conclusion: string | null; html_url: string; created_at: string };

/** daily ワークフローの最新の実行（トークンがあるときだけ。取れなければ null）。 */
export async function latestWorkflowRun(): Promise<WorkflowRun | null> {
  if (!canDispatch()) return null;
  try {
    const res = await fetch(
      `${config.githubApi}/repos/${config.githubRepo}/actions/workflows/daily.yml/runs?per_page=1`,
      {
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${config.githubToken}`,
          "X-GitHub-Api-Version": "2022-11-28",
        },
        cache: "no-store",
        signal: AbortSignal.timeout(5000),
      },
    );
    if (!res.ok) return null;
    const body = (await res.json()) as { workflow_runs?: WorkflowRun[] };
    return body.workflow_runs?.[0] ?? null;
  } catch {
    return null;
  }
}
