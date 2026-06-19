"""
Telegram Inactive Channel Scanner Bot - Fixed Version
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
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

os.makedirs("data", exist_ok=True)

user_client = TelegramClient("user_session", API_ID, API_HASH)
bot_client = TelegramClient("bot_session", API_ID, API_HASH)


async def send_msg(text: str):
    try:
        await bot_client.send_message(MY_CHAT_ID, text, parse_mode="markdown")
    except Exception as e:
        log.error(f"Send error: {e}")


async def send_inactive_results(batch: list):
    if not batch:
        return
    lines = []
    for r in batch:
        level = r.get("level", "inactive")
        members = f"{r['members']:,}" if r.get("members") else "?"
        lines.append(
            f"{level}\n"
            f"  @{r['username']} - {r.get('title','')}\n"
            f"  {members} members | Last post: {r.get('last_post','never')} ({r.get('days_ago','?')}d ago)\n"
            f"  t.me/{r['username']}"
        )
    msg = "Inactive Channels Found\n\n" + "\n\n".join(lines)
    if len(msg) > 4000:
        chunks = []
        current = "Inactive Channels Found\n\n"
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
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log.info(f"Daily scan started at {now}")
    await send_msg(f"Daily scan started! {now}\n\nScraping channels from multiple websites...")

    try:
        channels = await scrape_all_sites()
        channel_list = list(channels)
        await send_msg(f"Scraping done! Found {len(channel_list):,} channels\n\nNow scanning...")
    except Exception as e:
        await send_msg(f"Scraping failed: {e}")
        return

    try:
        async def on_progress(scanned, total, inactive):
            pct = int(scanned / total * 100)
            await send_msg(f"Progress: {scanned:,}/{total:,} ({pct}%) | {inactive} inactive found")

        inactive_count = await scan_all(
            user_client,
            channel_list,
            on_inactive=send_inactive_results,
            on_progress=on_progress
        )
    except Exception as e:
        await send_msg(f"Scanning failed: {e}")
        return

    await send_msg(
        f"Scan complete!\n\n"
        f"Scanned: {len(channel_list):,} channels\n"
        f"Inactive: {inactive_count}\n"
        f"Done: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Next scan tomorrow at {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC"
    )

    if os.path.exists("data/scanned.txt"):
        os.remove("data/scanned.txt")


async def main():
    await user_client.start()
    me = await user_client.get_me()
    log.info(f"User logged in as {me.first_name}")

    await bot_client.start(bot_token=BOT_TOKEN)
    log.info("Bot client started")

    await send_msg(
        f"Bot is online!\n\n"
        f"Scanning as: {me.first_name}\n"
        f"Daily scan: every day at {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC\n\n"
        f"Send /scan to scan now\n"
        f"Send /status to check status"
    )

    @bot_client.on(events.NewMessage(pattern="/scan"))
    async def handle_scan(event):
        if event.sender_id != MY_CHAT_ID:
            return
        await event.reply("Starting scan now...")
        asyncio.create_task(run_daily_scan())

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
            f"Bot Status\n\n"
            f"Running\n"
            f"Total channels: {total:,}\n"
            f"Scanned today: {scanned:,}\n"
            f"Next scan: {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC"
        )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_scan, "cron", hour=SCAN_HOUR, minute=SCAN_MINUTE, timezone="UTC")
    scheduler.start()
    log.info(f"Scheduler set for {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC daily")

    await bot_client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
