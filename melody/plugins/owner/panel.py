"""
👑 Owner Panel — All owner control callbacks
   Handles: stats, chatlist, activevc, broadcast info,
            setpic info, maintenance toggle, reload, restart
"""
import asyncio
import importlib
import pkgutil
import sys
import time
import psutil
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from melody import bot
from melody.config import Config
from utils.decorators import owner_only, error_handler
from utils.database import get_all_chats, get_stats

_start_time = time.time()


def back_to_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️  Back to Panel", callback_data="owner_panel")],
    ])


# ─── /panel command ───────────────────────────────────────────────────────────

@bot.on_message(filters.command("panel") & filters.private)
@owner_only
@error_handler
async def panel_cmd(client: Client, message: Message):
    panel_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🖼️  Set Start Pic", callback_data="owner_setpic_info"),
            InlineKeyboardButton("📡  Active VCs", callback_data="owner_activevc"),
        ],
        [
            InlineKeyboardButton("📢  Broadcast", callback_data="owner_broadcast_info"),
            InlineKeyboardButton("📊  Bot Stats", callback_data="owner_stats"),
        ],
        [
            InlineKeyboardButton("📋  Chat List", callback_data="owner_chatlist"),
            InlineKeyboardButton("🔧  Maintenance", callback_data="owner_maintenance"),
        ],
        [
            InlineKeyboardButton("🔄  Reload Plugins", callback_data="owner_reload"),
            InlineKeyboardButton("🔁  Restart Bot", callback_data="owner_restart"),
        ],
    ])
    await message.reply(
        "👑 **OWNER CONTROL PANEL**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Welcome back, **Master** 🫡\n"
        "Choose an action below:\n\n"
        "🖼️ **Set Start Pic** — Change the bot's start image\n"
        "📡 **Active VCs** — See all active voice chats\n"
        "📢 **Broadcast** — Send message to all chats\n"
        "📊 **Bot Stats** — CPU, RAM, uptime, totals\n"
        "📋 **Chat List** — All served groups\n"
        "🔧 **Maintenance** — Toggle maintenance mode\n"
        "🔄 **Reload** — Hot-reload all plugins\n"
        "🔁 **Restart** — Full bot restart\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=panel_markup,
    )


# ─── Owner panel main (callback from start.py) ────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_panel$"))
@error_handler
async def cb_panel(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    panel_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🖼️  Set Start Pic", callback_data="owner_setpic_info"),
            InlineKeyboardButton("📡  Active VCs", callback_data="owner_activevc"),
        ],
        [
            InlineKeyboardButton("📢  Broadcast", callback_data="owner_broadcast_info"),
            InlineKeyboardButton("📊  Bot Stats", callback_data="owner_stats"),
        ],
        [
            InlineKeyboardButton("📋  Chat List", callback_data="owner_chatlist"),
            InlineKeyboardButton("🔧  Maintenance", callback_data="owner_maintenance"),
        ],
        [
            InlineKeyboardButton("🔄  Reload Plugins", callback_data="owner_reload"),
            InlineKeyboardButton("🔁  Restart Bot", callback_data="owner_restart"),
        ],
        [
            InlineKeyboardButton("◀️  Back", callback_data="owner_back_home"),
        ],
    ])
    await cb.message.edit_text(
        "👑 **OWNER CONTROL PANEL**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Welcome back, **Master** 🫡\n"
        "Choose an action below:\n\n"
        "🖼️ **Set Start Pic** — Change the bot's start image\n"
        "📡 **Active VCs** — See all active voice chats\n"
        "📢 **Broadcast** — Send message to all chats\n"
        "📊 **Bot Stats** — CPU, RAM, uptime, totals\n"
        "📋 **Chat List** — All served groups\n"
        "🔧 **Maintenance** — Toggle maintenance mode\n"
        "🔄 **Reload** — Hot-reload all plugins\n"
        "🔁 **Restart** — Full bot restart\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=panel_markup,
    )
    await cb.answer()


