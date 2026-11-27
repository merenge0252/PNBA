"use client";

import { useState } from "react";

export default function CopyButton({ value, label = "コピー" }: { value: string; label?: string }) {
  const [done, setDone] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      // 古いブラウザや権限が無いとき
      const t = document.createElement("textarea");
      t.value = value;
      document.body.appendChild(t);
      t.select();
      document.execCommand("copy");
      t.remove();
    }
    setDone(true);
    setTimeout(() => setDone(false), 2000);
  }
  return (
    <button type="button" className="secondary small" onClick={copy}>
      {done ? "コピーしました" : label}
    </button>
  );
}
