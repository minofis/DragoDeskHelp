import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:5001")
ALLOWED_TELEGRAM_IDS = list(map(int, os.getenv("ALLOWED_TELEGRAM_IDS", "568312173,852755803").split(",")))
