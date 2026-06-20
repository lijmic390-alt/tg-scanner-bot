"""
Ultimate Internet-Wide Scraper
Searches everywhere for Telegram channels and groups.
"""

import asyncio
import re
import os
from playwright.async_api import async_playwright
from config import ALL_CATEGORIES, SEARCH_KEYWORDS

TGLINK_RE = re.compile(r't\.me/([A-Za-z0-9_]{5,32})')
SKIP = {
    'joinchat','share','proxy','addstickers','addemoji',
    'iv','bg','addtheme','botstart','s','r','telegrambot'
}

DIRECTORY_SOURCES = [
    {"name": "TGStat",          "url": lambda c,p: f"https://tgstat.com/en/{c}" if p==1 else f"https://tgstat.com/en/{c}?page={p}", "pages": 50},
    {"name": "Telemetr",        "url": lambda c,p: f"https://telemetr.io/en/channels?category={c}" if p==1 else f"https://telemetr.io/en/channels?category={c}&page={p}", "pages": 20},
    {"name": "TelegramChannels","url": lambda c,p: f"https://telegramchannels.me/channels?category={c}" if p==1 else f"https://telegramchannels.me/channels?category={c}&page={p}", "pages": 20},
    {"name": "TGDB",            "url": lambda c,p: f"https://tgdb.org/en/{c}" if p==1 else f"https://tgdb.org/en/{c}?page={p}", "pages": 20},
    {"name": "TelegramGroup",   "url": lambda c,p: f"https://telegram-group.com/{c}/" if p==1 else f"https://telegram-group.com/{c}/page/{p}/", "pages": 15},
    {"name": "TChannels",       "url": lambda c,p: f"https://tchannels.me/category/{c}" if p==1 else f"https://tchannels.me/category/{c}?page={p}", "pages": 15},
    {"name": "Lyzem",           "url": lambda c,p: f"https://lyzem.com/search?q={c}&type=channel" if p==1 else f"https://lyzem.com/search?q={c}&type=channel&page={p}", "pages": 10},
    {"name": "Ssuna",           "url": lambda c,p: f"https://ssuna.net/category/{c}" if p==1 else f"https://ssuna.net/category/{c}?page={p}", "pages": 10},
    {"name": "Combot",          "url": lambda c,p: f"https://combot.org/chats?lng=en&q={c}" if p==1 else f"https://combot.org/chats?lng=en&q={c}&page={p}", "pages": 10},
]

SEARCH_ENGINES = [
    {"name": "Google",     "url": lambda k,p: f"https://www.google.com/search?q=site:t.me+{k.replace(' ','+')}+telegram" if p==1 else f"https://www.google.com/search?q=site:t.me+{k.replace(' ','+')}+telegram&start={p*10}", "pages": 5},
    {"name": "Bing",       "url": lambda k,p: f"https://www.bing.com/search?q=site:t.me+{k.replace(' ','+')}+telegram" if p==1 else f"https://www.bing.com/search?q=site:t.me+{k.replace(' ','+')}+telegram&first={p*10}", "pages": 5},
    {"name": "DuckDuckGo", "url": lambda k,p: f"https://duckduckgo.com/?q=site:t.me+{k.replace(' ','+')}+telegram", "pages": 1},
]

SOCIAL_URLS = [
    # Reddit
    "https://www.reddit.com/r/telegram/",
    "https://www.reddit.com/r/cryptocurrency/search/?q=telegram+channel&sort=new",
    "https://www.reddit.com/r/bitcoin/search/?q=telegram&sort=new",
    "https://www.reddit.com/r/ethereum/search/?q=telegram&sort=new",
    "https://www.reddit.com/r/investing/search/?q=telegram&sort=new",
    "https://www.reddit.com/r/finance/search/?q=telegram&sort=new",
    "https://www.reddit.com/r/forex/search/?q=telegram&sort=new",
    "https://www.reddit.com/r/algotrading/search/?q=telegram&sort=new",
    "https://www.reddit.com/r/defi/search/?q=telegram&sort=new",
    "https://www.reddit.com/r/gaming/search/?q=telegram&sort=new",
    "https://www.reddit.com/r/news/search/?q=telegram&sort=new",
    "https://www.reddit.com/r/worldnews/search/?q=telegram&sort=new",
    # GitHub
    "https://github.com/search?q=telegram+channels+crypto&type=repositories",
    "https://github.com/search?q=telegram+groups+list&type=repositories",
    "https://github.com/search?q=awesome+telegram+channels&type=repositories",
    "https://github.com/search?q=telegram+forex+signals&type=repositories",
    "https://github.com/search?q=telegram+news+channels&type=repositories",
    # Raw GitHub lists
    "https://raw.githubusercontent.com/telegramchannels/telegramchannels/master/README.md",
    "https://raw.githubusercontent.com/epicmaxco/awesome-telegram/master/README.md",
]


async def extract_usernames(html: str) -> set:
    found = set(TGLINK_RE.findall(html))
    return {u.lower() for u in found if u.lower() not in SKIP and len(u) >= 5}


async def scrape_url(page, url: str) -> set:
    try:
        await page.goto(url, timeout=25000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        for _ in range(4):
            await page.keyboard.press("End")
            await page.wait_for_timeout(500)
        html = await page.content()
        return await extract_usernames(html)
    except Exception:
        return set()


async def scrape_all_internet(status_callback=None) -> set:
    all_usernames = set()
    save_path = "data/all_channels.txt"

    if os.path.exists(save_path):
        with open(save_path) as f:
            all_usernames = set(line.strip() for line in f if line.strip())
        print(f"Resuming with {len(all_usernames):,} channels")

    async def save_and_report(name, new_count):
        with open(save_path, "w") as f:
            f.write("\n".join(sorted(all_usernames)))
        msg = f"✅ {name}: +{new_count} new | Total: {len(all_usernames):,}"
        print(msg)
        if status_callback:
            await status_callback(msg)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-dev-shm-usage","--disable-gpu"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="en-US"
        )
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        # 1 — All directory websites
        for source in DIRECTORY_SOURCES:
            source_new = 0
            for cat in ALL_CATEGORIES:
                for pg in range(1, source["pages"] + 1):
                    found = await scrape_url(page, source["url"](cat, pg))
                    new = found - all_usernames
                    all_usernames.update(found)
                    source_new += len(new)
                    if len(new) == 0 and pg > 3:
                        break
                    await asyncio.sleep(1)
            await save_and_report(source["name"], source_new)

        # 2 — Search engines with ALL keywords
        for engine in SEARCH_ENGINES:
            engine_new = 0
            for kw in SEARCH_KEYWORDS:
                for pg in range(1, engine["pages"] + 1):
                    found = await scrape_url(page, engine["url"](kw, pg))
                    new = found - all_usernames
                    all_usernames.update(found)
                    engine_new += len(new)
                    await asyncio.sleep(2)
            await save_and_report(engine["name"], engine_new)

        # 3 — Reddit, GitHub and social
        social_new = 0
        for url in SOCIAL_URLS:
            found = await scrape_url(page, url)
            new = found - all_usernames
            all_usernames.update(found)
            social_new += len(new)
            await asyncio.sleep(2)
        await save_and_report("Reddit + GitHub", social_new)

        await browser.close()

    print(f"\n🌍 TOTAL: {len(all_usernames):,} unique channels/groups from entire internet!")
    return all_usernames
