"""
Joiner — searches Telegram and joins channels and groups automatically.
"""

import asyncio
import os
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import Channel, Chat
from telethon.errors import (
    FloodWaitError, UserAlreadyParticipantError,
    ChannelPrivateError, InviteHashExpiredError
)
from config import SEARCH_KEYWORDS, JOIN_PER_DAY


async def search_and_join(client, status_callback=None) -> list:
    """Search Telegram for crypto channels and groups and join them."""

    joined_file = "data/joined.txt"
    already_joined = set()

    if os.path.exists(joined_file):
        with open(joined_file) as f:
            already_joined = set(line.strip() for line in f if line.strip())

    joined_today = 0
    all_joined   = list(already_joined)
    log_f        = open(joined_file, "a")

    for keyword in SEARCH_KEYWORDS:
        if joined_today >= JOIN_PER_DAY:
            break

        try:
            # Search Telegram directly
            result = await client(SearchRequest(
                q=keyword,
                limit=20
            ))

            for chat in result.chats:
                if joined_today >= JOIN_PER_DAY:
                    break

                try:
                    username = getattr(chat, "username", None)
                    if not username:
                        continue
                    if username.lower() in already_joined:
                        continue

                    # Join the channel or group
                    await client(JoinChannelRequest(chat))
                    already_joined.add(username.lower())
                    all_joined.append(username.lower())
                    log_f.write(username.lower() + "\n")
                    joined_today += 1

                    msg = f"✅ Joined: @{username} ({joined_today}/{JOIN_PER_DAY})"
                    print(msg)
                    if status_callback:
                        await status_callback(msg)

                    await asyncio.sleep(3)

                except UserAlreadyParticipantError:
                    already_joined.add(username.lower())
                    all_joined.append(username.lower())
                except (ChannelPrivateError, FloodWaitError) as e:
                    if isinstance(e, FloodWaitError):
                        await asyncio.sleep(e.seconds + 5)
                except Exception:
                    pass

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 5)
        except Exception:
            pass

        await asyncio.sleep(2)

    log_f.close()
    print(f"\n✅ Total channels/groups joined: {len(all_joined)}")
    return all_joined
