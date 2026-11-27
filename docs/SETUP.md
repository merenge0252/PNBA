# PNBA はじめての設定（20分）

プログラミングの知識はいりません。上から順番に進めてください。
画面は英語のところが多いですが、押すボタンの名前を **太字** で書いています（サービス側の変更で表示が少し違うことがあります）。

## 準備するもの

| もの | 作り方 |
|---|---|
| Google アカウント | Gmail のアカウントでOK |
| GitHub アカウント | https://github.com/signup で作る（無料） |
| Vercel アカウント | 手順1の途中で「GitHub で続ける」を選べば一緒にできる（無料の Hobby プラン） |

パソコンのブラウザで進めるのがおすすめです（スマホでもできますが画面が狭いです）。

---

## 1. アプリを自分用にコピーして公開する（Vercel）

1. 下のボタンを押す

   [![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fmerenge0252%2FPNBA&env=PNBA_PASSWORD&envDescription=%E3%83%AD%E3%82%B0%E3%82%A4%E3%83%B3%E3%81%AE%E3%83%91%E3%82%B9%E3%83%AF%E3%83%BC%E3%83%89%EF%BC%88%E8%87%AA%E5%88%86%E3%81%A7%E6%B1%BA%E3%82%81%E3%82%8B%EF%BC%89&project-name=pnba&repository-name=pnba)

2. Vercel にログインしていなければ **Continue with GitHub** を選び、GitHub でログインして許可する
3. **Create Git Repository** の欄で
   - Repository Name: `pnba` のままでOK
   - **Create private Git Repository** にチェックを入れる（自分だけが見られる設定）
   - **Create** を押す
4. **PNBA_PASSWORD** の欄に、このアプリに入るときのパスワードを入れる
   - 自分で決めます。12文字以上で、他のサービスと同じにしないもの
   - **忘れないようにメモ**しておいてください
5. **Deploy** を押す。2〜3分待つと「Congratulations」のような完了画面になる
6. **Continue to Dashboard**（またはプロジェクト名）を押して、プロジェクトの画面を開く

## 2. データの保存場所を作る（Neon）

1. プロジェクトの画面の上のメニューから **Storage** を開く
2. **Create Database** を押し、一覧から **Neon** を選んで **Continue**
3. 地域（Region）は日本に近いもの（Tokyo / Singapore など）、プランは **Free** を選んで **Continue** / **Create**
   - 規約の同意を求められたら同意する
4. 「どのプロジェクトにつなぐか」を聞かれたら、さっきの **pnba** を選んで **Connect**
   - 「Custom Prefix」のような欄があれば、空のままにする
5. 上のメニューの **Deployments** を開き、一番上の行の右端 **…** → **Redeploy** → もう一度 **Redeploy**
6. 1〜2分待って完了したら、**Visit**（またはプロジェクト画面に出ている `〜.vercel.app` の URL）を押す
7. 手順1で決めたパスワードでログインする
8. 「セットアップがまだ終わっていません」と出たら成功です。**セットアップ確認** を押す

> この URL がこれからずっと使うアプリの場所です。スマホのホーム画面に追加しておくと便利です。

## 3. AI の鍵（API キー）を作る（Google）

1. https://aistudio.google.com/apikey を開いて Google でログイン
2. 規約の同意を求められたら同意する
3. **Create API key**（API キーを作成）を押す。プロジェクトを聞かれたら新しく作るものを選ぶ
4. 出てきた長い文字列（`AIza` で始まることが多い）の **コピー** を押す
5. メモ帳などに一時的に貼っておく（他人に見せないでください）

> クレジットカードを登録しなければ料金はかかりません。

## 4. 鍵を GitHub に入れる

ここからはアプリの **セットアップ確認** 画面を見ながら進めると簡単です。

1. セットアップ確認の **Secrets を開く** を押す（GitHub の画面が開きます）
2. 1つ目を入れる
   - Name: `DATABASE_URL`
   - Secret: セットアップ確認の **値をコピー** を押してから貼り付け
   - **Add secret** を押す
3. もう一度 **New repository secret** を押して、2つ目を入れる
   - Name: `GEMINI_API_KEY`
   - Secret: 手順3でコピーした AI の鍵を貼り付け
   - **Add secret** を押す

> Name は大文字・アンダーバーまで正確に。前後に空白が入らないように注意してください。

## 5. 1回目を動かす

1. セットアップ確認の **Actions を開く** を押す
   - 「Workflows aren't being run on this repository」のような表示が出たら、緑の **I understand my workflows, go ahead and enable them** を押す
2. 右側の **Run workflow** → 緑の **Run workflow** を押す
3. 3〜5分待って、アプリの **セットアップ確認** を再読み込みする
4. 「必須 3 / 3 完了」になれば完成です 🎉 **今日** を開くと記事が並んでいます

## 6. 自分好みにする

1. アプリの **設定** を開く
2. **あなたの関心** を自分のことに書き換えて **保存**
   - 例: 仕事、趣味、最近気になっていること、近い予定（引っ越し・旅行・買い物など）、読みたくない話題
3. 記事に 👍 / 👎 を付けていくと、だんだん好みに合ってきます

これで毎朝 6時すぎ〜7時ごろ（日本時間）に自動で届きます。

---

## うまくいかないとき

まず **セットアップ確認** を開いてください。何が足りないかと直し方が出ます。

| こうなった | 直し方 |
|---|---|
| ログイン画面に「PNBA_PASSWORD が設定されていません」 | Vercel のプロジェクト → **Settings** → **Environment Variables** で `PNBA_PASSWORD` を追加し、**Deployments** から **Redeploy** |
| 「DATABASE_URL が設定されていません」と出る | 手順2（Neon）をやり直す。Connect の後の **Redeploy** を忘れがち |
| パスワードを忘れた | Vercel の **Settings** → **Environment Variables** で `PNBA_PASSWORD` を編集して新しくし、**Redeploy** |
| 「失敗が続いたので15分ほど待ってください」 | パスワードを5回間違えると15分入れません。待ってから入り直す |
| セットアップ確認が「まだ一度も記録がありません」のまま | GitHub の **Actions** を開き、赤い × の行を押すと原因が出ます。多いのは Secret の Name の打ち間違い |
| 「Gemini の API キーが正しくないようです」 | 手順3で鍵を作り直し、GitHub の Secrets の `GEMINI_API_KEY` を開いて **Update** で貼り直す |
| 朝になっても届かない | GitHub は混んでいると数十分遅れます。お昼を過ぎても来なければ、セットアップ確認か Actions の画面を確認 |
| しばらく使わなかったら届かなくなった | GitHub は長く更新の無いリポジトリの自動実行を止めることがあります。**Actions** の画面で再開ボタンを押す |

それでもわからないときは、セットアップ確認の画面のスクリーンショットを、このアプリをくれた人に送ってください。

## 料金について

Vercel（Hobby）・Neon（Free）・GitHub・Gemini API はどれも無料の範囲で使える想定です。
クレジットカードを登録しなければ、勝手に料金がかかることはありません。
