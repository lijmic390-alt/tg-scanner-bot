# ============================================================
# CONFIG — Fill these in before deploying
# ============================================================

# Your Telegram API (from https://my.telegram.org)
API_ID   = 37881574
API_HASH = "8089162cfb211f374a1112ec910d1b2c"

# Your Telegram Bot token (from @BotFather on Telegram)
BOT_TOKEN = "8766389548:AAFEx0i8jh0rHolh7-ZGwLZLHVUgD2_m6uU"

# Your Telegram user ID (the bot sends results to YOU)
# Get it by messaging @userinfobot on Telegram
MY_CHAT_ID = 7147866789

# Inactivity levels (days)
INACTIVE_90  = 90    # 3 months
INACTIVE_180 = 180   # 6 months
INACTIVE_365 = 365   # 1 year

# Scan time every day (24h format)
SCAN_HOUR   = 9   # 9 AM
SCAN_MINUTE = 0

# Priority categories (scanned first and deeper)
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
