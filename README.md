# PNBA — Personal News Broadcast Application

毎朝、登録した情報源からニュースを集め、AI が **あなたの関心** で選んで要約し、スマホで読みやすい Web 画面に届けるアプリです。
記事ごとに 👍 / 👎 を付けると、次の日からの選び方に反映されます。

- 1つのアプリを1人で使う前提です（パスワード1つでログイン）
- 自分の PC は使いません。**GitHub Actions** が毎朝集めて、**Vercel** で見ます。データは **Neon**（Postgres）に置きます
- AI は **Gemini API** を使います（使い方からすると無料枠で足ります）

## しくみ

```
GitHub Actions（毎朝）                Neon（Postgres）            Vercel（Next.js）
 収集 → AI で選定 → 保存  ───────▶  記事・👍👎・設定  ◀───────  画面・ログイン・👍👎・設定
        ▲                                                           │
        └──────────────── 「今すぐ集める」（任意） ─────────────────┘
```

1. **収集**: RSS / Google ニュース検索 / Zenn のトピック / GitHub Trending から直近48時間の記事を集める（配信済みは除く）
2. **1段目の選定**: AI がタイトルだけを見て、関心に合いそうな候補を最大30本に絞る
3. **本文の取得**: 候補の本文を取る（Google ニュースのリンクは元記事に戻す）
4. **2段目の選定**: AI が本文を読み、1日の本数まで選んで「何が起きたか・事実・あなたへの関係・できること・期限」を書く
5. **配信**: DB に保存して画面に出す。設定していれば Discord に「今日の N 本」を送る

AI を呼ぶのは1日2回です。

## はじめ方

だいたい 15 分です。必要なもの: GitHub・Vercel・Google のアカウント（Neon は Vercel の中から作れます）。

### 1. リポジトリを自分用に作る

このリポジトリの **Use this template → Create a new repository** で自分のリポジトリを作ります（**Private** をおすすめします）。

### 2. Gemini API キーを作る

