export default function SetupNotice({ message }: { message: string }) {
  return (
    <div className="card setup">
      <h2>設定が足りません</h2>
      <p className="error">{message}</p>
      <p className="help">README の「Vercel に載せる」の手順を確認してください。環境変数を変えたら Vercel で再デプロイが必要です。</p>
    </div>
  );
}
