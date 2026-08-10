/**
 * Koyebにデプロイしたボットを10分おきに叩き起こすためのGoogle Apps Scriptコード。
 *
 * 【使い方】
 * 1. https://script.google.com/ で新しいプロジェクトを作成
 * 2. このファイルの内容を貼り付け
 * 3. KOYEB_URL を実際のKoyebアプリのURL（/health を付けたもの）に書き換える
 *    例: https://your-app-xxxxxxx.koyeb.app/health
 * 4. 関数選択で `createTrigger` を選び、実行（初回は権限の許可が必要）
 * 5. 左メニューの「トリガー」で 10分おき の time-driven トリガーが
 *    登録されていれば設定完了
 *
 * これで10分ごとに pingBot() が自動実行され、Koyebの無料インスタンスが
 * 1時間の無通信スリープ（scale-to-zero）に入るのを防げます。
 */

// ここをあなたのKoyebアプリのURLに書き換えてください
const KOYEB_URL = 'https://your-app-xxxxxxx.koyeb.app/health';

function pingBot() {
  try {
    const res = UrlFetchApp.fetch(KOYEB_URL, {
      method: 'get',
      muteHttpExceptions: true,
      followRedirects: true,
    });
    console.log('ping status: ' + res.getResponseCode());
  } catch (e) {
    console.error('ping failed: ' + e);
  }
}

/**
 * 10分おきのトリガーを作成する（初回に1回だけ実行すればOK）。
 * 二重登録を防ぐため、既存の同名トリガーは一旦削除してから作り直す。
 */
function createTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'pingBot') {
      ScriptApp.deleteTrigger(t);
    }
  });

  ScriptApp.newTrigger('pingBot')
    .timeBased()
    .everyMinutes(10)
    .create();

  console.log('10分おきのトリガーを作成しました。');
}

/**
 * トリガーを止めたくなったときに実行する。
 */
function removeTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'pingBot') {
      ScriptApp.deleteTrigger(t);
    }
  });
  console.log('トリガーを削除しました。');
}