# ─── Bot Stats ────────────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_stats$"))
@error_handler
async def cb_stats(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    db_stats = await get_stats()
    uptime_sec = int(time.time() - _start_time)
    h = uptime_sec // 3600
    m = (uptime_sec % 3600) // 60
    s = uptime_sec % 60

    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    text = (
        "📊 **BOT STATISTICS**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🕒 **Uptime:** `{h}h {m}m {s}s`\n\n"
        "💻 **System:**\n"
        f"  ▸ CPU: `{cpu}%`\n"
        f"  ▸ RAM: `{ram.percent}%` ({ram.used // 1024 // 1024}MB / {ram.total // 1024 // 1024}MB)\n"
        f"  ▸ Disk: `{disk.percent}%` ({disk.used // 1024 // 1024 // 1024}GB / {disk.total // 1024 // 1024 // 1024}GB)\n\n"
        "📈 **Database:**\n"
        f"  ▸ Total Chats: `{db_stats['chats']}`\n"
        f"  ▸ Banned Users: `{db_stats['banned']}`\n"
        f"  ▸ Globally Banned: `{db_stats['gbanned']}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await cb.message.edit_text(text, reply_markup=back_to_panel())
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
            "📋 **Chat List**\n\n❌ No chats in database yet.",
            reply_markup=back_to_panel(),
        )
        return await cb.answer()

    lines = [f"📋 **All Served Chats** ({len(chats)} total)\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    for c in chats[:30]:
        title = c.get("title", "Unknown")[:25]
        lines.append(f"▸ `{c['chat_id']}` — {title}")
    if len(chats) > 30:
        lines.append(f"\n_...and {len(chats) - 30} more_")
    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━")

    await cb.message.edit_text("\n".join(lines), reply_markup=back_to_panel())
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
            "📡 **Active Voice Chats**\n\n🔇 No active VCs right now.",
            reply_markup=back_to_panel(),
        )
        return await cb.answer()

    # Get chat titles from DB
    all_chats = await get_all_chats()
    chat_map = {c["chat_id"]: c.get("title", "Unknown") for c in all_chats}

    lines = [f"📡 **Active Voice Chats** ({len(active_ids)} active)\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    for cid in active_ids:
        title = chat_map.get(cid, "Unknown")[:25]
        lines.append(f"🎵 `{cid}` — {title}")
    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━")

    await cb.message.edit_text("\n".join(lines), reply_markup=back_to_panel())
    await cb.answer()


# ─── Broadcast Info ───────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_broadcast_info$"))
@error_handler
async def cb_broadcast_info(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    chats = await get_all_chats()
    await cb.message.edit_text(
        "📢 **Broadcast**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Total chats to broadcast: **{len(chats)}**\n\n"
        "**How to broadcast:**\n"
        "1. Close this panel\n"
        "2. Write or forward your message\n"
        "3. Reply to it with `/broadcast`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
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
        "🖼️ **Set Start Picture**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send a photo to change the bot's start/welcome image.\n\n"
        "**How to use:**\n"
        "Send any photo with caption `/setpic`\n\n"
        "**Current status:**\n"
        "Use `/delpic` to remove the custom image.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
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
    current = getattr(melody, "_maintenance", False)
    new_state = not current
    melody._maintenance = new_state

    status = "🔧 **ON** — Regular users cannot use the bot." if new_state else "✅ **OFF** — Bot is available for everyone."
    await cb.message.edit_text(
        f"🔧 **Maintenance Mode**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Status: {status}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔧 Toggle Again",
                callback_data="owner_maintenance",
            )],
            [InlineKeyboardButton("◀️  Back to Panel", callback_data="owner_panel")],
        ]),
    )
    await cb.answer(f"Maintenance {'ON' if new_state else 'OFF'}", show_alert=True)


# ─── Reload Plugins ───────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_reload$"))
@error_handler
async def cb_reload(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    await cb.message.edit_text("🔄 **Reloading plugins...**\n_Please wait..._")
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
        except Exception as e:
            failed.append(name.split(".")[-1])

    text = (
        f"🔄 **Reload Complete**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Reloaded: `{len(reloaded)}` plugins\n"
    )
    if failed:
        text += f"❌ Failed: `{len(failed)}` — `{'`, `'.join(failed[:10])}`\n"
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━"

    await cb.message.edit_text(text, reply_markup=back_to_panel())


# ─── Restart Bot ──────────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_restart$"))
@error_handler
async def cb_restart(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    await cb.message.edit_text(
        "🔁 **Restarting Melody...**\n_Thodi der mein wapas aaunga! 👋_"
    )
    await cb.answer("Restarting...", show_alert=True)
    await asyncio.sleep(1)
    import os
    os.execv(sys.executable, [sys.executable, "-m", "melody"])
