"""
Account & Channel Scanner
Scans channels, groups, members, admins and owners.
Detects inactive accounts and deleted/banned users.
"""

import asyncio
import os
import csv
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.types import (
    UserStatusOffline, UserStatusOnline,
    UserStatusRecently, UserStatusLastWeek,
    UserStatusLastMonth, UserStatusEmpty,
    ChannelParticipantAdmin, ChannelParticipantCreator
)
from telethon.errors import (
    ChannelPrivateError, UsernameNotOccupiedError,
    FloodWaitError, UsernameInvalidError,
    ChatAdminRequiredError, UserNotParticipantError
)
from config import INACTIVE_90, INACTIVE_180, INACTIVE_365, MAX_MEMBERS_PER_GROUP


def get_last_seen_status(user) -> tuple:
    """
    Returns (status_label, is_inactive)
    """
    if user.deleted:
        return "deleted account", True
    if user.bot:
        return "bot account", False

    status = user.status
    if status is None or isinstance(status, UserStatusEmpty):
        return "last seen: never / unknown", True
    elif isinstance(status, UserStatusOnline):
        return "online right now", False
    elif isinstance(status, UserStatusRecently):
        return "last seen: recently (within 3 days)", False
    elif isinstance(status, UserStatusLastWeek):
        return "last seen: within a week", False
    elif isinstance(status, UserStatusLastMonth):
        return "last seen: within a month", False
    elif isinstance(status, UserStatusOffline):
        last = status.was_online
        age  = datetime.now(timezone.utc) - last
        label = f"last seen: {last.strftime('%Y-%m-%d')} ({age.days} days ago)"
        return label, age.days >= 30
    else:
        return "last seen: a long time ago", True


def get_channel_inactive_label(days: int) -> str:
    if days >= INACTIVE_365:
        return "🔴 1+ YEAR inactive"
    elif days >= INACTIVE_180:
        return "🟠 6+ MONTHS inactive"
    elif days >= INACTIVE_90:
        return "🟡 3+ MONTHS inactive"
    return "active"


def format_account_report(user, role: str, channel_username: str, last_seen: str) -> str:
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "No name"
    username = f"@{user.username}" if user.username else f"ID:{user.id}"
    deleted  = "YES - ACCOUNT DELETED" if user.deleted else "No"

    return (
        f"{'='*35}\n"
        f"👤 INACTIVE ACCOUNT\n"
        f"Name:      {name}\n"
        f"Username:  {username}\n"
        f"Role:      {role}\n"
        f"Channel:   @{channel_username}\n"
        f"Last seen: {last_seen}\n"
        f"Deleted:   {deleted}\n"
        f"{'='*35}"
    )


def format_channel_report(result: dict) -> str:
    return (
        f"{'='*35}\n"
        f"📢 INACTIVE CHANNEL\n"
        f"Username:  @{result['username']}\n"
        f"Title:     {result.get('title','?')}\n"
        f"Members:   {result.get('members','?')}\n"
        f"Last post: {result.get('last_post','never')}\n"
        f"Days ago:  {result.get('days_ago','?')} days\n"
        f"Status:    {result.get('level','inactive')}\n"
        f"Link:      t.me/{result['username']}\n"
        f"{'='*35}"
    )


async def scan_channel_info(client, username: str) -> dict:
    """Check a channel's last post date."""
    username = username.strip().lstrip("@")
    result = {
        "username": username, "title": None, "members": None,
        "last_post": None, "days_ago": None,
        "status": "unknown", "level": None,
        "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    }
    try:
        entity = await client.get_entity(username)
        result["title"]   = getattr(entity, "title", username)
        result["members"] = getattr(entity, "participants_count", None)

        msgs = await client.get_messages(username, limit=1)
        if not msgs:
            result["status"] = "empty"
        else:
            age = datetime.now(timezone.utc) - msgs[0].date
            result["last_post"] = msgs[0].date.strftime("%Y-%m-%d")
            result["days_ago"]  = age.days
            label = get_channel_inactive_label(age.days)
            if label == "active":
                result["status"] = "active"
            else:
                result["status"] = "inactive"
                result["level"]  = label

    except ChannelPrivateError:
        result["status"] = "private"
    except (UsernameNotOccupiedError, UsernameInvalidError):
        result["status"] = "not_found"
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 5)
        return await scan_channel_info(client, username)
    except Exception as e:
        result["status"] = f"error"

    return result


