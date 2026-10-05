"""SQLite-хранилище: настройки, активность, кулдауны, журнал заявок, уровни и магазин."""
import datetime as dt
import json
import time
import aiosqlite
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY, value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity_daily (
    user_id INTEGER NOT NULL, day TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day)
);
CREATE TABLE IF NOT EXISTS cooldowns (
    kind TEXT NOT NULL, user_id INTEGER NOT NULL, last_ts INTEGER NOT NULL,
    PRIMARY KEY (kind, user_id)
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, forum TEXT, thread_id INTEGER,
    user_id INTEGER, status TEXT, reason TEXT, created_ts INTEGER
);
-- Новые таблицы для уровней, монет и магазина ролей
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    coins INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS shop_roles (
    role_id INTEGER PRIMARY KEY,
    price INTEGER
);
"""

def _today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: Optional[aiosqlite.Connection] = None

    async def init(self):
        self.conn = await aiosqlite.connect(self.path)
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    # ---------- настройки ----------
    async def get_setting(self, key: str) -> Optional[str]:
        cur = await self.conn.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else None

    async def set_setting(self, key: str, value: str):
        await self.conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        await self.conn.commit()

    async def delete_setting(self, key: str):
        await self.conn.execute("DELETE FROM settings WHERE key=?", (key,))
        await self.conn.commit()

    # ---------- пинги ответственных ----------
    async def get_ping(self, forum: str) -> dict:
        raw = await self.get_setting(f"ping:{forum}")
        return json.loads(raw) if raw else {"users": [], "roles": []}

    async def set_ping(self, forum: str, users: list[int], roles: list[int]):
        await self.set_setting(f"ping:{forum}", json.dumps({"users": users, "roles": roles}))

    # ---------- активность ----------
    async def add_message(self, user_id: int):
        await self.conn.execute(
            "INSERT INTO activity_daily(user_id,day,count) VALUES(?,?,1) "
            "ON CONFLICT(user_id,day) DO UPDATE SET count=count+1",
            (user_id, _today().isoformat()))
        await self.conn.commit()

    async def get_activity(self, user_id: int) -> dict:
        today = _today()
        d7 = (today - dt.timedelta(days=6)).isoformat()
        d30 = (today - dt.timedelta(days=29)).isoformat()
        cur = await self.conn.execute(
            "SELECT COALESCE(SUM(count),0),"
            " COALESCE(SUM(CASE WHEN day>=? THEN count END),0),"
            " COALESCE(SUM(CASE WHEN day>=? THEN count END),0),"
            " COUNT(*), MIN(day) FROM activity_daily WHERE user_id=?",
            (d7, d30, user_id))
        total, last7, last30, days, first = await cur.fetchone()
        return {"total": total, "last7": last7, "last30": last30,
                "active_days": days, "first_day": first}

    # ---------- кулдауны ----------
    async def get_cooldown(self, kind: str, user_id: int) -> int:
        cur = await self.conn.execute(
            "SELECT last_ts FROM cooldowns WHERE kind=? AND user_id=?", (kind, user_id))
        row = await cur.fetchone()
        return row[0] if row else 0

    async def set_cooldown(self, kind: str, user_id: int, ts: Optional[int] = None):
        await self.conn.execute(
            "INSERT INTO cooldowns(kind,user_id,last_ts) VALUES(?,?,?) "
            "ON CONFLICT(kind,user_id) DO UPDATE SET last_ts=excluded.last_ts",
            (kind, user_id, ts or int(time.time())))
        await self.conn.commit()

    async def reset_cooldown(self, kind: str, user_id: int):
        await self.conn.execute("DELETE FROM cooldowns WHERE kind=? AND user_id=?", (kind, user_id))
        await self.conn.commit()

    # ---------- журнал ----------
    async def log_application(self, forum, thread_id, user_id, status, reason):
        await self.conn.execute(
            "INSERT INTO applications(forum,thread_id,user_id,status,reason,created_ts) "
            "VALUES(?,?,?,?,?,?)", (forum, thread_id, user_id, status, reason, int(time.time())))
        await self.conn.commit()

    # ---------- Уровни, опыт и монеты ----------
    async def get_user(self, user_id: int) -> dict:
        cur = await self.conn.execute("SELECT xp, level, coins FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if not row:
            return {"xp": 0, "level": 1, "coins": 0}
        return {"xp": row[0], "level": row[1], "coins": row[2]}

    async def update_user(self, user_id: int, xp_add: int, coins_add: int):
        user = await self.get_user(user_id)
        new_xp = user["xp"] + xp_add
        new_coins = user["coins"] + coins_add
        new_level = user["level"]

        # Простая формула уровня: уровень * 100 XP требуется для апа
        xp_needed = new_level * 100
        level_up = False
        if new_xp >= xp_needed:
            new_xp -= xp_needed
            new_level += 1
            level_up = True

        await self.conn.execute("""
            INSERT INTO users (user_id, xp, level, coins) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET xp = ?, level = ?, coins = ?
        """, (user_id, new_xp, new_level, new_coins, new_xp, new_level, new_coins))
        await self.conn.commit()

        return {"level_up": level_up, "new_level": new_level, "coins_added": coins_add}