"use server";

import { refresh } from "next/cache";
import { redirect } from "next/navigation";
import { clearLoginFails, LOCK_MINUTES, loginLocked, recordLoginFail, saveSettings, setFeedback } from "@/lib/data";
import { config } from "@/lib/env";
import { dispatchRun } from "@/lib/github";
import { clientIp, endSession, isLoggedIn, requireLogin, startSession } from "@/lib/session";
import { passwordMatches } from "@/lib/session-core";
import { parseSettingsForm, SettingsError } from "@/lib/settings-core";

export type FormState = { error?: string; ok?: string };

// ---------- ログイン ----------

export async function login(_prev: FormState, form: FormData): Promise<FormState> {
  if (!config.password) {
    return { error: "サーバーに PNBA_PASSWORD が設定されていません（Vercel の環境変数に入れてください）" };
  }
  const ip = await clientIp();
  if (await loginLocked(ip)) {
    return { error: `失敗が続いたので ${LOCK_MINUTES} 分ほど待ってください` };
  }
  if (!(await passwordMatches(String(form.get("password") ?? ""), config.password))) {
    await recordLoginFail(ip);
    return { error: "パスワードが違います" };
  }
  await clearLoginFails(ip);
  await startSession();
  redirect("/");
}

export async function logout(): Promise<void> {
  await endSession();
  redirect("/login");
}

// ---------- 👍 / 👎 ----------

export async function vote(id: string, value: "" | "up" | "down"): Promise<{ ok: boolean }> {
  if (!(await isLoggedIn())) return { ok: false };
  if (!["", "up", "down"].includes(value) || !/^[0-9a-f]{6,40}$/.test(id)) return { ok: false };
  return { ok: await setFeedback(id, value) };
}

// ---------- 今すぐ集める ----------

export async function runNow(): Promise<FormState> {
  if (!(await isLoggedIn())) return { error: "ログインし直してください" };
  try {
    await dispatchRun();
    return { ok: "started" };
  } catch (e) {
    return { error: (e as Error).message };
  }
}

// ---------- 設定 ----------

export async function updateSettings(_prev: FormState, form: FormData): Promise<FormState> {
  await requireLogin();
  try {
    const s = parseSettingsForm({
      interests: String(form.get("interests") ?? ""),
      per_day: String(form.get("per_day") ?? ""),
      schedule_enabled: form.get("schedule_enabled") as string | null,
      discord_webhook: String(form.get("discord_webhook") ?? ""),
      sources: String(form.get("sources") ?? ""),
    });
    await saveSettings(s);
  } catch (e) {
    if (e instanceof SettingsError) return { error: e.message };
    throw e;
  }
  refresh();
  return { ok: "保存しました" };
}
