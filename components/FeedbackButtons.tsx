"use client";

import { useState, useTransition } from "react";
import { vote } from "@/app/actions";

type Value = "" | "up" | "down";

export default function FeedbackButtons({ id, initial }: { id: string; initial: Value }) {
  const [value, setValue] = useState<Value>(initial);
  const [pending, startTransition] = useTransition();

  function press(v: "up" | "down") {
    const next: Value = value === v ? "" : v; // もう一度押すと取り消し
    const prev = value;
    setValue(next);
    startTransition(async () => {
      const r = await vote(id, next);
      if (!r.ok) setValue(prev);
    });
  }

  return (
    <div className="fb" aria-busy={pending}>
      <button
        className={`vote${value === "up" ? " on" : ""}`}
        aria-label="よかった"
        aria-pressed={value === "up"}
        onClick={() => press("up")}
      >
        👍
      </button>
      <button
        className={`vote${value === "down" ? " on" : ""}`}
        aria-label="いらなかった"
        aria-pressed={value === "down"}
        onClick={() => press("down")}
      >
        👎
      </button>
    </div>
  );
}
