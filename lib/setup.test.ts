import assert from "node:assert/strict";
import { test } from "node:test";
import { diagnoseRunError, githubLinks, maskDatabaseUrl, runCheck } from "./setup-core.ts";

test("diagnose run errors", () => {
  assert.match(diagnoseRunError("GEMINI_API_KEY が設定されていません").title, /入っていません/);
  assert.match(diagnoseRunError("Gemini API エラー 400: API key not valid").title, /正しくない/);
  assert.match(diagnoseRunError("Gemini API エラー 404: model not found").title, /モデル名/);
  assert.match(diagnoseRunError("Gemini API エラー 429: quota").title, /上限/);
  assert.match(diagnoseRunError("情報源 3 件すべての取得に失敗しました").title, /1件も/);
  assert.match(diagnoseRunError("AI の返答が JSON として読めません").title, /読み取れません/);
  assert.equal(diagnoseRunError("something else").title, "実行に失敗しました");
});

test("run check state", () => {
  assert.equal(runCheck(undefined, false), "todo");
  assert.equal(runCheck({ status: "error", message: "" }, false), "todo");
  assert.equal(runCheck({ status: "error", message: "" }, true), "warn");
  assert.equal(runCheck({ status: "running", message: "" }, false), "warn");
  assert.equal(runCheck({ status: "ok", message: "" }, false), "ok");
  assert.equal(runCheck({ status: "empty", message: "" }, true), "ok");
});

test("mask database url", () => {
  assert.equal(
    maskDatabaseUrl("postgresql://user:s3cr3t@ep-x.neon.tech/db?sslmode=require"),
    "postgresql://user:••••••@ep-x.neon.tech/db?sslmode=require",
  );
  assert.equal(maskDatabaseUrl("postgresql://host/db"), "postgresql://host/db");
});

test("github links", () => {
  assert.equal(githubLinks("me/pnba").newSecret, "https://github.com/me/pnba/settings/secrets/actions/new");
  assert.equal(githubLinks("me/pnba").workflow, "https://github.com/me/pnba/actions/workflows/daily.yml");
});
