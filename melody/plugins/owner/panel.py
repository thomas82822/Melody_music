"""
👑 Owner Panel — All owner control callbacks
   HTML blockquote formatting + color-coded emoji buttons
   🔵 Blue = info/safe | 🔴 Red = danger/restart | 🟢 Green = positive
"""
import asyncio
import html
import importlib
import pkgutil
import sys
import time
import psutil
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from melody import bot
from melody.config import Config
from utils.decorators import owner_only, error_handler
from utils.database import get_all_chats, get_stats
from strings.themes import BLUE, RED, GREEN, btn, fancy

_start_time = time.time()

PANEL_TEXT = (
    f"<blockquote>👑 <b>{fancy('OWNER CONTROL PANEL')}</b></blockquote>\n\n"
    "Welcome back, <b>Master</b> 🫡\n"
    "<i>Choose an action below:</i>\n\n"
    "<blockquote>"
    "🖼️ <b>Set Start Pic</b> — Change welcome image\n"
    "📡 <b>Active VCs</b> — Live voice chat sessions\n"
    "📢 <b>Broadcast</b> — Message all chats\n"
    "📊 <b>Bot Stats</b> — CPU, RAM, uptime\n"
    "📋 <b>Chat List</b> — All served groups\n"
    "🔧 <b>Maintenance</b> — Toggle mode\n"
    "🔄 <b>Reload</b> — Hot-reload plugins\n"
    "🔴 <b>Restart</b> — Full bot restart"
    "</blockquote>"
)

PANEL_MARKUP = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(btn("🖼️ Set Start Pic", BLUE),  callback_data="owner_setpic_info"),
        InlineKeyboardButton(btn("📡 Active VCs", GREEN),     callback_data="owner_activevc"),
    ],
    [
        InlineKeyboardButton(btn("📢 Broadcast", BLUE),       callback_data="owner_broadcast_info"),
        InlineKeyboardButton(btn("📊 Bot Stats", BLUE),       callback_data="owner_stats"),
    ],
    [
        InlineKeyboardButton(btn("📋 Chat List", BLUE),       callback_data="owner_chatlist"),
        InlineKeyboardButton(btn("🔧 Maintenance", RED),      callback_data="owner_maintenance"),
    ],
    [
        InlineKeyboardButton(btn("🔄 Reload Plugins", GREEN), callback_data="owner_reload"),
        InlineKeyboardButton(btn("🔁 Restart Bot", RED),      callback_data="owner_restart"),
    ],
])

PANEL_MARKUP_WITH_BACK = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(btn("🖼️ Set Start Pic", BLUE),  callback_data="owner_setpic_info"),
        InlineKeyboardButton(btn("📡 Active VCs", GREEN),     callback_data="owner_activevc"),
    ],
    [
        InlineKeyboardButton(btn("📢 Broadcast", BLUE),       callback_data="owner_broadcast_info"),
        InlineKeyboardButton(btn("📊 Bot Stats", BLUE),       callback_data="owner_stats"),
    ],
    [
        InlineKeyboardButton(btn("📋 Chat List", BLUE),       callback_data="owner_chatlist"),
        InlineKeyboardButton(btn("🔧 Maintenance", RED),      callback_data="owner_maintenance"),
    ],
    [
        InlineKeyboardButton(btn("🔄 Reload Plugins", GREEN), callback_data="owner_reload"),
        InlineKeyboardButton(btn("🔁 Restart Bot", RED),      callback_data="owner_restart"),
    ],
    [
        InlineKeyboardButton(btn("✵ BACK ✵", RED),            callback_data="owner_back_home"),
    ],
])


def back_to_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btn("✵ BACK ✵", RED), callback_data="owner_panel")],
    ])


# ─── /panel command ───────────────────────────────────────────────────────────

@bot.on_message(filters.command("panel") & filters.private)
@owner_only
@error_handler
async def panel_cmd(client: Client, message: Message):
    await message.reply(
        PANEL_TEXT,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=PANEL_MARKUP,
    )


