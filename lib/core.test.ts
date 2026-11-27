import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDay, formatTime, isDay, todayIn } from "./format.ts";
import { passwordMatches, sessionKey, signSession, verifySession } from "./session-core.ts";
import { parseSettingsForm, SettingsError, validateSources } from "./settings-core.ts";

test("session: sign and verify", async () => {
  const key = await sessionKey("pw");
  const token = await signSession(key);
  assert.equal(await verifySession(key, token), true);
  assert.equal(await verifySession(key, undefined), false);
  assert.equal(await verifySession(key, "garbage"), false);
  // 改ざん
  const [v, exp, sig] = token.split(".");
  assert.equal(await verifySession(key, `${v}.${Number(exp) + 1}.${sig}`), false);
  // 期限切れ
  assert.equal(await verifySession(key, token, Date.now() + 31 * 24 * 3600 * 1000), false);
  // パスワードを変えると無効
  assert.equal(await verifySession(await sessionKey("other"), token), false);
  // 秘密鍵があればそちらを使う
  const k2 = await sessionKey("pw", "secret");
  assert.equal(await verifySession(k2, token), false);
  assert.equal(await verifySession(k2, await signSession(k2)), true);
});

test("password compare", async () => {
  assert.equal(await passwordMatches("abc", "abc"), true);
  assert.equal(await passwordMatches("abd", "abc"), false);
  assert.equal(await passwordMatches("", ""), false); // 未設定なら誰も入れない
});

const SOURCES = JSON.stringify({ categories: { A: { about: "x", rss: [{ url: "https://e.com/f" }], google_news: ["q"] } } });

test("settings: valid form", () => {
  const s = parseSettingsForm({ interests: " 猫 ", per_day: "5", schedule_enabled: "1", discord_webhook: "", sources: SOURCES });
  assert.deepEqual(s, {
    interests: "猫",
    per_day: 5,
    schedule_enabled: true,
    discord_webhook: "",
    sources: JSON.parse(SOURCES),
  });
  assert.equal(parseSettingsForm({ per_day: "1", schedule_enabled: null, sources: SOURCES }).schedule_enabled, false);
});

test("settings: invalid input", () => {
  const base = { interests: "", per_day: "5", discord_webhook: "", sources: SOURCES };
  const bad = [
    { per_day: "0" },
    { per_day: "51" },
    { per_day: "2.5" },
    { discord_webhook: "https://evil.example/hook" },
    { sources: "{" },
    { sources: '{"categories": {}}' },
    { sources: '{"categories": {"A": {"rss": [{"url": "file:///etc/passwd"}]}}}' },
    { sources: '{"categories": {"A": {"google_news": "not a list"}}}' },
    { interests: "x".repeat(20001) },
  ];
  for (const b of bad) {
    assert.throws(() => parseSettingsForm({ ...base, ...b }), SettingsError, JSON.stringify(b).slice(0, 80));
  }
  assert.throws(() => validateSources("[]"), SettingsError);
});

test("format", () => {
  assert.equal(formatDay("2026-11-27"), "11/27（金）");
  assert.equal(formatDay("bad"), "bad");
  assert.equal(isDay("2026-01-02"), true);
  assert.equal(isDay("2026-1-2"), false);
  assert.equal(todayIn("Asia/Tokyo", new Date("2026-11-27T16:00:00Z")), "2026-11-28");
  assert.equal(formatTime("2026-11-26T21:17:00Z", "Asia/Tokyo"), "11/27 06:17");
});
