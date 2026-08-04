"""
💻 /shell — run shell commands (owner only)
"""
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from utils.decorators import owner_only, error_handler


@bot.on_message(filters.command(["shell", "sh", "bash", "exec"]) & filters.private)
@owner_only
@error_handler
async def shell_cmd(client: Client, message: Message):
    cmd = " ".join(message.command[1:])
    if not cmd:
        return await message.reply("**Usage:** `/shell <command>`")

    msg = await message.reply(f"⚙️ Running: `{cmd[:100]}`...")

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        output = (stdout + stderr).decode().strip()
        if not output:
            output = "✅ Done (no output)"
        await msg.edit(f"**$ {cmd[:50]}**\n```\n{output[:3500]}\n```")
    except asyncio.TimeoutError:
        await msg.edit("⏰ Command timed out after 30 seconds.")
    except Exception as e:
        await msg.edit(f"❌ Error: `{e}`")
