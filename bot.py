"""
ULTIMATE Telegram Scanner Bot
Scans entire internet for Telegram channels, groups, users.
Reports everything to your Telegram automatically.
"""

import asyncio
import os
import logging
from datetime import datetime, timezone
from telethon import TelegramClient, events
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import API_ID, API_HASH, BOT_TOKEN, MY_CHAT_ID, SCAN_HOUR, SCAN_MINUTE
from scraper import scrape_all_internet
from scanner import scan_all, format_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

os.makedirs("data", exist_ok=True)

user_client = TelegramClient("user_session", API_ID, API_HASH)
bot_client  = TelegramClient("bot_session",  API_ID, API_HASH)

# Message queue to avoid flooding
msg_queue = asyncio.Queue()


async def message_sender():
    """Sends messages from queue with delay to avoid Telegram limits."""
    while True:
        try:
            text = await msg_queue.get()
            await bot_client.send_message(MY_CHAT_ID, text)
            await asyncio.sleep(1)
        except Exception as e:
            log.error(f"Send error: {e}")
            await asyncio.sleep(3)


async def send_msg(text: str):
    await msg_queue.put(text[:4096])


async def on_result(result: dict):
    """Called for every inactive/deleted/unavailable result found."""
    report = format_report(result)
    await send_msg(f"{'='*30}\n{report}")


async def run_daily_scan():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log.info(f"Daily scan started at {now}")

    await send_msg(
        f"🌍 ULTIMATE SCAN STARTED\n"
        f"Time: {now}\n\n"
        f"Searching the entire internet:\n"
        f"✅ TGStat (50 pages per category)\n"
        f"✅ Telemetr\n"
        f"✅ TelegramChannels\n"
        f"✅ TGDB\n"
        f"✅ TelegramGroup\n"
        f"✅ TChannels\n"
        f"✅ Lyzem\n"
        f"✅ Ssuna\n"
        f"✅ Combot\n"
        f"✅ Google Search\n"
        f"✅ Bing Search\n"
        f"✅ DuckDuckGo\n"
        f"✅ Reddit\n"
        f"✅ GitHub Lists\n\n"
        f"Results will appear automatically as found!"
    )

    # Step 1 — Scrape entire internet
    try:
        async def scrape_status(msg):
            await send_msg(f"📊 {msg}")

        channels = await scrape_all_internet(status_callback=scrape_status)
        channel_list = list(channels)

        await send_msg(
            f"✅ INTERNET SCRAPING DONE\n"
            f"Found {len(channel_list):,} unique usernames\n\n"
            f"Now scanning each one:\n"
            f"- Channel activity\n"
            f"- Group activity\n"
            f"- User account status\n"
            f"- Members of each channel\n"
            f"- Deleted accounts\n"
            f"- Unavailable usernames\n\n"
            f"Estimated time: {len(channel_list)//60} minutes\n"
            f"Results coming now..."
        )
    except Exception as e:
        await send_msg(f"Scraping failed: {e}")
        log.error(f"Scraping error: {e}")
        return

    # Step 2 — Scan everything
    try:
        async def on_progress(scanned, total, counts):
            pct = int(scanned / total * 100)
            await send_msg(
                f"⏳ PROGRESS: {scanned:,}/{total:,} ({pct}%)\n"
                f"Inactive channels: {counts['inactive_channels']}\n"
                f"Inactive groups:   {counts['inactive_groups']}\n"
                f"Inactive users:    {counts['inactive_users']}\n"
                f"Deleted accounts:  {counts['deleted']}\n"
                f"Not available:     {counts['not_available']}"
            )

        counts = await scan_all(
            user_client,
            channel_list,
            on_result=on_result,
            on_progress=on_progress
        )
    except Exception as e:
        await send_msg(f"Scanning failed: {e}")
        log.error(f"Scanning error: {e}")
        return

    # Final report
    await send_msg(
        f"🎉 SCAN COMPLETE!\n"
        f"{'='*30}\n"
        f"Total scanned:       {counts['total']:,}\n"
        f"Inactive channels:   {counts['inactive_channels']:,}\n"
        f"Inactive groups:     {counts['inactive_groups']:,}\n"
        f"Inactive users:      {counts['inactive_users']:,}\n"
        f"Deleted accounts:    {counts['deleted']:,}\n"
        f"Username not avail:  {counts['not_available']:,}\n"
        f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Next scan tomorrow at {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC"
    )

    if os.path.exists("data/scanned.txt"):
        os.remove("data/scanned.txt")


async def main():
    await user_client.start()
    me = await user_client.get_me()
    log.info(f"Logged in as {me.first_name}")

    await bot_client.start(bot_token=BOT_TOKEN)
    log.info("Bot started")

    # Start message queue sender
    asyncio.create_task(message_sender())

    await send_msg(
        f"✅ ULTIMATE BOT ONLINE!\n"
        f"{'='*30}\n"
        f"Scanning as: {me.first_name}\n"
        f"Daily scan: {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC\n\n"
        f"Scans everything:\n"
        f"🌍 Entire internet\n"
        f"📢 All channels\n"
        f"👥 All groups\n"
        f"👤 All members\n"
        f"👑 All admins/owners\n"
        f"❌ Deleted accounts\n"
        f"🚫 Unavailable usernames\n\n"
        f"Commands:\n"
        f"/scan - Start now\n"
        f"/status - Check progress\n"
        f"/stop - Stop scan"
    )

    @bot_client.on(events.NewMessage(pattern="/scan"))
    async def handle_scan(event):
        if event.sender_id != MY_CHAT_ID:
            return
        await event.reply("🌍 Starting ultimate scan now...")
        asyncio.create_task(run_daily_scan())

    @bot_client.on(events.NewMessage(pattern="/status"))
    async def handle_status(event):
        if event.sender_id != MY_CHAT_ID:
            return
        total = 0
        scanned = 0
        if os.path.exists("data/all_channels.txt"):
            with open("data/all_channels.txt") as f:
                total = sum(1 for _ in f)
        if os.path.exists("data/scanned.txt"):
            with open("data/scanned.txt") as f:
                scanned = sum(1 for _ in f)
        inactive = 0
        if os.path.exists("data/results.csv"):
            with open("data/results.csv") as f:
                inactive = sum(1 for line in f if "inactive" in line or "deleted" in line or "not_available" in line)

        await event.reply(
            f"📊 STATUS\n"
            f"{'='*25}\n"
            f"Total found:    {total:,}\n"
            f"Scanned today:  {scanned:,}\n"
            f"Inactive/dead:  {inactive:,}\n"
            f"Remaining:      {max(0, total-scanned):,}\n"
            f"Next scan: {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC"
        )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_daily_scan, "cron",
        hour=SCAN_HOUR, minute=SCAN_MINUTE,
        timezone="UTC"
    )
    scheduler.start()

    await bot_client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
