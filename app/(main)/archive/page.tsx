import Link from "next/link";
import ArticleCard from "@/components/ArticleCard";
import SetupNotice from "@/components/SetupNotice";
import { articleDays, categories, searchArticles } from "@/lib/data";
import { SetupError } from "@/lib/db";
import { formatDay } from "@/lib/format";
import { requireLogin } from "@/lib/session";

type Params = { q?: string; category?: string; feedback?: string };

export default async function ArchivePage({ searchParams }: { searchParams: Promise<Params> }) {
  await requireLogin();
  const p = await searchParams;
  const q = (typeof p.q === "string" ? p.q : "").trim().slice(0, 100);
  const category = typeof p.category === "string" ? p.category.slice(0, 40) : "";
  const feedback = p.feedback === "up" || p.feedback === "down" ? p.feedback : "";
  const filtered = Boolean(q || category || feedback);

  let articles, cats, days;
  try {
    [articles, cats, days] = await Promise.all([
      searchArticles({ q, category, feedback, limit: filtered ? 200 : 60 }),
      categories(),
      articleDays(30),
    ]);
  } catch (e) {
    if (e instanceof SetupError) return <SetupNotice message={e.message} />;
    throw e;
  }

  return (
    <>
      <h1>過去の記事</h1>
      <form method="get" action="/archive" className="filters">
        <input type="search" name="q" defaultValue={q} placeholder="キーワード" />
        <select name="category" defaultValue={category}>
          <option value="">すべてのカテゴリ</option>
          {cats.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select name="feedback" defaultValue={feedback}>
          <option value="">反応すべて</option>
          <option value="up">👍 だけ</option>
          <option value="down">👎 だけ</option>
        </select>
        <button className="secondary">絞り込む</button>
      </form>
      {!filtered && days.length > 0 && (
        <p className="days">
          {days.map((d) => (
            <Link key={d.day} href={`/?day=${d.day}`}>
              {formatDay(d.day)}
              <small>{d.n}</small>
            </Link>
          ))}
        </p>
      )}
      {articles.length === 0 && <p className="muted">該当する記事はありません。</p>}
      {articles.map((a) => (
        <ArticleCard key={a.id} a={a} showDay />
      ))}
    </>
  );
}
