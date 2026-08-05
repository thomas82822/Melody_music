"""
📋 /logs — send bot logs (owner only)
FIX: decorator order corrected — @error_handler outer, @owner_only inner
     (consistent with all other command handlers in the codebase)
"""
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from melody import bot
from utils.decorators import owner_only, error_handler
from utils.formatters import quote_html


@bot.on_message(filters.command("logs") & filters.private)
@error_handler
@owner_only
async def logs_cmd(client: Client, message: Message):
    await message.reply(
        quote_html("📋 **Bot Logs** are streamed to the LOG_GROUP channel.\nUse `/chatlist` to see all served chats."),
        parse_mode=enums.ParseMode.HTML,
    )


@bot.on_message(filters.command("chatlist") & filters.private)
@error_handler
@owner_only
async def chatlist_cmd(client: Client, message: Message):
    from utils.database import get_all_chats
    chats = await get_all_chats()
    if not chats:
        return await message.reply(quote_html("❌ No chats in database."), parse_mode=enums.ParseMode.HTML)

    lines = [f"**📋 All Served Chats ({len(chats)} total):**\n"]
    for c in chats[:50]:
        lines.append(f"• `{c['chat_id']}` — {c.get('title', 'Unknown')[:30]}")
    if len(chats) > 50:
        lines.append(f"\n_...and {len(chats) - 50} more_")

    await message.reply(quote_html("\n".join(lines)), parse_mode=enums.ParseMode.HTML)


@bot.on_message(filters.command("maintenance") & filters.private)
@error_handler
@owner_only
async def maintenance_cmd(client: Client, message: Message):
    args = message.command
    if len(args) < 2:
        return await message.reply(
            quote_html("**Usage:** `/maintenance on` or `/maintenance off`"), parse_mode=enums.ParseMode.HTML
        )

    state = args[1].lower()
    if state == "on":
        import melody
        melody._maintenance = True
        await message.reply(
            quote_html("🔧 **Maintenance mode ON.** Regular users can't use the bot."),
            parse_mode=enums.ParseMode.HTML,
        )
    elif state == "off":
        import melody
        melody._maintenance = False
        await message.reply(quote_html("✅ **Maintenance mode OFF.**"), parse_mode=enums.ParseMode.HTML)
