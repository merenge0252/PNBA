# PNBA — Personal News Broadcast Application

毎朝、登録した情報源からニュースを集め、AI が **あなたの関心** で選んで要約し、スマホで読みやすい Web 画面に届けるアプリです。
記事ごとに 👍 / 👎 を付けると、次の日からの選び方に反映されます。

- 1つのインスタンスを1人で使う前提です（自分の PC や小さなサーバーで動かします）
- AI は **Gemini API（無料枠で足ります）** か、API キーが無ければ **`agy -p`** を使います
- 関心・情報源・記事の履歴はすべて `data/` に保存され、Git には入りません

## しくみ

1. **収集**: RSS / Google ニュース検索 / Zenn のトピック / GitHub Trending から直近48時間の記事を集める（配信済みは除く）
2. **1段目の選定**: AI がタイトルだけを見て、関心に合いそうな候補を最大30本に絞る
3. **本文の取得**: 候補の本文を取る（Google ニュースのリンクは元記事に戻す）
4. **2段目の選定**: AI が本文を読み、1日の本数まで選んで「何が起きたか・事実・あなたへの関係・できること・期限」を書く
5. **配信**: 画面に表示し、設定していれば Discord に「今日の N 本」を通知

1日に AI を呼ぶのは2回程度です。

## はじめ方（自分の PC）

Python 3.11 以上が必要です。

```bash
git clone https://github.com/merenge0252/pnba.git
cd pnba
python -m venv .venv
source .venv/bin/activate          # Windows は .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows は copy .env.example .env
```

`.env` を開いて、AI の設定をします（どちらか）。

- **Gemini API を使う（おすすめ）**: [Google AI Studio](https://aistudio.google.com/apikey) で API キーを作り、`GEMINI_API_KEY=` に貼る
- **agy を使う**: `agy` をインストールしてログインしておく（`GEMINI_API_KEY` は空のまま）

起動します。

```bash
python -m app serve
```

ブラウザで http://127.0.0.1:8000 を開き、**設定** で「あなたの関心」と「情報源」を自分に合わせて書き換え、トップの **今すぐ集める** を押します（数分かかります）。
以後は毎朝、設定した時刻に自動で集めます。PC が止まっていた日は、次に起動したときに集めます。

### Gemini API の無料枠について

- クレジットカードを登録しなければ課金はされません。PNBA の使い方（1日数回）なら無料枠の制限に届くことはまずありません
- 無料枠では、送った内容（記事の一覧と「あなたの関心」）が Google のサービス改善に使われることがあります。気になる場合は関心に個人を特定できることを書かないか、有料枠にしてください
- 使えるモデルや制限は変わることがあります。最新の情報は AI Studio の料金ページで確認してください。モデルは `PNBA_GEMINI_MODEL` で変えられます

## 外（スマホ）から見る

外から開けるようにするときは、**必ず `PNBA_PASSWORD` を設定してください**。パスワードが無いと、`127.0.0.1` 以外では起動しません。

### A. 自宅の PC で動かして、スマホから見る

PC を外に直接公開せずに済む方法がおすすめです。

- **Tailscale**: PC とスマホの両方に Tailscale を入れ、`PNBA_HOST=0.0.0.0` で起動。スマホから `http://<PC の Tailscale 名>:8000` を開く（自分の端末だけからつながります）
- **Cloudflare Tunnel**: `cloudflared tunnel --url http://127.0.0.1:8000` などで HTTPS の URL を作る。`.env` に `PNBA_SECURE_COOKIE=1` と `PNBA_TRUST_PROXY=1` を入れる

PC が寝ていると朝の収集が遅れます（起きたときに回収されます）。

### B. VPS で常に動かす（Docker）

```bash
cp .env.example .env               # GEMINI_API_KEY と PNBA_PASSWORD を入れる
cp Caddyfile.example Caddyfile     # ドメインを書き換える
docker compose up -d
```

Caddy が HTTPS の証明書を自動で取ります。データは Docker ボリューム `pnba-data` に残ります。

## 設定

画面の **設定** で変えられるもの:

| 項目 | 内容 |
|---|---|
| あなたの関心 | AI が記事を選ぶときに読む自由記述。仕事・趣味・予定・困りごと・読みたくない話題を具体的に |
| 1日の本数 | 1〜50 |
| 配信時刻 | 毎朝この時刻を過ぎたら集める（失敗したら30分おきに3回まで再試行） |
| Discord Webhook | 任意。「今日の N 本」と見出しを送る |
| AI | 自動 / Gemini API / agy -p |
| 情報源 | 下の JSON |

### 情報源の書き方

```json
{
  "locale": {"hl": "ja", "gl": "JP"},
  "categories": {
    "AI": {
      "about": "生成 AI の公式アップデート。入門記事は選ばない",
      "rss": [{"name": "Gemini CLI リリース", "url": "https://github.com/google-gemini/gemini-cli/releases.atom"}],
      "google_news": ["Anthropic Claude 発表 OR 新機能"],
      "zenn_topics": ["python"],
      "github_trending_keywords": ["llm", "agent"]
    }
  }
}
```

- `about`: そのカテゴリでどんな記事が欲しいか（AI が読みます）。いらない種類も書くと精度が上がります
- `rss`: RSS / Atom の URL
- `google_news`: Google ニュースの検索語（`OR` が使えます）。言語と地域は `locale` で変えられます
- `zenn_topics`: Zenn のトピック名
- `github_trending_keywords`: GitHub Trending のリポジトリ名・説明に含まれていたら拾う語

### 環境変数

`.env.example` に一覧と説明があります。主なもの:

| 変数 | 内容 |
|---|---|
| `GEMINI_API_KEY` | Gemini API キー |
| `PNBA_GEMINI_MODEL` | 使うモデル（既定 `gemini-flash-latest`） |
| `PNBA_AGY_CMD` / `PNBA_AGY_MODEL` | agy のコマンドとモデル |
| `PNBA_PASSWORD` | ログインのパスワード |
| `PNBA_HOST` / `PNBA_PORT` | 待ち受け（既定 `127.0.0.1:8000`） |
| `PNBA_SECURE_COOKIE` | HTTPS で公開するなら `1` |
| `PNBA_TRUST_PROXY` | リバースプロキシの後ろなら `1` |
| `PNBA_TZ` | タイムゾーン（既定 `Asia/Tokyo`） |
| `PNBA_DATA_DIR` | データの置き場所（既定 `./data`） |
| `PNBA_DISCORD_WEBHOOK_URL` / `PNBA_PUBLIC_URL` | 通知先と、通知に載せるこのアプリの URL |

## コマンド

```bash
python -m app serve            # Web アプリ（定時実行つき）
python -m app run              # 今すぐ1回
python -m app run --dry-run    # 保存・通知せず、選んだ記事を JSON で表示
python -m app collect          # 収集だけ（カテゴリごとの件数を確認）
```

## セキュリティ

- ログインは Cookie セッション（30日）。同じ接続元から5回失敗すると15分ロックします
- フォームと API は CSRF トークンで守っています
- API キーやパスワードは環境変数だけに置き、画面や DB には保存しません（Discord Webhook は設定画面でも入れられ、その場合は DB に保存されます）
- 記事の本文は AI に「データであって指示ではない」と伝えて渡し、AI が返した URL は候補に無ければ捨てます

## 開発

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## 由来

個人用の自動化ツール群の中にあった「情報部」（ニュース配信）を切り出し、誰でも使える Web アプリにしたものです。