# ─── Owner panel callback ─────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_panel$"))
@error_handler
async def cb_panel(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)
    await cb.message.edit_text(
        PANEL_TEXT,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=PANEL_MARKUP_WITH_BACK,
    )
    await cb.answer()


# ─── Bot Stats ────────────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_stats$"))
@error_handler
async def cb_stats(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    db_stats  = await get_stats()
    uptime_sec = int(time.time() - _start_time)
    h = uptime_sec // 3600
    m = (uptime_sec % 3600) // 60
    s = uptime_sec % 60

    cpu  = psutil.cpu_percent(interval=0.5)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    text = (
        "<blockquote>📊 <b>BOT STATISTICS</b></blockquote>\n\n"
        "<blockquote>"
        f"🕒 <b>Uptime:</b> <code>{h}h {m}m {s}s</code>\n\n"
        "💻 <b>System:</b>\n"
        f"  ▸ CPU:  <code>{cpu}%</code>\n"
        f"  ▸ RAM:  <code>{ram.percent}%</code> "
        f"<i>({ram.used // 1024 // 1024}MB / {ram.total // 1024 // 1024}MB)</i>\n"
        f"  ▸ Disk: <code>{disk.percent}%</code> "
        f"<i>({disk.used // 1024 // 1024 // 1024}GB / {disk.total // 1024 // 1024 // 1024}GB)</i>"
        "</blockquote>\n\n"
        "<blockquote>"
        "📈 <b>Database:</b>\n"
        f"  ▸ Total Chats:     <code>{db_stats['chats']}</code>\n"
        f"  ▸ Banned Users:    <code>{db_stats['banned']}</code>\n"
        f"  ▸ Globally Banned: <code>{db_stats['gbanned']}</code>"
        "</blockquote>"
    )
    await cb.message.edit_text(text, parse_mode=enums.ParseMode.HTML, reply_markup=back_to_panel())
    await cb.answer()


# ─── Chat List ────────────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_chatlist$"))
@error_handler
async def cb_chatlist(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    chats = await get_all_chats()
    if not chats:
        await cb.message.edit_text(
            "<blockquote>📋 <b>Chat List</b></blockquote>\n\n"
            "❌ No chats in database yet.",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=back_to_panel(),
        )
        return await cb.answer()

    lines = [f"<blockquote>📋 <b>All Served Chats</b> ({len(chats)} total)</blockquote>\n"]
    for c in chats[:30]:
        title = html.escape(c.get("title", "Unknown")[:25])
        lines.append(f"  ▸ <code>{c['chat_id']}</code> — {title}")
    if len(chats) > 30:
        lines.append(f"\n<i>...and {len(chats) - 30} more</i>")

    await cb.message.edit_text(
        "\n".join(lines),
        parse_mode=enums.ParseMode.HTML,
        reply_markup=back_to_panel(),
    )
    await cb.answer()


# ─── Active VCs ───────────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_activevc$"))
@error_handler
async def cb_activevc(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    from melody.core.call import _active
    active_ids = [cid for cid, active in _active.items() if active]

    if not active_ids:
        await cb.message.edit_text(
            "<blockquote>📡 <b>Active Voice Chats</b></blockquote>\n\n"
            "🔇 No active VCs right now.",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=back_to_panel(),
        )
        return await cb.answer()

    all_chats = await get_all_chats()
    chat_map  = {c["chat_id"]: c.get("title", "Unknown") for c in all_chats}

    from melody.core.queue import get_current

    lines = [f"<blockquote>📡 <b>Active Voice Chats</b> ({len(active_ids)} active)</blockquote>\n"]
    for cid in active_ids:
        title   = html.escape(chat_map.get(cid, "Unknown")[:25])
        current = get_current(cid)
        song    = f"<code>{html.escape(current.title[:20])}...</code>" if current else "<i>Unknown</i>"
        lines.append(f"🎵 <b>{title}</b>\n   ID: <code>{cid}</code> | Now: {song}\n")

    await cb.message.edit_text(
        "\n".join(lines),
        parse_mode=enums.ParseMode.HTML,
        reply_markup=back_to_panel(),
    )
    await cb.answer()


# ─── Broadcast Info ───────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_broadcast_info$"))
@error_handler
async def cb_broadcast_info(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    chats = await get_all_chats()
    await cb.message.edit_text(
        "<blockquote>📢 <b>Broadcast</b></blockquote>\n\n"
        f"📊 Total chats: <b>{len(chats)}</b>\n\n"
        "<blockquote>"
        "<b>How to broadcast:</b>\n"
        "1. Close this panel\n"
        "2. Write or forward your message\n"
        "3. Reply to it with <code>/broadcast</code>"
        "</blockquote>",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=back_to_panel(),
    )
    await cb.answer()


# ─── Set Start Pic Info ───────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_setpic_info$"))
@error_handler
async def cb_setpic_info(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    await cb.message.edit_text(
        "<blockquote>🖼️ <b>Set Start Picture</b></blockquote>\n\n"
        "<blockquote>"
        "<b>How to use:</b>\n"
        "Send any photo with caption <code>/setpic</code>\n\n"
        "To remove: send <code>/delpic</code>"
        "</blockquote>",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=back_to_panel(),
    )
    await cb.answer()


# ─── Maintenance Toggle ───────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_maintenance$"))
@error_handler
async def cb_maintenance(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    import melody
    current   = getattr(melody, "_maintenance", False)
    new_state = not current
    melody._maintenance = new_state

    status = (
        "🔧 <b>ON</b> — <i>Regular users cannot use the bot.</i>"
        if new_state else
        "✅ <b>OFF</b> — <i>Bot is available for everyone.</i>"
    )
    await cb.message.edit_text(
        f"<blockquote>🔧 <b>Maintenance Mode</b></blockquote>\n\n"
        f"Status: {status}",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                btn("🔧 Toggle Again", RED) if not new_state else btn("✅ Turn Off", GREEN),
                callback_data="owner_maintenance",
            )],
            [InlineKeyboardButton(btn("✵ BACK ✵", RED), callback_data="owner_panel")],
        ]),
    )
    await cb.answer(f"Maintenance {'ON ⚠️' if new_state else 'OFF ✅'}", show_alert=True)


# ─── Reload Plugins ───────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_reload$"))
@error_handler
async def cb_reload(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    await cb.message.edit_text(
        "<blockquote>🔄 <b>Reloading plugins...</b></blockquote>\n<i>Please wait...</i>",
        parse_mode=enums.ParseMode.HTML,
    )
    await cb.answer()

    reloaded, failed = [], []
    import melody.plugins as plugins_pkg
    for finder, name, ispkg in pkgutil.walk_packages(
        plugins_pkg.__path__, plugins_pkg.__name__ + "."
    ):
        try:
            mod = sys.modules.get(name)
            if mod:
                importlib.reload(mod)
            else:
                importlib.import_module(name)
            reloaded.append(name.split(".")[-1])
        except Exception:
            failed.append(name.split(".")[-1])

    text = (
        f"<blockquote>🔄 <b>Reload Complete</b></blockquote>\n\n"
        f"✅ Reloaded: <code>{len(reloaded)}</code> plugins\n"
    )
    if failed:
        text += f"❌ Failed: <code>{len(failed)}</code> — <code>{'</code>, <code>'.join(failed[:8])}</code>\n"

    await cb.message.edit_text(text, parse_mode=enums.ParseMode.HTML, reply_markup=back_to_panel())


# ─── Restart Bot ──────────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_restart$"))
@error_handler
async def cb_restart(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    await cb.message.edit_text(
        "<blockquote>🔁 <b>Restarting Melody...</b></blockquote>\n"
        "<i>Thodi der mein wapas aaunga! 👋</i>",
        parse_mode=enums.ParseMode.HTML,
    )
    await cb.answer("Restarting... 🔁", show_alert=True)
    await asyncio.sleep(1)
    import os
    os.execv(sys.executable, [sys.executable, "-m", "melody"])
