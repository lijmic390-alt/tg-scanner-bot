"""
Telegram Channel Activity Scanner
Checks each channel and categorizes by inactivity level.
"""

import asyncio
import os
import csv
from datetime import datetime, timezone
from telethon.errors import (
    ChannelPrivateError, UsernameNotOccupiedError,
    FloodWaitError, UsernameInvalidError
)
from config import INACTIVE_90, INACTIVE_180, INACTIVE_365


def get_inactivity_label(days: int) -> str:
    if days >= INACTIVE_365:
        return "🔴 1+ YEAR inactive"
    elif days >= INACTIVE_180:
        return "🟠 6+ MONTHS inactive"
    elif days >= INACTIVE_90:
        return "🟡 3+ MONTHS inactive"
    return "active"


async def scan_channel(client, username: str) -> dict:
    """Check a single channel. Returns result dict."""
    username = username.strip().lstrip("@")
    result = {
        "username": username,
        "title": None,
        "members": None,
        "last_post": None,
        "days_ago": None,
        "status": "unknown",
        "level": None,
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
            label = get_inactivity_label(age.days)
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
        return await scan_channel(client, username)
    except Exception:
        result["status"] = "error"

    return result


async def scan_all(client, channels: list, on_inactive=None, on_progress=None) -> list:
    """
    Scan all channels. 
    Calls on_inactive(result) whenever an inactive channel is found.
    Calls on_progress(scanned, total, inactive_count) every 50 channels.
    """
    # Resume support
    scanned_file = "data/scanned.txt"
    results_file = "data/results.csv"

    already_scanned = set()
    if os.path.exists(scanned_file):
        with open(scanned_file) as f:
            already_scanned = set(line.strip() for line in f if line.strip())

    todo = [c.lstrip("@") for c in channels if c.lstrip("@") not in already_scanned]
    total = len(todo)
    print(f"🔍 {total} channels to scan ({len(already_scanned)} already done)")

    csv_exists = os.path.exists(results_file)
    csv_f  = open(results_file, "a", newline="", encoding="utf-8")
    fields = ["username","title","members","last_post","days_ago","status","level","scanned_at"]
    writer = csv.DictWriter(csv_f, fieldnames=fields)
    if not csv_exists:
        writer.writeheader()

    log_f = open(scanned_file, "a")

    inactive_count = 0
    inactive_batch = []

    for i, username in enumerate(todo):
        result = await scan_channel(client, username)
        writer.writerow(result)
        log_f.write(username + "\n")

        if result["status"] == "inactive":
            inactive_count += 1
            inactive_batch.append(result)
            if on_inactive:
                await on_inactive(inactive_batch)
                inactive_batch = []

        if (i + 1) % 50 == 0:
            csv_f.flush()
            log_f.flush()
            if on_progress:
                await on_progress(i + 1, total, inactive_count)

        await asyncio.sleep(1)

    # Send any remaining
    if inactive_batch and on_inactive:
        await on_inactive(inactive_batch)

    csv_f.close()
    log_f.close()

    return inactive_count
