"""Система уровней, монет, активности в чате и магазина ролей."""
import random
import discord
from discord import app_commands
from discord.ext import commands

from utils import reply


class ShopView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot

    @discord.ui.button(label="Купить кастомную роль (Пример)", style=discord.ButtonStyle.primary, emoji="🛒")
    async def buy_role_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🛍️ Чтобы настроить товары магазина, используй команду администратора для добавления ролей в базу.",
            ephemeral=True)


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Игнорируем ботов и личные сообщения
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id

        # 1. Засчитываем сообщение в старую таблицу активности (для статистики)
        await self.bot.db.add_message(user_id)

        # 2. Начисляем опыт и монеты за сообщение (с рандомом, чтобы не спамили ради фарма)
        xp_gain = random.randint(10, 25)
        coins_gain = random.randint(1, 5)

        result = await self.bot.db.update_user(user_id, xp_gain, coins_gain)

        # Если игрок повысил уровень — можно при желании отправить уведомление
        if result["level_up"]:
            try:
                # Опционально: отправка сообщения в тот же чат о новом уровне
                pass
            except Exception:
                pass

    @app_commands.command(name="profile", description="Посмотреть свой профиль, уровень и баланс монет")
    @app_commands.describe(member="Участник (необязательно)")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        user_data = await self.bot.db.get_user(target.id)
        activity_data = await self.bot.db.get_activity(target.id)

        xp_needed = user_data["level"] * 100

        emb = discord.Embed(
            title=f"👤 Профиль участника: {target.display_name}",
            color=discord.Color.blurple()
        )
        emb.set_thumbnail(url=target.display_avatar.url)
        emb.add_field(name="✨ Уровень", value=str(user_data["level"]), inline=True)
        emb.add_field(name="📈 Опыт (XP)", value=f"{user_data['xp']} / {xp_needed}", inline=True)
        emb.add_field(name="🪙 Монеты", value=str(user_data["coins"]), inline=True)

        emb.add_field(name="💬 Сообщений всего", value=str(activity_data["total"]), inline=True)
        emb.add_field(name="🔥 Активных дней", value=str(activity_data["active_days"]), inline=True)

        emb.set_footer(text="MetaGrief Economy")
        await interaction.response.send_message(embed=emb)

    @app_commands.command(name="shop", description="Открыть магазин ролей за монеты")
    async def shop(self, interaction: discord.Interaction):
        emb = discord.Embed(
            title="🛒 Магазин сервера MetaGrief",
            description="Трать заработанные за активность монеты на крутые привилегии и роли!\n\n*(Магазин находится в режиме наполнения)*",
            color=discord.Color.gold()
        )
        emb.set_footer(text="Зарабатывай монеты просто общаясь в текстовых каналах.")
        await interaction.response.send_message(embed=emb, view=ShopView(self.bot))


async def setup(bot):
    await bot.add_cog(Economy(bot))