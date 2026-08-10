"""
欠席の記録・取り消し・確認を行うCog
"""
import discord
from discord import app_commands
from discord.ext import commands
from datetime import date

import database as db


def _validate_date(s: str) -> bool:
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def _status_emoji(count: int, threshold: int) -> str:
    if count >= threshold:
        return "🔴"

    if count == threshold - 1:
        return "🟡"

    return "🟢"


class AbsencesCog(commands.Cog):
    absence_group = app_commands.Group(
        name="absence",
        description="欠席の記録・確認"
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @absence_group.command(
        name="add",
        description="欠席を1回記録します"
    )
    @app_commands.describe(
        class_name="授業名",
        date_str="欠席した日付（省略時は今日、YYYY-MM-DD）",
        note="メモ（任意）",
    )
    async def absence_add(
        self,
        interaction: discord.Interaction,
        class_name: str,
        date_str: str = None,
        note: str = None,
    ):
        cls = await db.get_class(
            interaction.guild_id,
            class_name
        )

        if not cls:
            await interaction.response.send_message(
                f"授業「{class_name}」が見つかりません。"
                "`/class list` で確認してください。",
                ephemeral=True
            )
            return

        if date_str:
            if not _validate_date(date_str):
                await interaction.response.send_message(
                    "日付は `YYYY-MM-DD` 形式で指定してください。",
                    ephemeral=True
                )
                return
        else:
            date_str = date.today().isoformat()

        await db.add_absence(
            cls["id"],
            interaction.user.id,
            date_str,
            note
        )

        count = await db.count_absences(
            cls["id"],
            interaction.user.id
        )

        threshold = cls["threshold"]
        emoji = _status_emoji(
            count,
            threshold
        )

        msg = (
            f"{emoji} 「{class_name}」の欠席を記録しました。"
            f"（{date_str}）\n"
            f"現在の欠席回数: **{count} / {threshold}**"
        )

        if count >= threshold:
            msg += (
                "\n⚠️ 既に危険ラインに達しています。"
                "単位に注意してください。"
            )
        elif count == threshold - 1:
            msg += (
                "\n⚠️ あと1回で危険ラインです。"
            )

        await interaction.response.send_message(msg)

    @absence_group.command(
        name="remove",
        description="直近の欠席記録を1件取り消します"
    )
    @app_commands.describe(
        class_name="授業名"
    )
    async def absence_remove(
        self,
        interaction: discord.Interaction,
        class_name: str
    ):
        cls = await db.get_class(
            interaction.guild_id,
            class_name
        )

        if not cls:
            await interaction.response.send_message(
                f"授業「{class_name}」が見つかりません。",
                ephemeral=True
            )
            return

        ok = await db.remove_latest_absence(
            cls["id"],
            interaction.user.id
        )

        if ok:
            count = await db.count_absences(
                cls["id"],
                interaction.user.id
            )

            await interaction.response.send_message(
                f"↩️ 「{class_name}」の直近の欠席記録を"
                f"取り消しました。（現在: {count}回）"
            )
        else:
            await interaction.response.send_message(
                f"「{class_name}」の欠席記録はありません。",
                ephemeral=True
            )

    @absence_group.command(
        name="list",
        description="特定の授業の欠席日一覧を表示します"
    )
    @app_commands.describe(
        class_name="授業名"
    )
    async def absence_list(
        self,
        interaction: discord.Interaction,
        class_name: str
    ):
        cls = await db.get_class(
            interaction.guild_id,
            class_name
        )

        if not cls:
            await interaction.response.send_message(
                f"授業「{class_name}」が見つかりません。",
                ephemeral=True
            )
            return

        rows = await db.list_absences(
            cls["id"],
            interaction.user.id
        )

        if not rows:
            await interaction.response.send_message(
                f"「{class_name}」の欠席記録はありません。"
            )
            return

        lines = [
            f"- {d}" + (f"（{n}）" if n else "")
            for d, n in rows
        ]

        embed = discord.Embed(
            title=(
                f"📋 {class_name} の欠席一覧"
                f"（{len(rows)} / {cls['threshold']}）"
            ),
            description="\n".join(lines),
            color=(
                discord.Color.orange()
                if len(rows) >= cls["threshold"]
                else discord.Color.green()
            ),
        )

        await interaction.response.send_message(
            embed=embed
        )

    @absence_group.command(
        name="status",
        description="自分の全授業の欠席状況をまとめて確認します"
    )
    async def absence_status(
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
            count = await db.count_absences(
                c["id"],
                interaction.user.id
            )

            emoji = _status_emoji(
                count,
                c["threshold"]
            )

            lines.append(
                f"{emoji} **{c['name']}**: "
                f"{count} / {c['threshold']}回"
            )

        embed = discord.Embed(
            title=(
                f"📊 {interaction.user.display_name} さんの"
                "欠席状況"
            ),
            description="\n".join(lines),
            color=discord.Color.blue(),
        )

        embed.set_footer(
            text="🟢 安全 / 🟡 あと1回で危険 / 🔴 危険ライン到達"
        )

        await interaction.response.send_message(
            embed=embed
        )

    @absence_add.autocomplete("class_name")
    @absence_remove.autocomplete("class_name")
    @absence_list.autocomplete("class_name")
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
    cog = AbsencesCog(bot)

    await bot.add_cog(cog)

    bot.tree.add_command(
        AbsencesCog.absence_group
    )
