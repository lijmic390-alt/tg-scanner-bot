"""
Scanner — checks every channel, group, user for inactivity.
"""

import asyncio
import os
import csv
from datetime import datetime, timezone
from telethon.tl.types import (
    UserStatusOffline, UserStatusOnline, UserStatusRecently,
    UserStatusLastWeek, UserStatusLastMonth, UserStatusEmpty,
    ChannelParticipantAdmin, ChannelParticipantCreator,
    Channel, Chat, User
)
from telethon.errors import (
    ChannelPrivateError, UsernameNotOccupiedError,
    FloodWaitError, UsernameInvalidError, ChatAdminRequiredError
)
from config import INACTIVE_30, INACTIVE_90, INACTIVE_180, INACTIVE_365, MAX_MEMBERS


def get_last_seen(user) -> tuple:
    if user.deleted:
        return "DELETED ACCOUNT", True
    if user.bot:
        return "Bot", False
    status = user.status
    if status is None or isinstance(status, UserStatusEmpty):
        return "Last seen: never / unknown", True
    elif isinstance(status, UserStatusOnline):
        return "Online now", False
    elif isinstance(status, UserStatusRecently):
        return "Last seen: within 3 days", False
    elif isinstance(status, UserStatusLastWeek):
        return "Last seen: within a week", False
    elif isinstance(status, UserStatusLastMonth):
        return "Last seen: within a month", True
    elif isinstance(status, UserStatusOffline):
        last = status.was_online
        age  = datetime.now(timezone.utc) - last
        return f"Last seen: {last.strftime('%Y-%m-%d')} ({age.days} days ago)", age.days >= INACTIVE_30
    else:
        return "Last seen: a long time ago (1+ month)", True


def inactivity_label(days: int) -> str:
    if days >= INACTIVE_365:
        return "🔴 DEAD — 1+ YEAR no posts"
    elif days >= INACTIVE_180:
        return "🟠 VERY INACTIVE — 6+ MONTHS"
    elif days >= INACTIVE_90:
        return "🟡 INACTIVE — 3+ MONTHS"
    elif days >= INACTIVE_30:
        return "🔵 SLOW — 1+ MONTH"
    return "active"


def format_channel_report(result: dict) -> str:
    icon = "📢" if result.get("type") == "channel" else "👥"
    kind = "CHANNEL" if result.get("type") == "channel" else "GROUP"
    members = f"{result['members']:,}" if result.get("members") else "?"
    return (
        f"{icon} INACTIVE {kind}\n"
        f"{'='*30}\n"
        f"Username:  @{result['username']}\n"
        f"Title:     {result.get('title','?')}\n"
        f"Members:   {members}\n"
        f"Last post: {result.get('last_post','never')}\n"
        f"Days ago:  {result.get('days_ago','?')} days\n"
        f"Status:    {result.get('level','?')}\n"
        f"Link:      t.me/{result['username']}"
    )


def format_user_report(result: dict) -> str:
    status = result.get("status","?")
    icon = "❌" if status == "deleted" else "💤" if status == "inactive" else "🚫"
    label = "DELETED ACCOUNT" if status == "deleted" else "INACTIVE USER" if status == "inactive" else "NOT AVAILABLE"
    return (
        f"{icon} {label}\n"
        f"{'='*30}\n"
        f"Name:      {result.get('name','?')}\n"
        f"Username:  @{result['username']}\n"
        f"Last seen: {result.get('last_seen','?')}\n"
        f"Found in:  @{result.get('found_in','?')}\n"
        f"Profile:   t.me/{result['username']}"
    )


def format_unavailable_report(username: str) -> str:
    return (
        f"🚫 USERNAME NOT AVAILABLE\n"
        f"{'='*30}\n"
        f"Username:  @{username}\n"
        f"Status:    Deleted / Never existed\n"
        f"Was at:    t.me/{username}"
    )


