"""Статические настройки проекта. Всё, что админы меняют в Discord, хранится в БД (database.py)."""
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
GUILD_ID = int(os.getenv("GUILD_ID") or 0)
DB_PATH = os.getenv("DB_PATH", "metaassistant.db")

# --- Правила Ютуб-заявок ---
SERVER_IPS = ["mc.MetaGriefs.fun", "mc.MetaGriefs.xyz"]
SITE_URL = "https://metagriefs.fun"
PROMO_CODE = "META"
MIN_AGE = 13
MIN_VIEWS_PER_DAY_VIDEO = 70
MIN_VIEWS_PER_DAY_SHORTS = 850
MEDIA_COOLDOWN_DAYS = 2

# Ключ -> название (используется в слеш-командах и в БД)
FORUMS = {
    "media": "Подача на Ютубера",
    "helper": "Подача на Хелпера",
    "report": "Жалобы",
    "support": "Техподдержка",
}

# Названия тегов форума, которые бот поставит на тему (если такие теги созданы)
STATUS_TAGS = {
    "accepted": ["принято", "одобрено", "accepted", "решено"],
    "rejected": ["отказано", "отклонено", "rejected"],
    "manual_check": ["на рассмотрении", "ручная проверка", "manual"],
}
