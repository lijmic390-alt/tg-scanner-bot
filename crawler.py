"""
Telegram Inside Crawler
Crawls from inside Telegram — no websites needed.
Discovers thousands of channels by going channel to channel.
"""

import asyncio
import re
import os
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, MessageEntityUrl, MessageEntityTextUrl
from telethon.errors import (
    ChannelPrivateError, UsernameNotOccupiedError,
    FloodWaitError, UsernameInvalidError, ChatAdminRequiredError
)
from config import SEED_CHANNELS, CRAWL_DEPTH, MAX_MEMBERS

TGLINK_RE = re.compile(r't\.me/([A-Za-z0-9_]{5,32})')
SKIP = {
    'joinchat','share','proxy','addstickers','addemoji',
    'iv','bg','addtheme','botstart','s','r'
}


async def extract_from_messages(client, username: str) -> set:
    """Extract channel usernames from messages inside a channel."""
    found = set()
    try:
        async for msg in client.iter_messages(username, limit=200):
            # From message text
            if msg.text:
                for match in TGLINK_RE.findall(msg.text):
                    if match.lower() not in SKIP and len(match) >= 5:
                        found.add(match.lower())

            # From forwarded messages
            if msg.fwd_from and hasattr(msg.fwd_from, 'from_id'):
                fwd = msg.fwd_from.from_id
                if hasattr(fwd, 'channel_id'):
                    try:
                        entity = await client.get_entity(fwd.channel_id)
                        if hasattr(entity, 'username') and entity.username:
                            found.add(entity.username.lower())
                    except Exception:
                        pass

            # From message buttons/links
            if msg.reply_markup:
                try:
                    for row in msg.reply_markup.rows:
                        for btn in row.buttons:
                            if hasattr(btn, 'url') and btn.url:
                                for match in TGLINK_RE.findall(btn.url):
                                    if match.lower() not in SKIP and len(match) >= 5:
                                        found.add(match.lower())
                except Exception:
                    pass

    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 5)
    except Exception:
        pass

    return found


async def crawl_all_channels(client, status_callback=None) -> set:
    """
    Start from seed channels.
    Crawl outward to discover thousands of channels.
    Returns set of all discovered usernames.
    """
    all_channels   = set()
    save_path      = "data/all_channels.txt"
    crawled_path   = "data/crawled.txt"

    # Resume
    if os.path.exists(save_path):
        with open(save_path) as f:
            all_channels = set(line.strip() for line in f if line.strip())

    already_crawled = set()
    if os.path.exists(crawled_path):
        with open(crawled_path) as f:
            already_crawled = set(line.strip() for line in f if line.strip())

    # Start with seeds
    to_crawl = set(SEED_CHANNELS) - already_crawled
    all_channels.update(SEED_CHANNELS)

    crawled_log = open(crawled_path, "a")

    for depth in range(CRAWL_DEPTH):
        if not to_crawl:
            break

        next_round  = set()
        batch_count = 0

        msg = f"🕸 Crawl depth {depth+1}/{CRAWL_DEPTH} — exploring {len(to_crawl):,} channels..."
        print(msg)
        if status_callback:
            await status_callback(msg)

        for username in list(to_crawl):
            if username in already_crawled:
                continue

            try:
                # Get links from messages
                found = await extract_from_messages(client, username)

                # Get linked channels from channel info
                try:
                    entity = await client.get_entity(username)
                    if hasattr(entity, 'username') and entity.username:
                        all_channels.add(entity.username.lower())

                    # Also get members to find their channels
                    async for member in client.iter_participants(entity, limit=MAX_MEMBERS):
                        try:
                            if member.username and len(member.username) >= 5:
                                all_channels.add(member.username.lower())
                        except Exception:
                            pass
                        await asyncio.sleep(0.1)

                except (ChannelPrivateError, ChatAdminRequiredError):
                    pass
                except Exception:
                    pass

                # Add newly discovered channels
                new = found - all_channels - already_crawled
                all_channels.update(found)
                next_round.update(new)
                batch_count += len(new)

                already_crawled.add(username)
                crawled_log.write(username + "\n")

                # Save every 10 channels
                if len(already_crawled) % 10 == 0:
                    with open(save_path, "w") as f:
                        f.write("\n".join(sorted(all_channels)))
                    crawled_log.flush()

            except FloodWaitError as e:
                msg = f"⏳ Rate limit — waiting {e.seconds}s..."
                print(msg)
                if status_callback:
                    await status_callback(msg)
                await asyncio.sleep(e.seconds + 5)
            except Exception:
                pass

            await asyncio.sleep(1.5)

        # Save after each depth
        with open(save_path, "w") as f:
            f.write("\n".join(sorted(all_channels)))

        msg = f"✅ Depth {depth+1} done — found {batch_count:,} new channels | Total: {len(all_channels):,}"
        print(msg)
        if status_callback:
            await status_callback(msg)

        to_crawl = next_round

    crawled_log.close()

    # Reset crawled for next run
    if os.path.exists(crawled_path):
        os.remove(crawled_path)

    print(f"\n🎉 Crawling done! Found {len(all_channels):,} total channels!")
    return all_channels
