# 授業欠席管理Discordボット — ゼロから公開までの完全ガイド

このガイドは、何もない状態から
「Discordボットを作る → GitHubに置く → Koyebで24時間稼働させる → GASで起こし続ける」
までを、画面操作レベルで順番に説明します。上から順にやれば完成します。

---

## ステップ0. 事前に必要なアカウント

以下4つのアカウントを用意してください（すでにあるものはスキップ）。

| サービス | 用途 | URL |
|---|---|---|
| Discord | ボット本体・招待先サーバー | https://discord.com |
| GitHub | コードの置き場所（Koyebがここから取得） | https://github.com |
| Koyeb | ボットを24時間動かすサーバー | https://www.koyeb.com |
| Google | GASで10分おきに起こす | https://script.google.com |

クレジットカードは今回どのサービスでも必須ではありません（Koyebは人間確認のため求められる場合がありますが、無料インスタンスの利用自体は無料です）。

---

## ステップ1. Discord Developer PortalでBotを作成する

1. https://discord.com/developers/applications にアクセスし、Discordアカウントでログイン
2. 右上の **「New Application」** をクリック
3. アプリ名を入力（例: 出席管理くん）→ **「Create」**
4. 左メニューの **「Bot」** をクリック
5. 「Bot」ページに表示される **「Reset Token」** をクリックし、表示されたトークンをコピーして、どこかに一時的にメモしておく
   - ⚠️ このトークンは**パスワードと同じくらい重要**です。他人に見せたり、GitHubに直接コミットしたりしないでください。
6. 「Privileged Gateway Intents」の3つのトグル（Presence, Server Members, Message Content）は **すべてOFFのまま**でOKです（このボットはスラッシュコマンドのみで動くため不要）

---

## ステップ2. ボットをあなたのDiscordサーバーに招待する

1. 左メニューの **「OAuth2」** → **「URL Generator」** をクリック
2. 「SCOPES」で以下2つにチェック
   - `bot`
   - `applications.commands`
3. 下に表示される「BOT PERMISSIONS」で以下にチェック
   - `Send Messages`
   - `Embed Links`
   - `Use Slash Commands`
4. 一番下に生成されたURLをコピーし、ブラウザの新しいタブに貼り付けてアクセス
5. 招待したいサーバーを選択 → **「認証」**
6. Discordのサーバーにボットが（オフラインの状態で）追加されていればOK（まだ起動していないのでオフライン表示のままで正常です）

---

## ステップ3. コード一式をGitHubにアップロードする

Koyebは「GitHubリポジトリを見て自動デプロイする」仕組みなので、まずコードをGitHubに置きます。

### 3-1. リポジトリを作成

1. https://github.com にログイン → 右上の **「+」** → **「New repository」**
2. Repository name に `discord-absence-bot` など好きな名前を入力
3. Public / Private どちらでもOK（他人にトークンを見られなければ問題ないですが、`.env` はそもそもアップロードしないので Public でも構いません）
4. 「Add a README file」はチェックしなくてOK（すでにこちらにREADMEがあるため）
5. **「Create repository」**

### 3-2. ファイルをアップロード

一番簡単なのはブラウザから直接アップロードする方法です。

1. 作成したリポジトリのページで **「uploading an existing file」** のリンクをクリック（または「Add file」→「Upload files」）
2. 以前ダウンロードした `discord-absence-bot` フォルダの中身を**フォルダごとドラッグ＆ドロップ**
   - `main.py`, `database.py`, `keep_alive.py`, `Dockerfile`, `requirements.txt`, `README.md`, `.gitignore`, `.dockerignore`, `gas_keep_alive.gs`, `cogs/` フォルダ一式
   - **`.env` ファイルはアップロードしないでください**（トークンが含まれるファイルです。そもそも `.env.example` しか同梱していないので、これはこのままでOK）
3. 下の「Commit changes」欄にコメントを書いて **「Commit changes」**

Gitコマンドに慣れている場合は以下でも同じことができます。

```bash
cd discord-absence-bot
git init
git add .
git commit -m "初回コミット"
git branch -M main
git remote add origin https://github.com/あなたのユーザー名/discord-absence-bot.git
git push -u origin main
```

---

## ステップ4. Koyebにデプロイする

1. https://app.koyeb.com にアクセスし、GitHubアカウントでサインアップ/ログイン
2. ダッシュボードで **「Create Web Service」**（または「Create App」→「Web Service」）
3. デプロイ元で **「GitHub」** を選択し、先ほど作成した `discord-absence-bot` リポジトリを選択
   - 初回はKoyebにGitHubリポジトリへのアクセスを許可する画面が出るので許可する
4. 「Builder」は自動的に **Dockerfile** が検出されるはずです（このリポジトリに `Dockerfile` を含めてあるため）。特に変更不要
5. **「Environment variables」** のセクションで以下を追加
   - Key: `DISCORD_TOKEN`
   - Value: ステップ1でコピーしたボットトークン
   - 種類は **Secret**（暗号化保存）を選択
