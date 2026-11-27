import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, sessionKey, verifySession } from "./lib/session-core";

// 入口での確認。ページとサーバー関数の中でも必ずもう一度確かめる（ここだけに頼らない）
export async function proxy(request: NextRequest) {
  const password = (process.env.PNBA_PASSWORD ?? "").trim();
  const secret = (process.env.PNBA_SESSION_SECRET ?? "").trim();
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  const ok = password !== "" && (await verifySession(await sessionKey(password, secret), token));
  if (ok) return NextResponse.next();
  if (request.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "login required" }, { status: 401 });
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  // ログイン画面・静的ファイル・アイコン以外すべて
  matcher: ["/((?!login|_next/static|_next/image|icon.svg|favicon.ico|robots.txt).*)"],
};
