# 授業欠席管理Discordボット

授業ごとの欠席回数を記録し、授業当日に「危険ライン」に近い人へ自動で通知するDiscordボットです。
毎週開講の授業だけでなく、隔週授業や特定日のみの授業にも対応しています。

## 機能

- `/class add` … 授業を登録（毎週 / 隔週 / 特定日のみ、危険ラインとなる欠席回数を設定）
- `/class list` … 登録済み授業の一覧表示
- `/class remove` … 授業の削除
- `/class threshold` … 危険ラインの変更
- `/class setchannel` … 通知を送るチャンネルの設定
- `/absence add` … 欠席を1回記録
- `/absence remove` … 直近の欠席記録を取り消し
- `/absence list` … 特定授業の欠席日一覧
- `/absence status` … 自分の全授業の欠席状況をまとめて確認
- 毎日 **08:00 (JST)** に自動チェックし、今日が授業日かつ欠席が危険ライン到達／あと1回で到達のユーザーへ、設定したチャンネルで通知（🔴危険 / 🟡注意）

## セットアップ手順

### 1. Discord Developer Portal でボットを作成

1. https://discord.com/developers/applications にアクセスし「New Application」
2. 左メニュー「Bot」→「Add Bot」
3. 「TOKEN」の「Reset Token」からトークンを取得（後で `.env` に使用）
4. 「Privileged Gateway Intents」は今回すべてOFFのままでOK（スラッシュコマンドのみ使用するため）
5. 左メニュー「OAuth2」→「URL Generator」で
   - SCOPES: `bot`, `applications.commands`
   - BOT PERMISSIONS: `Send Messages`, `Embed Links`, `Use Slash Commands`
   を選択し、生成されたURLからサーバーに招待

### 2. ローカル環境のセットアップ

```bash
cd discord-absence-bot
python -m venv venv
source venv/bin/activate  # Windowsは venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` を開き、取得したトークンを設定:

```
DISCORD_TOKEN=あなたのボットトークン
```

### 3. 起動

```bash
python main.py
```

起動後、コンソールに「ログイン成功」「スラッシュコマンドを◯件同期しました」と出れば成功です。
（初回のコマンド反映には数分かかる場合があります）

## 使い方の例

### 授業登録

**毎週開講の授業:**
```
/class add name:線形代数 pattern:毎週 weekday:月曜日 threshold:5
```

**隔週開講の授業:**
```
/class add name:実験実習 pattern:隔週 weekday:水曜日 start_date:2026-04-08 threshold:3
```
→ `start_date` を含む週を「開講週」として、以後2週間おきに開講と判定します。

**特定日のみの集中講義など:**
```
/class add name:集中講義A pattern:特定日のみ specific_dates:2026-08-10,2026-08-11,2026-08-12 threshold:2
```

### 通知チャンネルの設定（サーバーごとに1回）
```
/class setchannel channel:#授業通知
```

### 欠席の記録
```
/absence add class_name:線形代数
/absence add class_name:線形代数 date_str:2026-06-01 note:寝坊
```

### 状況確認
```
/absence status
```

## データの保存について

欠席・授業データは同一フォルダ内の `absence_bot.db`（SQLite）に保存されます。
バックアップを取りたい場合はこのファイルをコピーしてください。

## 24時間稼働させたい場合（Koyeb + Google Apps Script）

> **Glitchについて**: glitch.com は2025年7月にアプリホスティング自体を終了しています。現在はプロジェクトのダウンロード・リダイレクトのみ可能で、実行環境としては使えません。そのため本ボットは **Koyeb単体** で24時間稼働させる構成にしています。

### 仕組み

- Koyebの無料インスタンスは **1時間トラフィックがないとスケールツーゼロ（完全停止）** します。この挙動は無料枠では無効化できません。
- そこで、このプロジェクトにはボット本体と同じプロセス内で動く軽量HTTPサーバー（`keep_alive.py`、`/health` エンドポイント）を組み込んであります。
- Google Apps Script (GAS) の time-driven トリガーで **10分おき** に `/health` をpingすることで、1時間の無通信しきい値に達する前に常にリクエストが入り、スリープしません。

### 注意点（重要）

- Koyebの無料プランは **永続ボリュームが使えません**。コンテナが再作成されると `absence_bot.db`（SQLite）は消えます。
  - **pingが途切れずコンテナが起動し続けている間はデータは保持されます。**
  - ただし **コードを再デプロイした場合は必ずDBがリセット**されます（欠席記録も消えます）。頻繁に再デプロイしない、または本番運用が安定してきたら外部の永続DB（例: Neon の無料PostgreSQLなど）に切り替えることを検討してください。
  - こまめに `/absence status` などでバックアップを取りたい場合は、`absence_bot.db` を定期的にダウンロードする運用でも構いません。

### 1. Koyebにデプロイ

1. このプロジェクト一式をGitHubリポジトリにpush（`Dockerfile` を含めてそのまま）
2. https://app.koyeb.com/ にサインアップ → 「Create Service」→「GitHub」でリポジトリを選択
3. Builder は自動検出された **Dockerfile** のままでOK
4. 「Environment variables」に `DISCORD_TOKEN` を **Secret** として追加（値はDiscordボットのトークン）
5. Instance type は無料の **Free** を選択し、Region は Washington D.C. か Frankfurt を選択
6. デプロイ完了後、割り当てられたURL（例: `https://your-app-xxxxxxx.koyeb.app`）を控える
   - `https://your-app-xxxxxxx.koyeb.app/health` にアクセスして `OK: absence bot is alive` と表示されればOK

### 2. GASで10分おきにping

1. https://script.google.com/ で新規プロジェクトを作成
2. 同梱の `gas_keep_alive.gs` の内容を貼り付け
3. 冒頭の `KOYEB_URL` を、手順1で控えたURル + `/health` に書き換える
   ```js
   const KOYEB_URL = 'https://your-app-xxxxxxx.koyeb.app/health';
   ```
4. 関数選択メニューから `createTrigger` を選んで実行（初回は権限承認が必要）
5. 左メニュー「トリガー」を開き、`pingBot` が10分おきに登録されていれば完了

これでKoyebのコンテナが常に稼働し続け、スケジューラー（毎日8:00 JSTの欠席チェック）も止まらずに動作します。

### 停止したいとき

- GAS側: `removeTrigger` 関数を実行してping停止
- Koyeb側: サービスをPause/削除

## （参考）ローカルや他のPaaSで常時稼働させたい場合

Koyeb以外にも、Railway / Fly.io / 自宅サーバー / VPS など、Pythonプロセスを常駐できる環境であれば同じコードでそのまま稼働できます（`keep_alive.py` はKoyeb専用ではなく、汎用のヘルスチェック用サーバーです）。
