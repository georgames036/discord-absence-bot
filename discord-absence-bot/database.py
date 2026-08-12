"""
Googleスプレッドシートをデータベースとして使うモジュール。
Render上のローカルSQLiteには保存せず、
Google Apps Script Web APIを経由してGoogleスプレッドシートに保存する。
"""

import json
import os
from datetime import date
from typing import Optional

import aiohttp


# ============================================================
# 設定
# ============================================================

GAS_API_URL = os.getenv("GAS_API_URL")
GAS_API_KEY = os.getenv("GAS_API_KEY")


# ============================================================
# パターン定数
# ============================================================

PATTERN_EVERY = "every"
PATTERN_BIWEEKLY = "biweekly"
PATTERN_SPECIFIC = "specific"

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


# ============================================================
# GAS API通信
# ============================================================

async def _request(
    action: str,
    data: Optional[dict] = None
) -> dict:

    if not GAS_API_URL:
        raise RuntimeError(
            "GAS_API_URL が設定されていません。"
        )

    if not GAS_API_KEY:
        raise RuntimeError(
            "GAS_API_KEY が設定されていません。"
        )

    params = {
        "action": action,
        "api_key": GAS_API_KEY,
        "data": json.dumps(
            data or {},
            ensure_ascii=False
        ),
    }

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        async with session.get(
            GAS_API_URL,
            params=params
        ) as response:

            text = await response.text()

            if response.status != 200:
                raise RuntimeError(
                    f"GAS API HTTPエラー: "
                    f"{response.status}: {text}"
                )

            try:
                result = json.loads(text)

            except Exception:
                raise RuntimeError(
                    f"GAS APIがJSONを返しませんでした: {text}"
                )

    if not result.get("ok", False):
        raise RuntimeError(
            f"GAS APIエラー: "
            f"{result.get('error', '不明なエラー')}"
        )

    return result.get("data", {})


# ============================================================
# データベース初期化
# ============================================================

async def init_db():

    await _request("init_db")


# ============================================================
# guild_config
# ============================================================

async def set_notify_channel(
    guild_id: int,
    channel_id: int
):

    await _request(
        "set_notify_channel",
        {
            "guild_id": guild_id,
            "channel_id": channel_id,
        },
    )


async def get_notify_channel(
    guild_id: int
) -> Optional[int]:

    result = await _request(
        "get_notify_channel",
        {
            "guild_id": guild_id,
        },
    )

    value = result.get("channel_id")

    if value is None:
        return None

    return int(value)


async def get_all_guild_ids_with_channel():

    result = await _request(
        "get_all_guild_ids_with_channel"
    )

    return [
        int(guild_id)
        for guild_id in result.get(
            "guild_ids",
            []
        )
    ]


# ============================================================
# classes
# ============================================================

async def add_class(
    guild_id: int,
    name: str,
    pattern: str,
    threshold: int,
    day_of_week: Optional[int] = None,
    start_date: Optional[str] = None,
    specific_dates: Optional[str] = None,
    created_by: Optional[int] = None,
) -> bool:

    result = await _request(
        "add_class",
        {
            "guild_id": guild_id,
            "name": name,
            "pattern": pattern,
            "threshold": threshold,
            "day_of_week": day_of_week,
            "start_date": start_date,
            "specific_dates": specific_dates,
            "created_by": created_by,
        },
    )

    return bool(
        result.get("created", False)
    )


async def remove_class(
    guild_id: int,
    name: str
) -> bool:

    result = await _request(
        "remove_class",
        {
            "guild_id": guild_id,
            "name": name,
        },
    )

    return bool(
        result.get("removed", False)
    )


async def get_class(
    guild_id: int,
    name: str,
) -> Optional[dict]:

    result = await _request(
        "get_class",
        {
            "guild_id": guild_id,
            "name": name,
        },
    )

    return result.get("class")


async def get_class_by_id(
    class_id: int,
) -> Optional[dict]:

    result = await _request(
        "get_class_by_id",
        {
            "class_id": class_id,
        },
    )

    return result.get("class")