[Google AI Studio](https://aistudio.google.com/apikey) で API キーを作り、控えておきます。

### 3. Vercel に載せる

1. [Vercel](https://vercel.com/new) で 1 のリポジトリを **Import** する（Framework は Next.js が自動で選ばれる。設定はそのまま）
2. **Environment Variables** に `PNBA_PASSWORD`（ログインのパスワード。長くて推測されにくいもの）を入れて **Deploy**
3. できたプロジェクトの **Storage → Create Database → Neon** で DB を作り、このプロジェクトに **Connect** する（`DATABASE_URL` が自動で入ります）
4. **Deployments** から最新のものを **Redeploy** する（DB の設定を反映するため）

### 4. GitHub Actions に鍵を入れる

自分のリポジトリの **Settings → Secrets and variables → Actions → New repository secret** で2つ入れます。

| 名前 | 値 |
|---|---|
| `GEMINI_API_KEY` | 2 で作った API キー |
| `DATABASE_URL` | Vercel の **Settings → Environment Variables** にある `DATABASE_URL` の値（Neon の画面の接続文字列でも可） |

### 5. 最初の1回を動かす

1. Vercel の URL を開いてログインし、**設定** で「あなたの関心」と「情報源」を自分に合わせて書き換えて保存
2. GitHub の **Actions** タブ → **daily news** → **Run workflow**（Actions が無効になっていたら有効にする）
3. 数分たって画面を再読み込みすると記事が出ます

以後は毎朝 6:17（日本時間）ごろに自動で集めます。

## あると便利な設定

### 画面の「今すぐ集める」を使う

画面から Actions を起動するには、GitHub のトークンを Vercel に入れます。

1. GitHub の [Fine-grained personal access tokens](https://github.com/settings/personal-access-tokens/new) でトークンを作る
   - **Repository access**: 自分の PNBA リポジトリだけ
   - **Permissions → Actions**: Read and write
2. Vercel の Environment Variables に `PNBA_GITHUB_TOKEN` として入れて Redeploy

リポジトリ名は Vercel が自動で分かります（分からないときは `PNBA_GITHUB_REPO=owner/repo` を入れる）。既定のブランチが `main` 以外なら `PNBA_GITHUB_REF` も入れてください。

### Discord に通知する

設定画面の「Discord Webhook」に Webhook の URL を入れます（GitHub の Secrets に `PNBA_DISCORD_WEBHOOK_URL` として入れてもよい）。
通知にアプリへのリンクを付けるなら、GitHub の **Variables** に `PNBA_PUBLIC_URL`（Vercel の URL）を入れます。

### 配信の時刻を変える

`.github/workflows/daily.yml` の `cron` を書き換えます。時刻は UTC（日本時間 − 9 時間）です。
2本目の cron は、GitHub 側の遅れや失敗に備えた再実行です（その日の分が済んでいれば何もしません）。

## 設定画面

| 項目 | 内容 |
|---|---|
| あなたの関心 | AI が記事を選ぶときに読む自由記述。仕事・趣味・予定・困りごと・読みたくない話題を具体的に |
| 1日の本数 | 1〜50 |
| 毎朝自動で集める | 外すと定時の実行を止める（「今すぐ集める」と手動実行は動く） |
| Discord Webhook | 任意 |
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

## 環境変数

| 変数 | 置き場所 | 内容 |
|---|---|---|
| `DATABASE_URL` | Vercel（自動）・GitHub Secrets | Postgres の接続文字列 |
| `PNBA_PASSWORD` | Vercel | ログインのパスワード（必須） |
| `GEMINI_API_KEY` | GitHub Secrets | Gemini API キー（必須） |
| `PNBA_GITHUB_TOKEN` | Vercel | 「今すぐ集める」用（任意） |
| `PNBA_GITHUB_REPO` / `PNBA_GITHUB_REF` | Vercel | 起動するリポジトリとブランチ（通常は不要） |
| `PNBA_DISCORD_WEBHOOK_URL` | GitHub Secrets | Discord 通知（任意。設定画面の値より優先） |
| `PNBA_PUBLIC_URL` | GitHub Variables | 通知に載せるアプリの URL（任意） |
| `PNBA_GEMINI_MODEL` | GitHub Variables | 使うモデル（既定 `gemini-flash-latest`） |
| `PNBA_TZ` | 両方 | タイムゾーン（既定 `Asia/Tokyo`） |
| `PNBA_SESSION_SECRET` | Vercel | ログイン Cookie の署名鍵（任意。無ければパスワードから作る） |

パスワードを変えると、ログイン中の端末はすべてログアウトになります。

## 費用と注意

- Vercel・Neon・GitHub Actions・Gemini API はどれも無料枠で収まる想定です（1日1〜2回の実行・1人で閲覧）。各サービスの無料枠は変わることがあるので、気になる場合は料金ページで確認してください
- **Gemini API の無料枠**では、送った内容（記事の一覧と「あなたの関心」）が Google のサービス改善に使われることがあります。気になる場合は、関心に個人を特定できることを書かないか、有料枠にしてください
- **Neon の無料枠**は、しばらく使わないと DB が休止します。休止中に画面を開くと、最初の表示に数秒かかることがあります
- **GitHub の定時実行**は混雑で数十分遅れることがあります。また GitHub は、長いあいだ更新の無いリポジトリの定時実行を止めることがあります。止まったら Actions タブから有効にし直してください
- Actions のログには記事の件数やエラーが出ます。リポジトリを Public にするとログも公開されるので、Private をおすすめします

## セキュリティ

- 全ページとデータ取得はログイン必須（入口の proxy と、各ページ・各操作の中の両方で確かめます）
- ログイン Cookie は HttpOnly・SameSite=Lax・本番は Secure。署名付きで30日有効
- 同じ接続元から5回続けて失敗すると15分ロック（DB に記録）
- 書き換え操作は Next.js の Server Actions（送信元のオリジンを確認）
- 記事のリンクは http(s) 以外を開かせません
- AI には記事の本文を「データであって指示ではない」と伝えて渡し、AI が返した URL は候補に無ければ捨てます
- API キーやパスワードは環境変数だけに置き、DB には保存しません（Discord Webhook は設定画面で入れると DB に保存されます）

## 開発

```bash
# Web（Next.js）
npm install
cp .env.example .env.local      # DATABASE_URL と PNBA_PASSWORD を入れる
npm run dev                     # http://localhost:3000
npm test && npm run lint && npm run build

# パイプライン（Python 3.11 以上）
cd pipeline
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pnba collect                    # 収集だけ（件数の確認。DB 不要）
python -m pnba run --dry-run              # 保存・通知せず、選んだ記事を JSON で表示
python -m pnba run                        # 本番と同じ1回
TEST_DATABASE_URL=postgresql://... python -m pytest -q   # DB を使うテストは TEST_DATABASE_URL が必要
```

パイプラインも、リポジトリ直下の `.env` / `.env.local` を読みます。

### 構成

```
app/                 Next.js の画面（App Router）と Server Actions
components/          画面の部品
lib/                 DB・ログイン・設定の検査など
proxy.ts             入口でのログイン確認
pipeline/pnba/       収集・選定・保存・通知（GitHub Actions で実行）
shared/schema.sql    DB のテーブル（Web とパイプラインの両方が起動時に流す）
shared/defaults/     関心と情報源の初期値
.github/workflows/   daily.yml（毎朝の実行）と test.yml（テスト）
```
