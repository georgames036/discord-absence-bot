"""
Discord 欠席管理ボット エントリーポイント
"""
import os
import asyncio
import logging

import discord
from discord.ext import commands
from dotenv import load_dotenv

import database as db
from keep_alive import start_keep_alive_server

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("absence_bot")

intents = discord.Intents.default()
# メンバー/メッセージ内容の特権インテントは今回不要（スラッシュコマンドのみ使用）

bot = commands.Bot(command_prefix="!", intents=intents)

INITIAL_EXTENSIONS = [
    "cogs.classes",
    "cogs.absences",
    "cogs.scheduler",
]


@bot.event
async def on_ready():
    logger.info(f"ログイン成功: {bot.user} (ID: {bot.user.id})")

    try:
        for guild in bot.guilds:
            # グローバルコマンドをこのサーバーにコピー
            bot.tree.copy_global_to(guild=guild)

            # サーバー単位で同期
            synced = await bot.tree.sync(guild=guild)

            logger.info(
                f"サーバー「{guild.name}」に "
                f"{len(synced)} 件のスラッシュコマンドを同期しました。"
            )

    except Exception as e:
        logger.exception(f"コマンド同期に失敗しました: {e}")


async def main():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN が設定されていません。.env ファイルを作成し、"
            "DISCORD_TOKEN=あなたのトークン を記入してください。"
        )

    await db.init_db()

    async with bot:
        # KoyebなどのPaaSで生存確認・スリープ回避のためのHTTPサーバーを起動
        await start_keep_alive_server()

        for ext in INITIAL_EXTENSIONS:
            await bot.load_extension(ext)
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