async def check_channel(client, username: str) -> dict:
    username = username.strip().lstrip("@")
    result = {
        "username": username, "type": "unknown",
        "title": None, "name": None, "members": None,
        "last_post": None, "days_ago": None, "last_seen": None,
        "status": "unknown", "level": None, "found_in": None,
        "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    }
    try:
        entity = await client.get_entity(username)

        if isinstance(entity, (Channel, Chat)):
            result["type"]    = "group" if getattr(entity, "megagroup", False) or isinstance(entity, Chat) else "channel"
            result["title"]   = getattr(entity, "title", username)
            result["members"] = getattr(entity, "participants_count", None)
            msgs = await client.get_messages(username, limit=1)
            if not msgs:
                result["status"] = "empty"
                result["level"]  = "⬜ EMPTY — no messages ever"
            else:
                age = datetime.now(timezone.utc) - msgs[0].date
                result["last_post"] = msgs[0].date.strftime("%Y-%m-%d")
                result["days_ago"]  = age.days
                label = inactivity_label(age.days)
                result["status"] = "inactive" if label != "active" else "active"
                result["level"]  = label

        elif isinstance(entity, User):
            result["type"] = "user"
            result["name"] = f"{entity.first_name or ''} {entity.last_name or ''}".strip()
            last_seen, is_inactive = get_last_seen(entity)
            result["last_seen"] = last_seen
            result["status"]    = "deleted" if entity.deleted else ("inactive" if is_inactive else "active")
            result["level"]     = "❌ DELETED" if entity.deleted else ("💤 INACTIVE" if is_inactive else None)

    except (UsernameNotOccupiedError, UsernameInvalidError):
        result["status"] = "not_available"
        result["level"]  = "🚫 NOT AVAILABLE"
    except ChannelPrivateError:
        result["status"] = "private"
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 5)
        return await check_channel(client, username)
    except Exception:
        result["status"] = "error"

    return result


async def scan_members(client, username: str, on_result=None):
    """Scan all members of a channel/group."""
    try:
        entity = await client.get_entity(username)
        async for user in client.iter_participants(entity, limit=MAX_MEMBERS):
            try:
                if user.bot:
                    continue
                last_seen, is_inactive = get_last_seen(user)
                uname = user.username or f"id{user.id}"
                if user.deleted or is_inactive:
                    result = {
                        "username": uname,
                        "type": "user",
                        "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
                        "members": None, "last_post": None, "days_ago": None,
                        "last_seen": last_seen,
                        "status": "deleted" if user.deleted else "inactive",
                        "level": "❌ DELETED" if user.deleted else "💤 INACTIVE",
                        "found_in": username,
                        "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                    }
                    if on_result:
                        await on_result(result)
                await asyncio.sleep(0.2)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 3)
            except Exception:
                pass
    except (ChatAdminRequiredError, ChannelPrivateError):
        pass
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 5)
    except Exception:
        pass


async def scan_all(client, channels: list, on_result=None, on_progress=None) -> dict:
    scanned_file = "data/scanned.txt"
    results_file = "data/results.csv"

    already_scanned = set()
    if os.path.exists(scanned_file):
        with open(scanned_file) as f:
            already_scanned = set(line.strip() for line in f if line.strip())

    todo  = [c.lstrip("@") for c in channels if c.lstrip("@") not in already_scanned]
    total = len(todo)
    print(f"Scanning {total:,} channels/users...")

    csv_exists = os.path.exists(results_file)
    csv_f  = open(results_file, "a", newline="", encoding="utf-8")
    fields = ["username","type","title","name","members","last_post",
              "days_ago","last_seen","status","level","found_in","scanned_at"]
    writer = csv.DictWriter(csv_f, fieldnames=fields, extrasaction="ignore")
    if not csv_exists:
        writer.writeheader()

    log_f  = open(scanned_file, "a")
    counts = {
        "total": 0, "inactive_channels": 0, "inactive_groups": 0,
        "inactive_users": 0, "deleted": 0, "not_available": 0
    }

    for i, username in enumerate(todo):
        result = await check_channel(client, username)
        writer.writerow(result)
        log_f.write(username + "\n")
        counts["total"] += 1

        status = result.get("status")
        typ    = result.get("type")

        if status in ("inactive","empty","deleted","not_available"):
            if typ == "channel":
                counts["inactive_channels"] += 1
            elif typ == "group":
                counts["inactive_groups"] += 1
            elif typ == "user" and status == "deleted":
                counts["deleted"] += 1
            elif typ == "user":
                counts["inactive_users"] += 1
            elif status == "not_available":
                counts["not_available"] += 1
            if on_result:
                await on_result(result)

        # Scan members too
        if typ in ("channel","group") and status not in ("private","not_available","error"):
            await scan_members(client, username, on_result=on_result)

        if (i + 1) % 50 == 0:
            csv_f.flush()
            log_f.flush()
            if on_progress:
                await on_progress(i + 1, total, counts)

        await asyncio.sleep(1)

    csv_f.close()
    log_f.close()
    return counts
