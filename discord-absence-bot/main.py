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

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

INITIAL_EXTENSIONS = [
    "cogs.classes",
    "cogs.absences",
    "cogs.scheduler",
]


@bot.event
async def on_ready():

    logger.info(
        f"ログイン成功: {bot.user} "
        f"(ID: {bot.user.id})"
    )

    # 起動時に一度だけ同期
    if getattr(bot, "_commands_synced", False):
        return

    bot._commands_synced = True

    try:

        # ========================================
        # グローバルコマンドを同期
        # ========================================

        global_synced = await bot.tree.sync()

        logger.info(
            f"{len(global_synced)} 件のグローバルスラッシュコマンドを同期しました。"
        )

        # ========================================
        # ギルド用コマンドを同期
        # ========================================

        for guild in bot.guilds:

            # グローバルコマンドを
            # このギルド用Treeへコピー
            bot.tree.copy_global_to(
                guild=guild
            )

            # ギルドへ同期
            synced = await bot.tree.sync(
                guild=guild
            )

            logger.info(
                f"サーバー「{guild.name}」に "
                f"{len(synced)} 件のギルド用スラッシュコマンドを同期しました。"
            )

    except Exception:
        logger.exception(
            "スラッシュコマンドの同期に失敗しました。"
        )


async def main():

    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN が設定されていません。"
            ".env ファイルを作成し、"
            "DISCORD_TOKEN=あなたのトークン を記入してください。"
        )

    await db.init_db()

    async with bot:

        # Keep Alive
        await start_keep_alive_server()

        # Cogを読み込む
        for ext in INITIAL_EXTENSIONS:

            try:

                await bot.load_extension(ext)

                logger.info(
                    f"Extension loaded: {ext}"
                )

            except Exception:
                logger.exception(
                    f"Extensionの読み込みに失敗しました: {ext}"
                )
                raise

        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