6. **「Instance」** で無料の **Free** を選択
7. **「Region」** は `Washington, D.C.` か `Frankfurt` を選択（無料枠はこの2つのみ）
8. **「Deploy」** をクリック

デプロイが始まると、ビルドログ・デプロイログが画面に流れます。数分で完了し、
`https://（アプリ名）-（ランダム文字列）.koyeb.app` のようなURLが発行されます。

### 4-1. 動作確認

1. 発行されたURLの末尾に `/health` を付けてブラウザでアクセス
   例: `https://discord-absence-bot-xxxxx.koyeb.app/health`
2. `OK: absence bot is alive` と表示されれば、コンテナが起動してボットも接続を試みています
3. Discordのサーバーメンバー一覧を見て、ボットが **オンライン** になっていればログイン成功です
4. なっていない場合は、Koyebの「Logs」タブでエラーを確認してください（トークンの入力ミスが多い原因です）

---

## ステップ5. GASで10分おきに起こす設定をする

Koyebの無料インスタンスは1時間トラフィックがないとスリープするため、これを防ぎます。

1. https://script.google.com にアクセスし、Googleアカウントでログイン
2. **「新しいプロジェクト」** をクリック
3. デフォルトで表示されているコードを全部削除し、同梱の `gas_keep_alive.gs` の中身を貼り付け
4. コード冒頭の以下の行を、ステップ4で発行されたあなたのURLに書き換える
   ```js
   const KOYEB_URL = 'https://your-app-xxxxxxx.koyeb.app/health';
   ```
5. 左上のプロジェクト名（「無題のプロジェクト」）を「absence-bot-keepalive」などに変更しておくとわかりやすいです
6. 上部の関数選択プルダウンで **`createTrigger`** を選択し、▶️（実行）をクリック
7. 初回は「承認が必要です」という画面が出るので
   - 「権限を確認」→ 自分のGoogleアカウントを選択 →「詳細」→「（プロジェクト名）に移動（安全ではないページ）」→「許可」
   - これはGoogle側の一般的な警告表示で、あなた自身が書いたスクリプトなので問題ありません
8. 実行後、下の「実行ログ」に `10分おきのトリガーを作成しました。` と出れば成功
9. 左メニューの時計アイコン（**トリガー**）を開き、`pingBot` が `時間主導型` `10分おき` で登録されていることを確認

これで10分ごとに自動でKoyebにアクセスが入り、コンテナがスリープしなくなります。

### 停止したいとき

同じ画面で関数選択を `removeTrigger` に変えて実行すると、pingが止まります。

---

## ステップ6. Discord上で動作確認する

サーバーのテキストチャンネルで `/` と入力し、以下のコマンドが候補に出れば成功です。

```
/class add
/class list
/class remove
/class threshold
/class setchannel
/absence add
/absence remove
/absence list
/absence status
```

出てこない場合、コマンド反映（Discord側のスラッシュコマンド同期）に数分〜最大1時間ほどかかることがあります。少し待ってから再度確認してください。

---

## ステップ7. 実際に使ってみる（基本の流れ）

```
# 1. 通知を送るチャンネルを設定（最初に1回だけ）
/class setchannel channel:#授業通知

# 2. 授業を登録
/class add name:線形代数 pattern:毎週 weekday:月曜日 threshold:5

# 3. 欠席したら記録
/absence add class_name:線形代数

# 4. 自分の欠席状況をまとめて確認
/absence status
```

毎日08:00(JST)に自動チェックが走り、その日が授業日で危険ラインに近いユーザーがいれば、
設定したチャンネルに自動で通知されます。

---

## 運用時の注意点（必ず読んでください）

- **再デプロイするとデータが消えます**: Koyebの無料プランは永続ボリュームが使えないため、コードを更新して再デプロイすると `absence_bot.db`（欠席記録）がリセットされます。GASのpingでコンテナが起動し続けている間は消えませんが、コード変更のたびにデータが飛ぶことは理解しておいてください。
- **無料枠の上限**: Koyebの無料インスタンスは1個のみ、512MB RAM / 0.1vCPU です。今回のような小規模ボットには十分ですが、サーバー数が非常に多い場合は動作が重くなる可能性があります。
- **トークンの管理**: `DISCORD_TOKEN` は絶対にGitHubにそのまま書かない（Koyebの「Secret」環境変数機能を必ず使う）。もし誤って公開してしまった場合は、Developer Portalの「Bot」ページからすぐに「Reset Token」してください。
- **長期運用でデータを守りたい場合**: 将来的にデータを絶対に消したくなくなったら、SQLiteの代わりにNeonなどの無料の外部PostgreSQLに切り替える方法があります。必要になったタイミングで対応しますので声をかけてください。

---

以上で、ゼロから24時間稼働のDiscordボットが完成します。詰まったポイントがあれば、そのときの画面やログのエラーメッセージを教えてください。
