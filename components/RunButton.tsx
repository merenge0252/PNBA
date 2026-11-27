"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { runNow } from "@/app/actions";

type RunInfo = { id: number; status: string; picked: number; message: string } | null;

const POLL_MS = 5000;
const GIVE_UP_MS = 20 * 60 * 1000;

export default function RunButton({
  enabled,
  lastRunId,
  initiallyRunning,
}: {
  enabled: boolean;
  lastRunId: number;
  initiallyRunning: boolean;
}) {
  const router = useRouter();
  const [state, setState] = useState<"idle" | "waiting" | "running" | "error">(
    initiallyRunning ? "running" : "idle",
  );
  const [message, setMessage] = useState("");
  const since = useRef(lastRunId);
  const startedAt = useRef(0);

  useEffect(() => {
    if (state !== "waiting" && state !== "running") return;
    if (!startedAt.current) startedAt.current = Date.now();
    const timer = setInterval(async () => {
      if (Date.now() - startedAt.current > GIVE_UP_MS) {
        setState("error");
        setMessage("時間がかかっています。GitHub の Actions 画面で進み具合を確認してください");
        return;
      }
      const res = await fetch("/api/status", { cache: "no-store" });
      if (res.status === 401) {
        router.push("/login");
        return;
      }
      if (!res.ok) return;
      const { last_run }: { last_run: RunInfo } = await res.json();
      if (!last_run) return;
      // 起動待ちのあいだは前回の記録が返る。新しい記録が出てくるまで待つ
      if (state === "waiting" && last_run.id <= since.current) return;
      if (last_run.status === "running") {
        setState("running");
        setMessage("記事を集めて AI が選んでいます（数分かかります）");
        return;
      }
      if (last_run.status === "error") {
        setState("error");
        setMessage(`失敗しました: ${last_run.message.slice(0, 160)}`);
        return;
      }
      setState("idle");
      setMessage(last_run.status === "ok" ? `${last_run.picked}本届きました` : "新しい記事はありませんでした");
      router.refresh();
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [state, router]);

  async function start() {
    setState("waiting");
    setMessage("GitHub Actions を起動しています（動き出すまで 30 秒ほどかかります）");
    startedAt.current = Date.now();
    const r = await runNow();
    if (r.error) {
      setState("error");
      setMessage(r.error);
    }
  }

  const busy = state === "waiting" || state === "running";
  return (
    <div className="runbox">
      <button className="secondary" onClick={start} disabled={!enabled || busy}>
        {busy ? "実行中…" : "今すぐ集める"}
      </button>
      {message && <span className={`runstatus${state === "error" ? " error" : ""}`}>{message}</span>}
      {!enabled && (
        <span className="hint">
          画面から起動するには PNBA_GITHUB_TOKEN の設定が必要です（README 参照）。GitHub の Actions 画面からも実行できます。
        </span>
      )}
    </div>
  );
}
