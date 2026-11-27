import Link from "next/link";
import ArticleCard from "@/components/ArticleCard";
import RunButton from "@/components/RunButton";
import SetupNotice from "@/components/SetupNotice";
import { articleDays, articlesForDay, everSucceeded, lastRuns } from "@/lib/data";
import { SetupError } from "@/lib/db";
import { config } from "@/lib/env";
import { formatDay, formatTime, isDay, todayIn } from "@/lib/format";
import { canDispatch } from "@/lib/github";
import { requireLogin } from "@/lib/session";

export default async function TodayPage({ searchParams }: { searchParams: Promise<{ day?: string }> }) {
  await requireLogin();
  const { day: dayParam } = await searchParams;
  const today = todayIn(config.tz);

  let days, runs, ready;
  try {
    [days, runs, ready] = await Promise.all([articleDays(), lastRuns(1), everSucceeded()]);
  } catch (e) {
    if (e instanceof SetupError) return <SetupNotice message={e.message} />;
    throw e;
  }
  const day = isDay(dayParam) ? dayParam : (days[0]?.day ?? today);
  const articles = await articlesForDay(day);
  const idx = days.findIndex((d) => d.day === day);
  const prevDay = idx >= 0 && idx + 1 < days.length ? days[idx + 1].day : "";
  const nextDay = idx > 0 ? days[idx - 1].day : "";
  const last = runs[0];
  const top = articles.filter((a) => a.top);
  const rest = articles.filter((a) => !a.top);

  return (
    <>
      <section className="dayhead">
        {prevDay ? (
          <Link className="nav-day" href={`/?day=${prevDay}`} aria-label="前の日">
            ‹
          </Link>
        ) : (
          <span className="nav-day" />
        )}
        <h1>
          {formatDay(day)}
          {day === today && <small> 今日</small>}
        </h1>
        {nextDay ? (
          <Link className="nav-day" href={`/?day=${nextDay}`} aria-label="次の日">
            ›
          </Link>
        ) : (
          <span className="nav-day" />
        )}
      </section>

      {!ready && (
        <div className="card banner">
          <p>
            <b>セットアップがまだ終わっていません。</b>
          </p>
          <p>
            <Link href="/setup">セットアップ確認</Link> を開くと、次にやることが順番に出ます。
          </p>
        </div>
      )}

      <RunButton enabled={canDispatch()} lastRunId={last?.id ?? 0} initiallyRunning={last?.status === "running"} />
      {last && (
        <p className="runstatus center">
          前回 {formatTime(last.started_at, config.tz)}{" "}
          {last.status === "ok" && `${last.picked}本`}
          {last.status === "empty" && "新着なし"}
          {last.status === "running" && "実行中"}
          {last.status === "error" && <span className="error">失敗（設定画面の「実行の記録」を確認）</span>}
        </p>
      )}

      {articles.length === 0 && (
        <div className="card empty">
          <p>この日の記事はまだありません。</p>
          <p>
            はじめての方は <Link href="/setup">セットアップ確認</Link> の手順に沿って進めてください。毎朝
            6:17（日本時間）ごろに届きます。
          </p>
        </div>
      )}

      {top.length > 0 && <h2 className="section">まず読む</h2>}
      {top.map((a) => (
        <ArticleCard key={a.id} a={a} />
      ))}
      {rest.length > 0 && <h2 className="section">ほかのニュース</h2>}
      {rest.map((a) => (
        <ArticleCard key={a.id} a={a} />
      ))}
    </>
  );
}
