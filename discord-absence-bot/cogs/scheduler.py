"""
毎日決まった時刻（デフォルト 08:00 JST）に、今日開講される授業をチェックし、
欠席回数が危険ライン付近のユーザーへ通知チャンネルで警告するCog
"""
import discord
from discord.ext import commands, tasks
from datetime import datetime, date, time
from zoneinfo import ZoneInfo

import database as db

JST = ZoneInfo("Asia/Tokyo")
NOTIFY_TIME = time(hour=8, minute=0, tzinfo=JST)  # 通知を送る時刻


class SchedulerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_check.start()

    def cog_unload(self):
        self.daily_check.cancel()

    @tasks.loop(time=NOTIFY_TIME)
    async def daily_check(self):
        await self.run_check_for_all_guilds()

    @daily_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()

    async def run_check_for_all_guilds(self):
        today = datetime.now(JST).date()
        guild_ids = await db.get_all_guild_ids_with_channel()

        for guild_id in guild_ids:
            channel_id = await db.get_notify_channel(guild_id)
            if not channel_id:
                continue
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                continue

            classes = await db.list_classes(guild_id)
            for cls in classes:
                if not db.is_class_day(cls, today):
                    continue
                await self._notify_for_class(channel, cls)

    async def _notify_for_class(self, channel: discord.abc.Messageable, cls: dict):
        threshold = cls["threshold"]
        user_ids = await db.get_users_with_absences(cls["id"])

        danger_mentions = []
        warning_mentions = []

        for user_id in user_ids:
            count = await db.count_absences(cls["id"], user_id)
            if count >= threshold:
                danger_mentions.append((user_id, count))
            elif count == threshold - 1:
                warning_mentions.append((user_id, count))

        if not danger_mentions and not warning_mentions:
            return  # 危険/注意レベルの人がいなければ通知しない（スパム防止）

        embed = discord.Embed(
            title=f"📅 本日は「{cls['name']}」の授業日です",
            color=discord.Color.red() if danger_mentions else discord.Color.gold(),
        )

        if danger_mentions:
            lines = [f"<@{uid}> — {count} / {threshold}回（危険ライン到達済み）" for uid, count in danger_mentions]
            embed.add_field(name="🔴 危険", value="\n".join(lines), inline=False)

        if warning_mentions:
            lines = [f"<@{uid}> — {count} / {threshold}回（あと1回で危険）" for uid, count in warning_mentions]
            embed.add_field(name="🟡 注意", value="\n".join(lines), inline=False)

        content = " ".join(f"<@{uid}>" for uid, _ in danger_mentions + warning_mentions)
        await channel.send(content=content, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerCog(bot))
