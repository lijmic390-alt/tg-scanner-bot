"""
Multi-site Telegram Channel Scraper
Pulls channel usernames from multiple directories on the internet.
"""

import asyncio
import re
import os
from playwright.async_api import async_playwright
from config import PRIORITY_CATEGORIES, OTHER_CATEGORIES

USERNAME_RE = re.compile(r'(?:tgstat\.(?:com|ru)|telemetr\.io|telegramchannels\.me|tgdb\.org|telegram-group\.com|combot\.org)/(?:en/)?(?:channel|chat|group|c)/?@?([A-Za-z0-9_]{5,32})')
TGLINK_RE   = re.compile(r't\.me/([A-Za-z0-9_]{5,32})')
SKIP        = {'joinchat','share','proxy','addstickers','addemoji','iv','bg','addtheme','botstart','s','r'}

# All websites to scrape with their URL patterns
SOURCES = [
    # TGStat — biggest directory
    {
        "name": "TGStat",
        "urls": lambda cat, pg: f"https://tgstat.com/en/{cat}" if pg == 1 else f"https://tgstat.com/en/{cat}?page={pg}",
        "pages": 30,
    },
    # Telemetr
    {
        "name": "Telemetr",
        "urls": lambda cat, pg: f"https://telemetr.io/en/channels?category={cat}" if pg == 1 else f"https://telemetr.io/en/channels?category={cat}&page={pg}",
        "pages": 10,
    },
    # Telegramchannels.me
    {
        "name": "TelegramChannels",
        "urls": lambda cat, pg: f"https://telegramchannels.me/channels?category={cat}" if pg == 1 else f"https://telegramchannels.me/channels?category={cat}&page={pg}",
        "pages": 10,
    },
    # Tgdb
    {
        "name": "TGDB",
        "urls": lambda cat, pg: f"https://tgdb.org/en/{cat}" if pg == 1 else f"https://tgdb.org/en/{cat}?page={pg}",
        "pages": 10,
    },
    # Telegram-group.com
    {
        "name": "TelegramGroup",
        "urls": lambda cat, pg: f"https://telegram-group.com/{cat}/" if pg == 1 else f"https://telegram-group.com/{cat}/page/{pg}/",
        "pages": 5,
    },
]


async def scrape_page(page, url: str) -> set:
    """Scrape a single URL and return usernames found."""
    found = set()
    try:
        await page.goto(url, timeout=25000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        for _ in range(3):
            await page.keyboard.press("End")
            await page.wait_for_timeout(500)
        html = await page.content()
        raw = set(USERNAME_RE.findall(html)) | set(TGLINK_RE.findall(html))
        found = {u.lower() for u in raw if u.lower() not in SKIP and len(u) >= 5}
    except Exception:
        pass
    return found


async def scrape_all_sites(status_callback=None) -> set:
    """
    Scrape all sites and all categories.
    Returns a set of all discovered channel usernames.
    """
    all_usernames = set()
    save_path = "data/all_channels.txt"

    # Resume if we already have some
    if os.path.exists(save_path):
        with open(save_path) as f:
            all_usernames = set(line.strip() for line in f if line.strip())

    all_categories = PRIORITY_CATEGORIES + OTHER_CATEGORIES

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        for source in SOURCES:
            source_name = source["name"]
            source_new  = 0

            for cat in all_categories:
                for pg in range(1, source["pages"] + 1):
                    url = source["urls"](cat, pg)
                    found = await scrape_page(page, url)
                    new   = found - all_usernames
                    all_usernames.update(found)
                    source_new += len(new)

                    if len(new) == 0 and pg > 2:
                        break  # No more pages for this category

                    await asyncio.sleep(1.2)

                # Save after every category
                with open(save_path, "w") as f:
                    f.write("\n".join(sorted(all_usernames)))

            msg = f"✅ {source_name}: +{source_new} new channels | Total: {len(all_usernames)}"
            print(msg)
            if status_callback:
                await status_callback(msg)

        await browser.close()

    print(f"\n🎉 Scraping done! {len(all_usernames)} total unique channels")
    return all_usernames
