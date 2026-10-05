import asyncio
import logging

import discord
from discord.ext import commands

import config
from database import Database
from gemini_ai import GeminiReviewer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("metaassistant")

# Список всех активных модулей (когов) ботов
EXTENSIONS = [
    "cogs.admin",
    "cogs.forums",
    "cogs.announce",
    "cogs.activity",
    "cogs.applications",
    "cogs.verify",          # Модуль верификации по кнопке
    "cogs.economy",         # Уровни, опыт, монеты и профиль
    "cogs.moderation",      # Автомодерация ссылок и логирование
    "cogs.reaction_roles",  # Выдача ролей по кнопкам
]


class MetaAssistant(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Чтение текста сообщений (обязательно в Developer Portal!)
        intents.members = True          # Информация об участниках сервера (обязательно в Developer Portal!)
        intents.guilds = True           # События сервера

        super().__init__(command_prefix="!", intents=intents)
        self.db = Database(config.DB_PATH)
        self.gemini = GeminiReviewer()

    async def setup_hook(self):
        # Инициализируем расширенную базу данных
        await self.db.init()

        # Загружаем коги
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                log.info("Загружено расширение: %s", ext)
            except Exception as e:
                log.error("Не удалось загрузить расширение %s: %s", ext, e)

        # Синхронизация слеш-команд
        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Команды синхронизированы для гильдии %s", config.GUILD_ID)
        else:
            # Принудительно очищаем и синхронизируем глобально, если гильдия не задана
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            log.info("Команды синхронизированы глобально")

    async def on_ready(self):
        log.info("Запущен как %s (%s)", self.user, self.user.id)
        await self.change_presence(activity=discord.Game("MetaGrief"))

    async def close(self):
        await self.db.close()
        await super().close()


async def main():
    if not config.DISCORD_TOKEN or not config.GEMINI_API_KEY:
        raise SystemExit("Заполни DISCORD_TOKEN и GEMINI_API_KEY в файле .env")
    async with MetaAssistant() as bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())