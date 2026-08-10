"""
データベース操作モジュール
SQLite (aiosqlite) を使ってクラス情報・欠席記録・通知チャンネル設定を管理する。
"""
import aiosqlite
from datetime import date, timedelta
from typing import Optional

DB_PATH = "absence_bot.db"

# ---- パターン定数 ----
PATTERN_EVERY = "every"        # 毎週
PATTERN_BIWEEKLY = "biweekly"  # 隔週
PATTERN_SPECIFIC = "specific"  # 特定日のみ

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                notify_channel_id INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                day_of_week INTEGER,            -- 0=月 ... 6=日 (specificの場合はNULL可)
                pattern TEXT NOT NULL,          -- every / biweekly / specific
                start_date TEXT,                -- biweeklyの基準日 (YYYY-MM-DD)
                specific_dates TEXT,             -- specific用 カンマ区切り YYYY-MM-DD
                threshold INTEGER NOT NULL DEFAULT 3,
                created_by INTEGER,
                UNIQUE(guild_id, name)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS absences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                note TEXT,
                FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE
            )
        """)
        await db.commit()


# ---------------- guild_config ----------------

async def set_notify_channel(guild_id: int, channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guild_config (guild_id, notify_channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET notify_channel_id=excluded.notify_channel_id
        """, (guild_id, channel_id))
        await db.commit()


async def get_notify_channel(guild_id: int) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT notify_channel_id FROM guild_config WHERE guild_id=?", (guild_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def get_all_guild_ids_with_channel():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT guild_id FROM guild_config WHERE notify_channel_id IS NOT NULL"
        ) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


# ---------------- classes ----------------

async def add_class(guild_id: int, name: str, pattern: str, threshold: int,
                     day_of_week: Optional[int] = None,
                     start_date: Optional[str] = None,
                     specific_dates: Optional[str] = None,
                     created_by: Optional[int] = None) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO classes
                    (guild_id, name, day_of_week, pattern, start_date, specific_dates, threshold, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, name, day_of_week, pattern, start_date, specific_dates, threshold, created_by))
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        return False  # 同名クラスが既に存在


async def remove_class(guild_id: int, name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM classes WHERE guild_id=? AND name=?", (guild_id, name)
        )
        await db.commit()
        return cur.rowcount > 0


async def get_class(guild_id: int, name: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM classes WHERE guild_id=? AND name=?", (guild_id, name)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_class_by_id(class_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM classes WHERE id=?", (class_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def list_classes(guild_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM classes WHERE guild_id=? ORDER BY name", (guild_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def update_threshold(guild_id: int, name: str, threshold: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE classes SET threshold=? WHERE guild_id=? AND name=?",
            (threshold, guild_id, name)
        )
        await db.commit()
        return cur.rowcount > 0


# ---------------- absences ----------------

async def add_absence(class_id: int, user_id: int, date_str: str, note: Optional[str] = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO absences (class_id, user_id, date, note) VALUES (?, ?, ?, ?)",
            (class_id, user_id, date_str, note)
        )
        await db.commit()
        return cur.lastrowid


async def remove_latest_absence(class_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM absences WHERE class_id=? AND user_id=? ORDER BY date DESC, id DESC LIMIT 1",
            (class_id, user_id)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return False
        await db.execute("DELETE FROM absences WHERE id=?", (row[0],))
        await db.commit()
        return True


async def count_absences(class_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM absences WHERE class_id=? AND user_id=?",
            (class_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def list_absences(class_id: int, user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT date, note FROM absences WHERE class_id=? AND user_id=? ORDER BY date",
            (class_id, user_id)
        ) as cur:
            return await cur.fetchall()


async def get_users_with_absences(class_id: int) -> list:
    """指定クラスで欠席記録のあるユーザーID一覧（重複なし）"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT DISTINCT user_id FROM absences WHERE class_id=?", (class_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


# ---------------- スケジュール判定ロジック ----------------

def is_class_day(cls: dict, target_date: date) -> bool:
    """指定した日付にそのクラスの授業があるかどうかを判定する"""
    pattern = cls["pattern"]

    if pattern == PATTERN_SPECIFIC:
        dates = (cls["specific_dates"] or "").split(",")
        return target_date.isoformat() in [d.strip() for d in dates if d.strip()]

    if cls["day_of_week"] is None:
        return False
    if target_date.weekday() != cls["day_of_week"]:
        return False

    if pattern == PATTERN_EVERY:
        return True

    if pattern == PATTERN_BIWEEKLY:
        if not cls["start_date"]:
            return False
        start = date.fromisoformat(cls["start_date"])
        if target_date < start:
            return False
        weeks_diff = (target_date - start).days // 7
        return weeks_diff % 2 == 0

    return False


def describe_schedule(cls: dict) -> str:
    """クラスのスケジュールを人間が読める形式にする"""
    pattern = cls["pattern"]
    if pattern == PATTERN_SPECIFIC:
        dates = (cls["specific_dates"] or "").split(",")
        dates = [d.strip() for d in dates if d.strip()]
        return f"特定日のみ（{', '.join(dates)}）"
    day_str = WEEKDAY_JP[cls["day_of_week"]] + "曜日" if cls["day_of_week"] is not None else "?"
    if pattern == PATTERN_EVERY:
        return f"毎週{day_str}"
    if pattern == PATTERN_BIWEEKLY:
        return f"隔週{day_str}（基準日: {cls['start_date']}）"
    return "不明"
