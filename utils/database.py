"""
🗄️ MongoDB database utilities using Motor (async)
"""
import motor.motor_asyncio
from melody.config import Config
from melody.logging import LOGGER

client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_DB_URI)
db = client["MelodyDB"]

# Collections
chats_col = db["chats"]
users_col = db["users"]
banned_col = db["banned"]
gban_col = db["gban"]
auth_col = db["auth"]
history_col = db["history"]
settings_col = db["settings"]


# ─── Chat management ─────────────────────────────────────────────────────────

async def add_chat(chat_id: int, title: str = "", owner_id: int = None, owner_name: str = None):
    """
    `owner_id`/`owner_name` capture the user who ADDED the bot to this group
    — used for the "👑 My Cute Owner" welcome button (utils/database.py ->
    melody/plugins/misc/start.py). Only set on first insert so a later
    `add_chat()` call (e.g. from another handler) never overwrites the
    original adder with `None`.
    """
    update = {"$set": {"chat_id": chat_id, "title": title}}
    if owner_id is not None:
        update["$setOnInsert"] = {"owner_id": owner_id, "owner_name": owner_name or ""}
    await chats_col.update_one({"chat_id": chat_id}, update, upsert=True)


async def get_all_chats() -> list:
    return await chats_col.find({}, {"_id": 0, "chat_id": 1, "title": 1}).to_list(None)


async def get_chat_owner(chat_id: int) -> "dict | None":
    """Return {"owner_id", "owner_name"} for whoever added the bot to this
    group, or None if unknown (e.g. chat predates this feature)."""
    doc = await chats_col.find_one({"chat_id": chat_id}, {"_id": 0, "owner_id": 1, "owner_name": 1})
    if doc and doc.get("owner_id"):
        return doc
    return None


# ─── Auth management ─────────────────────────────────────────────────────────

async def auth_user(chat_id: int, user_id: int):
    await auth_col.update_one(
        {"chat_id": chat_id},
        {"$addToSet": {"users": user_id}},
        upsert=True,
    )


async def unauth_user(chat_id: int, user_id: int):
    await auth_col.update_one(
        {"chat_id": chat_id},
        {"$pull": {"users": user_id}},
    )


async def get_auth_users(chat_id: int) -> list:
    doc = await auth_col.find_one({"chat_id": chat_id})
    return doc.get("users", []) if doc else []


# ─── Ban management ───────────────────────────────────────────────────────────

async def ban_user(user_id: int, reason: str = ""):
    await banned_col.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "reason": reason}},
        upsert=True,
    )


async def unban_user(user_id: int):
    await banned_col.delete_one({"user_id": user_id})


async def is_banned(user_id: int) -> bool:
    return bool(await banned_col.find_one({"user_id": user_id}))


# ─── Global ban management ────────────────────────────────────────────────────

async def gban_user(user_id: int, reason: str = ""):
    await gban_col.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "reason": reason}},
        upsert=True,
    )


async def ungban_user(user_id: int):
    await gban_col.delete_one({"user_id": user_id})


async def is_gbanned(user_id: int) -> bool:
    return bool(await gban_col.find_one({"user_id": user_id}))


# ─── Play history ─────────────────────────────────────────────────────────────

async def add_history(chat_id: int, video_id: str, title: str = ""):
    await history_col.update_one(
        {"chat_id": chat_id},
        {"$push": {"history": {"$each": [{"id": video_id, "title": title}], "$slice": -15}}},
        upsert=True,
    )


async def get_history(chat_id: int) -> list:
    doc = await history_col.find_one({"chat_id": chat_id})
    return doc.get("history", []) if doc else []


# ─── Chat settings (autoplay, loop, etc.) ────────────────────────────────────

async def get_setting(chat_id: int, key: str, default=None):
    doc = await settings_col.find_one({"chat_id": chat_id})
    if doc:
        return doc.get(key, default)
    return default


async def set_setting(chat_id: int, key: str, value):
    await settings_col.update_one(
        {"chat_id": chat_id},
        {"$set": {key: value}},
        upsert=True,
    )


# ─── Stats ────────────────────────────────────────────────────────────────────

async def get_stats() -> dict:
    total_chats = await chats_col.count_documents({})
    total_banned = await banned_col.count_documents({})
    total_gbanned = await gban_col.count_documents({})
    return {
        "chats": total_chats,
        "banned": total_banned,
        "gbanned": total_gbanned,
    }
