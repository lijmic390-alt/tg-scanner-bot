# ============================================================
# CONFIG — Fill these in before deploying
# ============================================================

API_ID     = 37881574
API_HASH   = "8089162cfb211f374a1112ec910d1b2c"
BOT_TOKEN  = "8766389548:AAFEx0i8jh0rHolh7-ZGwLZLHVUgD2_m6uU"
MY_CHAT_ID = 7147866789

# How many channels/groups to join per day (stay safe)
JOIN_PER_DAY = 15

# Search keywords to find channels and groups
SEARCH_KEYWORDS = [
    # Crypto
    "crypto", "bitcoin", "ethereum", "binance", "trading",
    "blockchain", "defi", "nft", "altcoin", "btc", "eth",
    "forex", "investment", "finance", "stocks", "gold",
    "signals", "pump", "moon", "hodl", "wallet", "exchange",
    # More crypto
    "solana", "cardano", "dogecoin", "ripple", "litecoin",
    "web3", "mining", "staking", "airdrop", "presale",
]

# Scam patterns to detect
SCAM_PATTERNS = [
    # Money doubling
    "send and get back", "send 1 get 2", "send 0.1 get 1",
    "double your", "2x your", "3x your", "10x guaranteed",
    "send btc get", "send eth get", "send usdt get",
    # Guaranteed profit
    "guaranteed profit", "guaranteed return", "100% profit",
    "guaranteed 100", "risk free profit", "no risk",
    "guaranteed investment", "guaranteed earning",
    # Fake giveaway
    "elon musk giveaway", "binance giveaway", "bitcoin giveaway",
    "free bitcoin", "free crypto", "free eth", "free usdt",
    "claim your reward", "you have been selected", "you won",
    "limited time offer", "claim now", "free money",
    # Phishing
    "verify your wallet", "confirm your wallet", "wallet suspended",
    "account suspended", "enter seed phrase", "enter private key",
    "click to claim", "click to verify", "login to claim",
    # Fake investment
    "dm me for profit", "dm me for investment", "contact me to invest",
    "i turned 100 into", "i made 10000 from", "my trader",
    "join my vip", "vip signals", "i can help you make",
    "invest with me", "work from home", "earn from home",
    # Impersonation
    "official binance", "official bitcoin", "official elon",
    "tesla giveaway", "apple giveaway", "amazon giveaway",
    # General scam
    "send first then receive", "pay first", "deposit first",
    "registration fee", "activation fee", "processing fee",
    "your profit is ready", "withdraw your profit",
]