async def scan_members(client, username: str, on_inactive_account=None) -> list:
    """
    Scan members, admins and owners of a channel/group.
    Reports inactive accounts, deleted accounts, not found.
    """
    username = username.strip().lstrip("@")
    inactive_accounts = []

    try:
        entity = await client.get_entity(username)

        # Get admins and owner first (most important)
        try:
            admins = await client.get_participants(entity, filter=None, limit=0)
            async for participant in client.iter_participants(entity, limit=MAX_MEMBERS_PER_GROUP):
                try:
                    user = participant

                    # Determine role
                    role = "Member"
                    if hasattr(participant, "participant"):
                        p = participant.participant
                        if isinstance(p, ChannelParticipantCreator):
                            role = "👑 OWNER"
                        elif isinstance(p, ChannelParticipantAdmin):
                            role = "⭐ ADMIN"

                    # Check if deleted
                    if user.deleted:
                        account = {
                            "username": user.username or f"ID:{user.id}",
                            "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
                            "role": role,
                            "channel": username,
                            "last_seen": "DELETED ACCOUNT",
                            "status": "deleted",
                            "user_id": user.id
                        }
                        inactive_accounts.append(account)
                        if on_inactive_account:
                            await on_inactive_account(account)
                        continue

                    # Check last seen
                    last_seen_label, is_inactive = get_last_seen_status(user)

                    if is_inactive:
                        account = {
                            "username": user.username or f"ID:{user.id}",
                            "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
                            "role": role,
                            "channel": username,
                            "last_seen": last_seen_label,
                            "status": "inactive",
                            "user_id": user.id
                        }
                        inactive_accounts.append(account)
                        if on_inactive_account:
                            await on_inactive_account(account)

                    await asyncio.sleep(0.3)

                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds + 5)
                except Exception:
                    pass

        except (ChatAdminRequiredError, UserNotParticipantError):
            pass  # Can't read members — private group

    except ChannelPrivateError:
        pass
    except (UsernameNotOccupiedError, UsernameInvalidError):
        pass
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 5)
        return await scan_members(client, username, on_inactive_account)
    except Exception:
        pass

    return inactive_accounts


async def scan_all(client, channels: list, on_inactive_channel=None,
                   on_inactive_account=None, on_progress=None) -> dict:
    """
    Full scan:
    1. Check each channel for inactivity
    2. Scan members/admins of each channel for inactive accounts
    """
    scanned_file  = "data/scanned.txt"
    results_file  = "data/channel_results.csv"
    accounts_file = "data/account_results.csv"

    already_scanned = set()
    if os.path.exists(scanned_file):
        with open(scanned_file) as f:
            already_scanned = set(line.strip() for line in f if line.strip())

    todo = [c.lstrip("@") for c in channels if c.lstrip("@") not in already_scanned]
    total = len(todo)
    print(f"🔍 {total} channels to scan")

    # CSV setup
    ch_exists  = os.path.exists(results_file)
    acc_exists = os.path.exists(accounts_file)

    ch_file  = open(results_file,  "a", newline="", encoding="utf-8")
    acc_file = open(accounts_file, "a", newline="", encoding="utf-8")

    ch_writer = csv.DictWriter(ch_file, fieldnames=[
        "username","title","members","last_post","days_ago","status","level","scanned_at"
    ])
    acc_writer = csv.DictWriter(acc_file, fieldnames=[
        "username","name","role","channel","last_seen","status","user_id"
    ])

    if not ch_exists:
        ch_writer.writeheader()
    if not acc_exists:
        acc_writer.writeheader()

    log_f = open(scanned_file, "a")

    counts = {"channels": 0, "inactive_channels": 0, "inactive_accounts": 0}

    async def handle_inactive_account(account):
        acc_writer.writerow(account)
        counts["inactive_accounts"] += 1
        if on_inactive_account:
            await on_inactive_account(account)

    for i, username in enumerate(todo):
        # 1 — Check channel inactivity
        ch_result = await scan_channel_info(client, username)
        ch_writer.writerow(ch_result)
        log_f.write(username + "\n")
        counts["channels"] += 1

        if ch_result["status"] == "inactive":
            counts["inactive_channels"] += 1
            if on_inactive_channel:
                await on_inactive_channel(ch_result)

        # 2 — Scan members and admins
        await scan_members(client, username, on_inactive_account=handle_inactive_account)

        # Progress every 50
        if (i + 1) % 50 == 0:
            ch_file.flush()
            acc_file.flush()
            log_f.flush()
            if on_progress:
                await on_progress(i + 1, total, counts)

        await asyncio.sleep(1)

    ch_file.close()
    acc_file.close()
    log_f.close()

    return counts
