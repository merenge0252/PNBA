import type { Article } from "@/lib/data";
import { formatDay } from "@/lib/format";
import FeedbackButtons from "./FeedbackButtons";

export default function ArticleCard({ a, showDay = false }: { a: Article; showDay?: boolean }) {
  return (
    <article className={`card news${a.top ? " top" : ""}`}>
      <div className="meta">
        <span className="cat">{a.category}</span>
        <span className="pub">{a.publisher || a.source}</span>
        {showDay && <span className="date">{formatDay(a.day)}</span>}
        {a.deadline && <span className="deadline">期限 {a.deadline}</span>}
      </div>
      <h2>
        <a href={safeUrl(a.url)} target="_blank" rel="noopener noreferrer">
          {a.headline || a.title}
        </a>
      </h2>
      {a.facts && <p className="facts">{a.facts}</p>}
      {a.why_me && (
        <p className="why">
          <b>あなたに</b>
          {a.why_me}
        </p>
      )}
      {a.action && (
        <p className="action">
          <b>できること</b>
          {a.action}
        </p>
      )}
      <FeedbackButtons id={a.id} initial={a.feedback} />
    </article>
  );
}

/** http(s) 以外（javascript: など）のリンクは開かせない。 */
function safeUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : "#";
}
