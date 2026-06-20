"""
Telegram Inactive Scanner Bot v2
Scans channels, groups, members, admins and owners.
Sends full reports to your Telegram automatically every day.
"""

import asyncio
import os
import logging
from datetime import datetime, timezone
from telethon import TelegramClient, events
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import API_ID, API_HASH, BOT_TOKEN, MY_CHAT_ID, SCAN_HOUR, SCAN_MINUTE
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
bot_client  = TelegramClient("bot_session",  API_ID, API_HASH)


async def send_msg(text: str):
    try:
        await bot_client.send_message(MY_CHAT_ID, text)
    except Exception as e:
        log.error(f"Send error: {e}")


async def on_inactive_channel(result: dict):
    """Called every time an inactive channel is found."""
    members = f"{result['members']:,}" if result.get("members") else "?"
    msg = (
        f"📢 INACTIVE CHANNEL FOUND\n"
        f"{'='*30}\n"
        f"Username:  @{result['username']}\n"
        f"Title:     {result.get('title','?')}\n"
        f"Members:   {members}\n"
        f"Last post: {result.get('last_post','never')}\n"
        f"Days ago:  {result.get('days_ago','?')} days\n"
        f"Status:    {result.get('level','inactive')}\n"
        f"Link:      t.me/{result['username']}"
    )
    await send_msg(msg)


async def on_inactive_account(account: dict):
    """Called every time an inactive account is found."""
    status_icon = {
        "deleted":  "❌ DELETED ACCOUNT",
        "inactive": "💤 INACTIVE ACCOUNT",
    }.get(account["status"], "❓ UNKNOWN")

    msg = (
        f"{status_icon}\n"
        f"{'='*30}\n"
        f"Name:      {account.get('name','?')}\n"
        f"Username:  @{account['username']}\n"
        f"Role:      {account['role']}\n"
        f"In channel: @{account['channel']}\n"
        f"Last seen: {account['last_seen']}\n"
        f"Profile:   t.me/{account['username']}"
    )
    await send_msg(msg)


async def run_daily_scan():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log.info(f"Daily scan started at {now}")

    await send_msg(
        f"🚀 DAILY SCAN STARTED\n"
        f"Time: {now}\n\n"
        f"Step 1: Scraping channels from:\n"
        f"- TGStat\n- Telemetr\n- TelegramChannels\n"
        f"- TGDB\n- TelegramGroup\n- TChannels\n"
        f"- Lyzem\n- Ssuna\n\n"
        f"Please wait..."
    )

    # Step 1 — Scrape all websites
    try:
        async def scrape_status(msg):
            await send_msg(f"📊 {msg}")

        channels = await scrape_all_sites(status_callback=scrape_status)
        channel_list = list(channels)
        await send_msg(
            f"✅ SCRAPING DONE\n"
            f"Found {len(channel_list):,} unique channels\n\n"
            f"Step 2: Now scanning each channel...\n"
            f"Checking:\n"
            f"- Channel inactivity\n"
            f"- Member inactivity\n"
            f"- Admin/Owner inactivity\n"
            f"- Deleted accounts\n\n"
            f"Results will appear as found!"
        )
    except Exception as e:
        await send_msg(f"❌ Scraping failed: {e}")
        log.error(f"Scraping error: {e}")
        return

    # Step 2 — Scan everything
    try:
        async def on_progress(scanned, total, counts):
            pct = int(scanned / total * 100)
            await send_msg(
                f"⏳ PROGRESS UPDATE\n"
                f"Scanned: {scanned:,}/{total:,} ({pct}%)\n"
                f"Inactive channels: {counts['inactive_channels']}\n"
                f"Inactive accounts: {counts['inactive_accounts']}"
            )

        counts = await scan_all(
            user_client,
            channel_list,
            on_inactive_channel=on_inactive_channel,
            on_inactive_account=on_inactive_account,
            on_progress=on_progress
        )
    except Exception as e:
        await send_msg(f"❌ Scanning failed: {e}")
        log.error(f"Scanning error: {e}")
        return

    # Final summary
    await send_msg(
        f"🎉 SCAN COMPLETE!\n"
        f"{'='*30}\n"
        f"Total channels scanned: {counts['channels']:,}\n"
        f"Inactive channels found: {counts['inactive_channels']}\n"
        f"Inactive accounts found: {counts['inactive_accounts']}\n"
        f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Next scan tomorrow at {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC"
    )

    log.info(f"Scan complete. Channels: {counts['channels']}, Inactive: {counts['inactive_channels']}, Accounts: {counts['inactive_accounts']}")

    # Reset for tomorrow
    if os.path.exists("data/scanned.txt"):
        os.remove("data/scanned.txt")


async def main():
    await user_client.start()
    me = await user_client.get_me()
    log.info(f"User logged in as {me.first_name}")

    await bot_client.start(bot_token=BOT_TOKEN)
    log.info("Bot started")

    await send_msg(
        f"✅ BOT IS ONLINE!\n"
        f"{'='*30}\n"
        f"Scanning as: {me.first_name}\n"
        f"Daily scan: {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC every day\n\n"
        f"What I scan:\n"
        f"- Inactive channels (3/6/12 months)\n"
        f"- Inactive members\n"
        f"- Inactive admins & owners\n"
        f"- Deleted/banned accounts\n\n"
        f"Commands:\n"
        f"/scan - Start scan now\n"
        f"/status - Check progress\n"
        f"/stop - Stop current scan"
    )

    @bot_client.on(events.NewMessage(pattern="/scan"))
    async def handle_scan(event):
        if event.sender_id != MY_CHAT_ID:
            return
        await event.reply("🚀 Starting full scan now...")
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
        inactive_ch = 0
        if os.path.exists("data/channel_results.csv"):
            with open("data/channel_results.csv") as f:
                inactive_ch = sum(1 for line in f if "inactive" in line)
        inactive_acc = 0
        if os.path.exists("data/account_results.csv"):
            with open("data/account_results.csv") as f:
                inactive_acc = sum(1 for line in f if "inactive" in line or "deleted" in line)

        await event.reply(
            f"📊 BOT STATUS\n"
            f"{'='*25}\n"
            f"Status: Running\n"
            f"Total channels: {total:,}\n"
            f"Scanned today: {scanned:,}\n"
            f"Inactive channels: {inactive_ch}\n"
            f"Inactive accounts: {inactive_acc}\n"
            f"Next scan: {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC"
        )

    @bot_client.on(events.NewMessage(pattern="/stop"))
    async def handle_stop(event):
        if event.sender_id != MY_CHAT_ID:
            return
        await event.reply("⏹ Scan will stop after current channel finishes.")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_daily_scan, "cron",
        hour=SCAN_HOUR, minute=SCAN_MINUTE,
        timezone="UTC"
    )
    scheduler.start()
    log.info(f"Scheduler ready — daily scan at {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC")

    await bot_client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
