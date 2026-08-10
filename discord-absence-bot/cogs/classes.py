"""
授業（クラス）の登録・一覧・削除・通知チャンネル設定を行うCog
"""
import discord
from discord import app_commands
from discord.ext import commands
from datetime import date

import database as db


WEEKDAY_CHOICES = [
    app_commands.Choice(name="月曜日", value=0),
    app_commands.Choice(name="火曜日", value=1),
    app_commands.Choice(name="水曜日", value=2),
    app_commands.Choice(name="木曜日", value=3),
    app_commands.Choice(name="金曜日", value=4),
    app_commands.Choice(name="土曜日", value=5),
    app_commands.Choice(name="日曜日", value=6),
]

PATTERN_CHOICES = [
    app_commands.Choice(name="毎週", value=db.PATTERN_EVERY),
    app_commands.Choice(name="隔週", value=db.PATTERN_BIWEEKLY),
    app_commands.Choice(name="特定日のみ", value=db.PATTERN_SPECIFIC),
]


def _validate_date(s: str) -> bool:
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


class ClassesCog(commands.Cog):
    class_group = app_commands.Group(
        name="class",
        description="授業スケジュールの管理"
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @class_group.command(
        name="add",
        description="授業を登録します"
    )
    @app_commands.describe(
        name="授業名（例: 線形代数）",
        pattern="開講パターン",
        weekday="毎週/隔週の場合の曜日",
        threshold="危険とみなす欠席回数（例: 5回で危険なら5）",
        start_date="隔週の場合の基準日（YYYY-MM-DD）。この日を含む週を開講週とします",
        specific_dates="特定日のみの場合の開講日（カンマ区切り、YYYY-MM-DD）",
    )
    @app_commands.choices(
        pattern=PATTERN_CHOICES,
        weekday=WEEKDAY_CHOICES
    )
    async def class_add(
        self,
        interaction: discord.Interaction,
        name: str,
        pattern: app_commands.Choice[str],
        threshold: int,
        weekday: app_commands.Choice[int] = None,
        start_date: str = None,
        specific_dates: str = None,
    ):
        pattern_value = pattern.value

        if pattern_value in (
            db.PATTERN_EVERY,
            db.PATTERN_BIWEEKLY
        ):
            if weekday is None:
                await interaction.response.send_message(
                    "毎週・隔週の場合は `weekday`（曜日）を指定してください。",
                    ephemeral=True
                )
                return

        if pattern_value == db.PATTERN_BIWEEKLY:
            if not start_date or not _validate_date(start_date):
                await interaction.response.send_message(
                    "隔週の場合は `start_date` を `YYYY-MM-DD` 形式で指定してください。",
                    ephemeral=True
                )
                return

        if pattern_value == db.PATTERN_SPECIFIC:
            if not specific_dates:
                await interaction.response.send_message(
                    "特定日のみの場合は `specific_dates` にカンマ区切りで日付を指定してください。",
                    ephemeral=True
                )
                return

            parts = [
                d.strip()
                for d in specific_dates.split(",")
                if d.strip()
            ]

            if not all(_validate_date(d) for d in parts):
                await interaction.response.send_message(
                    "`specific_dates` は `YYYY-MM-DD,YYYY-MM-DD,...` の形式で指定してください。",
                    ephemeral=True
                )
                return

            specific_dates = ",".join(parts)

        ok = await db.add_class(
            guild_id=interaction.guild_id,
            name=name,
            pattern=pattern_value,
            threshold=threshold,
            day_of_week=weekday.value if weekday else None,
            start_date=start_date,
            specific_dates=specific_dates,
            created_by=interaction.user.id,
        )

        if not ok:
            await interaction.response.send_message(
                f"授業「{name}」は既に登録されています。",
                ephemeral=True
            )
            return

        cls = await db.get_class(
            interaction.guild_id,
            name
        )

        await interaction.response.send_message(
            f"✅ 授業「{name}」を登録しました。\n"
            f"スケジュール: {db.describe_schedule(cls)}\n"
            f"危険ライン: {threshold}回"
        )

    @class_group.command(
        name="remove",
        description="授業を削除します"
    )
    @app_commands.describe(
        name="削除する授業名"
    )
    async def class_remove(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        ok = await db.remove_class(
            interaction.guild_id,
            name
        )

        if ok:
            await interaction.response.send_message(
                f"🗑️ 授業「{name}」を削除しました。"
            )
        else:
            await interaction.response.send_message(
                f"授業「{name}」が見つかりません。",
                ephemeral=True
            )

    @class_group.command(
        name="list",
        description="登録されている授業の一覧を表示します"
    )
    async def class_list(
        self,
        interaction: discord.Interaction
    ):
        classes = await db.list_classes(
            interaction.guild_id
        )

        if not classes:
            await interaction.response.send_message(
                "登録されている授業はありません。"
            )
            return

        lines = []

        for c in classes:
            lines.append(
                f"**{c['name']}** — "
                f"{db.describe_schedule(c)} / "
                f"危険ライン: {c['threshold']}回"
            )

        embed = discord.Embed(
            title="📚 登録されている授業一覧",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(
            embed=embed
        )

    @class_group.command(
        name="setchannel",
        description="欠席通知を送るチャンネルを設定します"
    )
    @app_commands.describe(
        channel="通知を送るテキストチャンネル"
    )
    async def class_setchannel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        await db.set_notify_channel(
            interaction.guild_id,
            channel.id
        )

        await interaction.response.send_message(
            f"✅ 通知チャンネルを {channel.mention} に設定しました。"
        )

    @class_group.command(
        name="threshold",
        description="授業の危険ライン（欠席回数）を変更します"
    )
    @app_commands.describe(
        name="授業名",
        threshold="危険ラインとなる欠席回数"
    )
    async def class_threshold(
        self,
        interaction: discord.Interaction,
        name: str,
        threshold: int
    ):
        ok = await db.update_threshold(
            interaction.guild_id,
            name,
            threshold
        )

        if ok:
            await interaction.response.send_message(
                f"✅ 「{name}」の危険ラインを "
                f"{threshold}回 に更新しました。"
            )
        else:
            await interaction.response.send_message(
                f"授業「{name}」が見つかりません。",
                ephemeral=True
            )

    @class_remove.autocomplete("name")
    @class_threshold.autocomplete("name")
    async def class_name_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        classes = await db.list_classes(
            interaction.guild_id
        )

        return [
            app_commands.Choice(
                name=c["name"],
                value=c["name"]
            )
            for c in classes
            if current.lower() in c["name"].lower()
        ][:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(ClassesCog(bot))
