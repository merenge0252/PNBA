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
