import { NextResponse } from "next/server";
import { lastRuns } from "@/lib/data";
import { isLoggedIn } from "@/lib/session";

// 「今すぐ集める」の進み具合（最新の実行記録）
export async function GET() {
  if (!(await isLoggedIn())) {
    return NextResponse.json({ error: "login required" }, { status: 401 });
  }
  const [last] = await lastRuns(1);
  return NextResponse.json({ last_run: last ?? null }, { headers: { "Cache-Control": "no-store" } });
}
