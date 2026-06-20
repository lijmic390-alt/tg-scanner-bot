# ============================================================
# CONFIG — Fill these in before deploying
# ============================================================

# Your Telegram API (from https://my.telegram.org)
API_ID   = 12345678
API_HASH = "your_api_hash"

# Your Telegram Bot token (from @BotFather)
BOT_TOKEN = "your_bot_token"

# Your Telegram user ID (from @userinfobot)
MY_CHAT_ID = 123456789

# Inactivity thresholds for CHANNELS (days)
INACTIVE_90  = 90    # 3 months
INACTIVE_180 = 180   # 6 months
INACTIVE_365 = 365   # 1 year

# Scan time every day (UTC)
SCAN_HOUR   = 9
SCAN_MINUTE = 0

# How many members to scan per group/channel
MAX_MEMBERS_PER_GROUP = 200

# Priority categories
PRIORITY_CATEGORIES = [
    "cryptocurrency", "finance", "economics",
    "technology", "software", "business", "marketing"
]

# All other categories
OTHER_CATEGORIES = [
    "news", "politics", "education", "science",
    "entertainment", "music", "movies", "sport",
    "health", "food", "travel", "fashion", "art",
    "humor", "animals", "nature", "cars", "gaming",
    "real-estate", "jobs", "legal", "psychology",
    "history", "design", "photography", "medicine",
    "fitness", "books", "quotes"
]
