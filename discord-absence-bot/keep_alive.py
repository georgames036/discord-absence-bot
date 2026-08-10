"""
Koyebなどのコンテナ環境で「起きている」ことを示すための最小限のHTTPサーバー。

discord.py の依存に aiohttp が含まれているため、追加のライブラリ（Flaskなど）は不要。
Botと同じイベントループ上で動かす。

GAS(Google Apps Script) などの外部サービスから /health に定期的にGETすることで、
Koyebの「無通信1時間でスリープ（スケールツーゼロ）」を回避できる。
"""
import os
import logging
from aiohttp import web

logger = logging.getLogger("absence_bot.keep_alive")

# Koyebはコンテナに PORT 環境変数を渡してくる。ローカル実行時は 8000 を使う。
PORT = int(os.getenv("PORT", "8000"))


async def _health(request: web.Request) -> web.Response:
    return web.Response(text="OK: absence bot is alive")


async def start_keep_alive_server() -> web.AppRunner:
    """aiohttpサーバーをバックグラウンドで起動して返す（呼び出し側でrunnerを保持しておくこと）"""
    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info(f"Keep-aliveサーバーを起動しました (0.0.0.0:{PORT})")
    return runner
