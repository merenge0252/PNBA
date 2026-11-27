(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const post = (url, body) => fetch(url, {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(body || {}),
  });

  // 👍 / 👎（もう一度押すと取り消し）
  document.addEventListener("click", async (ev) => {
    const btn = ev.target.closest(".vote");
    if (!btn) return;
    const card = btn.closest("[data-id]");
    const value = btn.classList.contains("on") ? "" : btn.dataset.value;
    const r = await post(`/api/feedback/${card.dataset.id}`, { value });
    if (r.status === 401) { location.href = "/login"; return; }
    if (!r.ok) return;
    card.querySelectorAll(".vote").forEach((b) => {
      const on = b.dataset.value === value;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  });

  // 今すぐ集める
  const runBtn = document.getElementById("run-now");
  const runStatus = document.getElementById("runstatus");
  const poll = async () => {
    const r = await fetch("/api/status", { credentials: "same-origin" });
    if (!r.ok) return;
    const s = await r.json();
    if (s.running) { setTimeout(poll, 4000); return; }
    const last = s.last_run;
    if (last && last.status === "error") {
      runBtn.disabled = false; runBtn.textContent = "今すぐ集める";
      runStatus.textContent = "失敗しました（設定画面の「実行の記録」を確認してください）";
      runStatus.classList.add("error");
    } else {
      location.href = "/";
    }
  };
  if (runBtn) {
    runBtn.addEventListener("click", async () => {
      runBtn.disabled = true; runBtn.textContent = "実行中…";
      runStatus.textContent = "記事を集めて AI が選んでいます（数分かかります）";
      runStatus.classList.remove("error");
      const r = await post("/api/run");
      if (r.status === 401) { location.href = "/login"; return; }
      setTimeout(poll, 4000);
    });
    if (runBtn.disabled) setTimeout(poll, 4000);
  }
})();