async def list_classes(
    guild_id: int
) -> list:

    result = await _request(
        "list_classes",
        {
            "guild_id": guild_id,
        },
    )

    return result.get(
        "classes",
        []
    )


async def update_threshold(
    guild_id: int,
    name: str,
    threshold: int,
) -> bool:

    result = await _request(
        "update_threshold",
        {
            "guild_id": guild_id,
            "name": name,
            "threshold": threshold,
        },
    )

    return bool(
        result.get("updated", False)
    )


# ============================================================
# absences
# ============================================================

async def add_absence(
    class_id: int,
    user_id: int,
    date_str: str,
    note: Optional[str] = None,
) -> int:

    result = await _request(
        "add_absence",
        {
            "class_id": class_id,
            "user_id": user_id,
            "date": date_str,
            "note": note,
        },
    )

    return int(result["id"])


async def remove_latest_absence(
    class_id: int,
    user_id: int,
) -> bool:

    result = await _request(
        "remove_latest_absence",
        {
            "class_id": class_id,
            "user_id": user_id,
        },
    )

    return bool(
        result.get("removed", False)
    )


async def count_absences(
    class_id: int,
    user_id: int,
) -> int:

    result = await _request(
        "count_absences",
        {
            "class_id": class_id,
            "user_id": user_id,
        },
    )

    return int(
        result.get("count", 0)
    )


async def list_absences(
    class_id: int,
    user_id: int,
) -> list:

    result = await _request(
        "list_absences",
        {
            "class_id": class_id,
            "user_id": user_id,
        },
    )

    return [
        (
            row.get("date"),
            row.get("note")
        )
        for row in result.get(
            "absences",
            []
        )
    ]


async def get_users_with_absences(
    class_id: int,
) -> list:

    result = await _request(
        "get_users_with_absences",
        {
            "class_id": class_id,
        },
    )

    return [
        int(user_id)
        for user_id in result.get(
            "user_ids",
            []
        )
    ]


# ============================================================
# スケジュール判定
# ============================================================

def is_class_day(
    cls: dict,
    target_date: date
) -> bool:

    pattern = cls["pattern"]

    # 特定日のみ
    if pattern == PATTERN_SPECIFIC:

        dates = (
            cls["specific_dates"] or ""
        ).split(",")

        return target_date.isoformat() in [
            d.strip()
            for d in dates
            if d.strip()
        ]

    # 曜日が設定されていない
    if cls["day_of_week"] is None:
        return False

    # 曜日が違う
    if target_date.weekday() != int(
        cls["day_of_week"]
    ):
        return False

    # 毎週
    if pattern == PATTERN_EVERY:
        return True

    # 隔週
    if pattern == PATTERN_BIWEEKLY:

        if not cls["start_date"]:
            return False

        start = date.fromisoformat(
            cls["start_date"]
        )

        if target_date < start:
            return False

        weeks_diff = (
            target_date - start
        ).days // 7

        return weeks_diff % 2 == 0

    return False


def describe_schedule(
    cls: dict
) -> str:

    pattern = cls["pattern"]

    # 特定日のみ
    if pattern == PATTERN_SPECIFIC:

        dates = (
            cls["specific_dates"] or ""
        ).split(",")

        dates = [
            d.strip()
            for d in dates
            if d.strip()
        ]

        return (
            f"特定日のみ"
            f"（{', '.join(dates)}）"
        )

    # 曜日
    if cls["day_of_week"] is not None:

        day_str = (
            WEEKDAY_JP[
                int(cls["day_of_week"])
            ]
            + "曜日"
        )

    else:
        day_str = "?"

    # 毎週
    if pattern == PATTERN_EVERY:

        return f"毎週{day_str}"

    # 隔週
    if pattern == PATTERN_BIWEEKLY:

        return (
            f"隔週{day_str}"
            f"（基準日: {cls['start_date']}）"
        )

    return "不明"
