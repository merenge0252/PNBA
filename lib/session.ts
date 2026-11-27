import "server-only";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { config } from "./env";
import { SESSION_COOKIE, SESSION_DAYS, sessionKey, signSession, verifySession } from "./session-core";

function key() {
  return sessionKey(config.password, config.sessionSecret);
}

export async function isLoggedIn(): Promise<boolean> {
  // 先に Cookie を読む（リクエストごとに判定させる。パスワード未設定のビルド時に結果が固定されないように）
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!config.password) return false;
  return verifySession(await key(), token);
}

/** ログインしていなければログイン画面へ。ページとサーバー関数の最初で呼ぶ（proxy だけに頼らない）。 */
export async function requireLogin(): Promise<void> {
  if (!(await isLoggedIn())) redirect("/login");
}

export async function startSession(): Promise<void> {
  (await cookies()).set(SESSION_COOKIE, await signSession(await key()), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_DAYS * 24 * 3600,
  });
}

export async function endSession(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
}

export async function clientIp(): Promise<string> {
  const h = await headers();
  return h.get("x-real-ip") || h.get("x-forwarded-for")?.split(",")[0].trim() || "unknown";
}
