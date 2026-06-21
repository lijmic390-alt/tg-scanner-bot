"""
Scammer Detection Bot
Watches channels and groups in real time.
Detects scammers and sends alerts to your Telegram immediately.
"""

import asyncio
import os
import logging
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import API_ID, API_HASH, BOT_TOKEN, MY_CHAT_ID, SCAM_PATTERNS, SEARCH_KEYWORDS
from joiner import search_and_join

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

os.makedirs("data", exist_ok=True)

user_client = TelegramClient("user_session", API_ID, API_HASH)
bot_client  = TelegramClient("bot_session",  API_ID, API_HASH)

msg_queue  = asyncio.Queue()
scam_count = 0


async def message_sender():
    while True:
        try:
            text = await msg_queue.get()
            await bot_client.send_message(MY_CHAT_ID, text)
            await asyncio.sleep(1.5)
        except Exception as e:
            log.error(f"Send error: {e}")
            await asyncio.sleep(3)


async def send_msg(text: str):
    await msg_queue.put(str(text)[:4096])


def is_scam(text: str):
    if not text:
        return False, None
    text_lower = text.lower()
    for pattern in SCAM_PATTERNS:
        if pattern.lower() in text_lower:
            return True, pattern
    return False, None


async def join_daily():
    async def status(msg):
        await send_msg(f"🔍 {msg}")

    await send_msg(
        f"🔍 Searching for crypto channels and groups...\n"
        f"Joining up to 15 per day safely!"
    )

    joined = await search_and_join(user_client, status_callback=status)

    await send_msg(
        f"✅ Now watching {len(joined)} channels and groups!\n"
        f"Monitoring every message for scammers 24/7..."
    )


async def main():
    await user_client.start()
    me = await user_client.get_me()
    log.info(f"Logged in as {me.first_name}")

    await bot_client.start(bot_token=BOT_TOKEN)
    log.info("Bot started")

    asyncio.create_task(message_sender())

    @user_client.on(events.NewMessage)
    async def watch_messages(event):
        global scam_count
        try:
            if not event.is_channel and not event.is_group:
                return

            text = event.text or ""
            if not text:
                return

            scam_found, pattern = is_scam(text)
            if not scam_found:
                return

            sender = await event.get_sender()
            chat   = await event.get_chat()

            sender_name     = "Unknown"
            sender_username = "unknown"

            if sender:
                first = getattr(sender, "first_name", "") or ""
                last  = getattr(sender, "last_name",  "") or ""
                sender_name     = f"{first} {last}".strip() or "Unknown"
                sender_username = getattr(sender, "username", None) or f"ID:{sender.id}"

            chat_name     = getattr(chat, "title", "Unknown")
            chat_username = getattr(chat, "username", None) or f"ID:{chat.id}"
            is_channel    = isinstance(chat, Channel) and not getattr(chat, "megagroup", False)
            chat_type     = "Channel" if is_channel else "Group"
            members       = getattr(chat, "participants_count", "?")

            scam_count += 1

            alert = (
                f"SCAMMER DETECTED #{scam_count}\n"
                f"{'='*30}\n"
                f"Time:     {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"{chat_type}: @{chat_username}\n"
                f"Name:     {chat_name}\n"
                f"Members:  {members}\n"
                f"{'='*30}\n"
                f"Scammer:  {sender_name}\n"
                f"Username: @{sender_username}\n"
                f"Pattern:  {pattern}\n"
                f"{'='*30}\n"
                f"Message:\n{text[:300]}\n"
                f"{'='*30}\n"
                f"Profile:  t.me/{sender_username}\n"
                f"Link:     t.me/{chat_username}"
            )

            await send_msg(alert)
            log.info(f"Scammer: @{sender_username} in @{chat_username}")

        except Exception as e:
            log.error(f"Watch error: {e}")

    @bot_client.on(events.NewMessage(pattern="/status"))
    async def handle_status(event):
        if event.sender_id != MY_CHAT_ID:
            return
        joined = 0
        if os.path.exists("data/joined.txt"):
            with open("data/joined.txt") as f:
                joined = sum(1 for _ in f)
        await event.reply(
            f"BOT STATUS\n"
            f"{'='*25}\n"
            f"Running: YES\n"
            f"Watching: {joined} channels/groups\n"
            f"Scammers found: {scam_count}\n"
            f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        )

    @bot_client.on(events.NewMessage(pattern="/join"))
    async def handle_join(event):
        if event.sender_id != MY_CHAT_ID:
            return
        await event.reply("Searching and joining new channels/groups...")
        asyncio.create_task(join_daily())

    scheduler = AsyncIOScheduler()
    scheduler.add_job(join_daily, "cron", hour=9, minute=0, timezone="UTC")
    scheduler.start()

    asyncio.create_task(join_daily())

    joined = 0
    if os.path.exists("data/joined.txt"):
        with open("data/joined.txt") as f:
            joined = sum(1 for _ in f)

    await send_msg(
        f"SCAMMER BOT ONLINE!\n"
        f"{'='*30}\n"
        f"Scanning as: {me.first_name}\n\n"
        f"What I do:\n"
        f"- Search Telegram for crypto channels/groups\n"
        f"- Watch every message 24/7\n"
        f"- Detect scammers instantly\n"
        f"- Send you alerts immediately\n\n"
        f"Watching: {joined} channels/groups now\n"
        f"Joining 15 more today!\n\n"
        f"Commands:\n"
        f"/status - Check bot status\n"
        f"/join - Join more channels now"
    )

    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )


if __name__ == "__main__":
    asyncio.run(main())
