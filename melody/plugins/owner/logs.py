"""
📋 /logs — send bot logs (owner only)
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from utils.decorators import owner_only, error_handler


@bot.on_message(filters.command("logs") & filters.private)
@owner_only
@error_handler
async def logs_cmd(client: Client, message: Message):
    await message.reply("📋 **Bot Logs** are streamed to the LOG_GROUP channel.\nUse `/chatlist` to see all served chats.")


@bot.on_message(filters.command("chatlist") & filters.private)
@owner_only
@error_handler
async def chatlist_cmd(client: Client, message: Message):
    from utils.database import get_all_chats
    chats = await get_all_chats()
    if not chats:
        return await message.reply("❌ No chats in database.")

    lines = [f"**📋 All Served Chats ({len(chats)} total):**\n"]
    for c in chats[:50]:
        lines.append(f"• `{c['chat_id']}` — {c.get('title', 'Unknown')[:30]}")
    if len(chats) > 50:
        lines.append(f"\n_...and {len(chats) - 50} more_")

    await message.reply("\n".join(lines))


@bot.on_message(filters.command("maintenance") & filters.private)
@owner_only
@error_handler
async def maintenance_cmd(client: Client, message: Message):
    args = message.command
    if len(args) < 2:
        return await message.reply("**Usage:** `/maintenance on` or `/maintenance off`")

    state = args[1].lower()
    if state == "on":
        import melody
        melody._maintenance = True
        await message.reply("🔧 **Maintenance mode ON.** Regular users can't use the bot.")
    elif state == "off":
        import melody
        melody._maintenance = False
        await message.reply("✅ **Maintenance mode OFF.**")
