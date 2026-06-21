"""
Telegram Inside Scanner Bot
Works from inside Telegram — no websites needed.
Finds inactive channels, groups, users and sends to your Telegram.
"""

import asyncio
import os
import logging
from datetime import datetime, timezone
from telethon import TelegramClient, events
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import API_ID, API_HASH, BOT_TOKEN, MY_CHAT_ID, SCAN_HOUR, SCAN_MINUTE
from crawler import crawl_all_channels
from scanner import scan_all, format_channel_report, format_user_report, format_unavailable_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

os.makedirs("data", exist_ok=True)

user_client = TelegramClient("user_session", API_ID, API_HASH)
bot_client  = TelegramClient("bot_session",  API_ID, API_HASH)

msg_queue = asyncio.Queue()


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


async def on_result(result: dict):
    """Send every inactive/deleted/unavailable result immediately."""
    status = result.get("status")
    typ    = result.get("type")

    if status == "not_available":
        await send_msg(format_unavailable_report(result["username"]))
    elif typ in ("channel", "group") and status in ("inactive", "empty"):
        await send_msg(format_channel_report(result))
    elif typ == "user" and status in ("inactive", "deleted"):
        await send_msg(format_user_report(result))


async def run_daily_scan():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log.info(f"Scan started at {now}")

    await send_msg(
        f"🚀 SCAN STARTED!\n"
        f"Time: {now}\n\n"
        f"Working from INSIDE Telegram:\n"
        f"Step 1: Crawling channels from big seeds\n"
        f"Step 2: Scanning all members\n"
        f"Step 3: Finding inactive/deleted accounts\n\n"
        f"Results will appear automatically!"
    )

    # Step 1 — Crawl from inside Telegram
    try:
        async def crawl_status(msg):
            await send_msg(f"🕸 {msg}")

        channels = await crawl_all_channels(user_client, status_callback=crawl_status)
        channel_list = list(channels)

        await send_msg(
            f"✅ CRAWLING DONE!\n"
            f"Found {len(channel_list):,} channels/groups\n\n"
            f"Now scanning each one...\n"
            f"Results coming now! 📨"
        )
    except Exception as e:
        await send_msg(f"❌ Crawling failed: {e}")
        log.error(f"Crawl error: {e}")
        return

    # Step 2 — Scan everything
    try:
        async def on_progress(scanned, total, counts):
            pct = int(scanned / total * 100)
            await send_msg(
                f"⏳ PROGRESS: {scanned:,}/{total:,} ({pct}%)\n"
                f"📢 Inactive channels: {counts['inactive_channels']}\n"
                f"👥 Inactive groups:   {counts['inactive_groups']}\n"
                f"👤 Inactive users:    {counts['inactive_users']}\n"
                f"❌ Deleted accounts:  {counts['deleted']}\n"
                f"🚫 Not available:     {counts['not_available']}"
            )

        counts = await scan_all(
            user_client,
            channel_list,
            on_result=on_result,
            on_progress=on_progress
        )
    except Exception as e:
        await send_msg(f"❌ Scanning failed: {e}")
        log.error(f"Scan error: {e}")
        return

    # Final summary
    await send_msg(
        f"🎉 SCAN COMPLETE!\n"
        f"{'='*30}\n"
        f"Total scanned:      {counts['total']:,}\n"
        f"Inactive channels:  {counts['inactive_channels']:,}\n"
        f"Inactive groups:    {counts['inactive_groups']:,}\n"
        f"Inactive users:     {counts['inactive_users']:,}\n"
        f"Deleted accounts:   {counts['deleted']:,}\n"
        f"Not available:      {counts['not_available']:,}\n"
        f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Next scan tomorrow at {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC 🔄"
    )

    # Reset for tomorrow
    for f in ["data/scanned.txt", "data/crawled.txt"]:
        if os.path.exists(f):
            os.remove(f)


async def main():
    await user_client.start()
    me = await user_client.get_me()
    log.info(f"Logged in as {me.first_name}")

    await bot_client.start(bot_token=BOT_TOKEN)
    log.info("Bot started")

    asyncio.create_task(message_sender())

    await send_msg(
        f"✅ BOT IS ONLINE!\n"
        f"{'='*30}\n"
        f"Scanning as: {me.first_name}\n"
        f"Daily scan: {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC\n\n"
        f"Works from INSIDE Telegram:\n"
        f"📢 Finds inactive channels\n"
        f"👥 Finds inactive groups\n"
        f"👤 Finds inactive members\n"
        f"👑 Finds inactive admins\n"
        f"❌ Finds deleted accounts\n"
        f"🚫 Finds unavailable usernames\n\n"
        f"Commands:\n"
        f"/scan — Start now\n"
        f"/status — Check progress\n"
        f"/stop — Stop scan"
    )

    @bot_client.on(events.NewMessage(pattern="/scan"))
    async def handle_scan(event):
        if event.sender_id != MY_CHAT_ID:
            return
        await event.reply("🚀 Starting scan now...")
        asyncio.create_task(run_daily_scan())

    @bot_client.on(events.NewMessage(pattern="/status"))
    async def handle_status(event):
        if event.sender_id != MY_CHAT_ID:
            return
        total = scanned = inactive = 0
        if os.path.exists("data/all_channels.txt"):
            with open("data/all_channels.txt") as f:
                total = sum(1 for _ in f)
        if os.path.exists("data/scanned.txt"):
            with open("data/scanned.txt") as f:
                scanned = sum(1 for _ in f)
        if os.path.exists("data/results.csv"):
            with open("data/results.csv") as f:
                inactive = sum(1 for line in f if any(
                    x in line for x in ["inactive","deleted","not_available","empty"]
                ))
        await event.reply(
            f"📊 STATUS\n"
            f"{'='*25}\n"
            f"Total found:    {total:,}\n"
            f"Scanned:        {scanned:,}\n"
            f"Inactive/dead:  {inactive:,}\n"
            f"Remaining:      {max(0,total-scanned):,}\n"
            f"Next scan: {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC"
        )

    @bot_client.on(events.NewMessage(pattern="/stop"))
    async def handle_stop(event):
        if event.sender_id != MY_CHAT_ID:
            return
        await event.reply("⏹ Stopping after current channel...")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_daily_scan, "cron",
        hour=SCAN_HOUR, minute=SCAN_MINUTE, timezone="UTC"
    )
    scheduler.start()
    log.info(f"Daily scan scheduled at {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC")

    await bot_client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
