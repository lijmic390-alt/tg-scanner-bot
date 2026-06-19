"""
Telegram Inactive Channel Scanner Bot
Runs daily, scrapes multiple websites, scans all channels,
sends inactive ones straight to your Telegram.
"""

import asyncio
import os
import logging
from datetime import datetime, timezone
from telethon import TelegramClient, events
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import (
    API_ID, API_HASH, BOT_TOKEN, MY_CHAT_ID,
    SCAN_HOUR, SCAN_MINUTE
)
from scraper import scrape_all_sites
from scanner import scan_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Two clients: one user account (to read channels), one bot (to send messages)
user_client = TelegramClient("user_session", API_ID, API_HASH)
bot_client  = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)


async def send_msg(text: str):
    """Send a message to your Telegram."""
    try:
        await bot_client.send_message(MY_CHAT_ID, text, parse_mode="markdown")
    except Exception as e:
        log.error(f"Failed to send message: {e}")


async def send_inactive_results(batch: list):
    """Format and send a batch of inactive channels."""
    if not batch:
        return

    lines = []
    for r in batch:
        level = r.get("level", "inactive")
        members = f"{r['members']:,}" if r.get("members") else "?"
        lines.append(
            f"{level}\n"
            f"  👤 @{r['username']} — {r.get('title','')}\n"
            f"  👥 {members} members | 📅 Last post: {r.get('last_post','never')} ({r.get('days_ago','?')}d ago)\n"
            f"  🔗 t.me/{r['username']}"
        )

    msg = "📡 *Inactive Channels Found*\n\n" + "\n\n".join(lines)

    # Telegram has a 4096 char limit per message — split if needed
    if len(msg) > 4000:
        chunks = []
        current = "📡 *Inactive Channels Found*\n\n"
        for line in lines:
            if len(current) + len(line) > 3800:
                chunks.append(current)
                current = ""
            current += line + "\n\n"
        if current:
            chunks.append(current)
        for chunk in chunks:
            await send_msg(chunk)
            await asyncio.sleep(0.5)
    else:
        await send_msg(msg)


async def run_daily_scan():
    """The main daily job — scrape + scan + report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log.info(f"Starting daily scan at {now}")

    await send_msg(f"🚀 *Daily scan started!*\n🕐 {now}\n\nScraping channels from TGStat, Telemetr, TelegramChannels and more...")

    # Step 1: Scrape all websites
    try:
        async def scrape_status(msg):
            await send_msg(f"📊 {msg}")

        channels = await scrape_all_sites(status_callback=scrape_status)
        channel_list = list(channels)
        await send_msg(f"✅ *Scraping done!*\nFound *{len(channel_list):,}* unique channels\n\nNow scanning for inactivity... this will take a while ⏳")
    except Exception as e:
        await send_msg(f"❌ Scraping failed: {e}")
        log.error(f"Scraping error: {e}")
        return

    # Step 2: Scan all channels
    try:
        async def on_progress(scanned, total, inactive):
            pct = int(scanned / total * 100)
            await send_msg(f"⏳ Progress: {scanned:,}/{total:,} ({pct}%) | 💤 {inactive} inactive found so far")

        inactive_count = await scan_all(
            user_client,
            channel_list,
            on_inactive=send_inactive_results,
            on_progress=on_progress
        )
    except Exception as e:
        await send_msg(f"❌ Scanning failed: {e}")
        log.error(f"Scanning error: {e}")
        return

    # Step 3: Final summary
    await send_msg(
        f"🎉 *Daily scan complete!*\n\n"
        f"📊 Scanned: *{len(channel_list):,}* channels\n"
        f"💤 Inactive: *{inactive_count}* channels\n"
        f"🕐 Finished: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Next scan tomorrow at {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC 🔄"
    )
    log.info(f"Daily scan complete. {inactive_count} inactive channels found.")

    # Reset scanned list so tomorrow it scans fresh
    if os.path.exists("data/scanned.txt"):
        os.remove("data/scanned.txt")


async def main():
    # Start both clients
    await user_client.start()
    me = await user_client.get_me()
    log.info(f"User client: logged in as {me.first_name}")

    await send_msg(
        f"✅ *Bot is online!*\n\n"
        f"👤 Scanning as: {me.first_name}\n"
        f"⏰ Daily scan runs every day at *{SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC*\n\n"
        f"Send /scan to run a manual scan now\n"
        f"Send /status to check bot status"
    )

    # Handle /scan command
    @bot_client.on(events.NewMessage(pattern="/scan"))
    async def handle_scan(event):
        if event.sender_id != MY_CHAT_ID:
            return
        await event.reply("🚀 Starting manual scan now...")
        asyncio.create_task(run_daily_scan())

    # Handle /status command
    @bot_client.on(events.NewMessage(pattern="/status"))
    async def handle_status(event):
        if event.sender_id != MY_CHAT_ID:
            return
        scanned = 0
        if os.path.exists("data/scanned.txt"):
            with open("data/scanned.txt") as f:
                scanned = sum(1 for _ in f)
        total = 0
        if os.path.exists("data/all_channels.txt"):
            with open("data/all_channels.txt") as f:
                total = sum(1 for _ in f)
        await event.reply(
            f"📊 *Bot Status*\n\n"
            f"✅ Running\n"
            f"📋 Total channels found: {total:,}\n"
            f"🔍 Already scanned today: {scanned:,}\n"
            f"⏰ Next scan: {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC"
        )

    # Schedule daily scan
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_daily_scan,
        "cron",
        hour=SCAN_HOUR,
        minute=SCAN_MINUTE,
        timezone="UTC"
    )
    scheduler.start()
    log.info(f"Scheduler started — daily scan at {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC")

    # Keep running forever
    await bot_client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
