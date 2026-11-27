const WEEKDAYS = "日月火水木金土";

/** タイムゾーン tz での今日（YYYY-MM-DD）。 */
export function todayIn(tz: string, now = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
}

/** 2026-11-27 → 11/27（金） */
export function formatDay(day: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(day);
  if (!m) return day;
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  return `${Number(m[2])}/${Number(m[3])}（${WEEKDAYS[d.getUTCDay()]}）`;
}

/** 日時を tz で「11/27 06:20」にする。 */
export function formatTime(value: string | Date | null, tz: string): string {
  if (!value) return "";
  const d = typeof value === "string" ? new Date(value) : value;
  const parts = new Intl.DateTimeFormat("ja-JP", {
    timeZone: tz, month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return `${get("month")}/${get("day")} ${get("hour")}:${get("minute")}`;
}

export function isDay(s: string | undefined): s is string {
  return typeof s === "string" && /^\d{4}-\d{2}-\d{2}$/.test(s);
}
