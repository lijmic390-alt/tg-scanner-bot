"""
Configuration for Telegram Inactive Channel Scanner
----------------------------------------------------
1. Get your API_ID and API_HASH from https://my.telegram.org
2. Add channels to scan below
3. Set your inactivity threshold
"""

# ── Telegram API credentials ──────────────────────────────────────────────────
# Get these from https://my.telegram.org → "API development tools"
API_ID   =   37881574       # Replace with your API ID (integer)
API_HASH = "8089162cfb211f374a1112ec910d1b2c"   # Replace with your API hash (string)

# Session file name (keeps you logged in between runs)
SESSION_NAME = "7147866789"

# ── Inactivity threshold ──────────────────────────────────────────────────────
# Channels with no posts for this many days will be marked inactive
INACTIVE_DAYS = 180  # e.g. 180 = 6 months, 365 = 1 year, 90 = 3 months

# ── Channels to scan manually ─────────────────────────────────────────────────
# Add usernames with or without the @ symbol
MANUAL_CHANNELS = [
    "@durov",
    "@telegram",
    # Add more here...
]

# ── Seed channels for auto-crawl ──────────────────────────────────────────────
# The scanner will read these channels and discover linked/forwarded channels
SEED_CHANNELS = [
    "@telegram",
    # Add channels likely to link to others...
]
