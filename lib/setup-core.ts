// セットアップの進み具合の判定（画面とテストの共通部分）

export type CheckState = "ok" | "todo" | "warn" | "optional";

export type RunLike = { status: string; message: string } | undefined;

/** 実行記録のエラーメッセージから、利用者が直すべき場所を当てる。 */
export function diagnoseRunError(message: string): { title: string; fix: string } {
  const m = message || "";
  if (/GEMINI_API_KEY/.test(m)) {
    return {
      title: "Gemini の API キーが入っていません",
      fix: "GitHub の Secrets に GEMINI_API_KEY を入れて、もう一度実行してください。",
    };
  }
  if (/Gemini API エラー (400|401|403)/.test(m)) {
    return {
      title: "Gemini の API キーが正しくないようです",
      fix: "Google AI Studio でキーを作り直し、GitHub の Secrets の GEMINI_API_KEY を上書きしてください。",
    };
  }
  if (/Gemini API エラー 404/.test(m)) {
    return {
      title: "Gemini のモデル名が使えません",
      fix: "GitHub の Variables の PNBA_GEMINI_MODEL を消すか、使えるモデル名に変えてください。",
    };
  }
  if (/Gemini API エラー 429|再試行が尽きました/.test(m)) {
    return {
      title: "Gemini の利用上限に当たりました",
      fix: "しばらく待ってから実行してください。毎回起きるなら AI Studio で上限を確認してください。",
    };
  }
  if (/すべての取得に失敗/.test(m)) {
    return {
      title: "ニュースを1件も取れませんでした",
      fix: "設定画面の「情報源」の URL や検索語を見直してください。一時的な障害のこともあります。",
    };
  }
  if (/JSON として読めません/.test(m)) {
    return {
      title: "AI の返事を読み取れませんでした",
      fix: "たまに起きます。もう一度実行してください。続くなら Variables の PNBA_GEMINI_MODEL を変えてみてください。",
    };
  }
  return { title: "実行に失敗しました", fix: "下のエラー内容を確認してください。わからなければ、この画面を作った人に見せてください。" };
}

export function runCheck(last: RunLike, everSucceeded: boolean): CheckState {
  if (!last) return "todo";
  if (last.status === "error") return everSucceeded ? "warn" : "todo";
  if (last.status === "running") return everSucceeded ? "ok" : "warn";
  return "ok";
}

/** 接続文字列のパスワード部分を伏せる。 */
export function maskDatabaseUrl(url: string): string {
  return url.replace(/(\/\/[^:/@]+:)[^@]*@/, "$1••••••@");
}

export function githubLinks(repo: string) {
  const base = `https://github.com/${repo}`;
  return {
    repo: base,
    newSecret: `${base}/settings/secrets/actions/new`,
    secrets: `${base}/settings/secrets/actions`,
    workflow: `${base}/actions/workflows/daily.yml`,
    actions: `${base}/actions`,
  };
}
