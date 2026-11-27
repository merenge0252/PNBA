"use client";

import { useActionState } from "react";
import { login, type FormState } from "@/app/actions";

export default function LoginForm({ configured }: { configured: boolean }) {
  const [state, action, pending] = useActionState<FormState, FormData>(login, {});
  return (
    <form action={action} className="card login">
      <h1>PNBA</h1>
      {!configured && (
        <p className="error">
          サーバーに PNBA_PASSWORD が設定されていません。Vercel の環境変数に入れて、再デプロイしてください。
        </p>
      )}
      {state.error && <p className="error">{state.error}</p>}
      <label>
        パスワード
        <input type="password" name="password" autoComplete="current-password" autoFocus required />
      </label>
      <button className="primary" disabled={pending || !configured}>
        {pending ? "確認中…" : "ログイン"}
      </button>
    </form>
  );
}
