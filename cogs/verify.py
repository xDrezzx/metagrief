"""Модуль верификации: кнопка для получения доступа к серверу."""
import discord
from discord import app_commands
from discord.ext import commands

from utils import reply


class VerifyView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Пройти верификацию", style=discord.ButtonStyle.success, emoji="✅",
                       custom_id="meta:verify:btn")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ID роли, которую выдаем при верификации (можно прописать сюда или вынести в настройки БД)
        role_id_str = await self.bot.db.get_setting("verify_role_id")
        if not role_id_str:
            return await interaction.response.send_message(
                "⚠️ Роль верификации еще не настроена администрацией!", ephemeral=True)

        role = interaction.guild.get_role(int(role_id_str))
        if not role:
            return await interaction.response.send_message(
                "⚠️ Настроенная роль верификации не найдена на сервере.", ephemeral=True)

        if role in interaction.user.roles:
            return await interaction.response.send_message("ℹ️ Ты уже верифицирован!", ephemeral=True)

        try:
            await interaction.user.add_roles(role, reason="Верификация через Discord-бота")
            await interaction.response.send_message("✅ Верификация успешно пройдена! Добро пожаловать на сервер.",
                                                    ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("⛔ У бота недостаточно прав для выдачи этой роли.", ephemeral=True)


class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Регистрируем persistent view, чтобы кнопка работала после перезапуска бота
        self.bot.add_view(VerifyView(self.bot))

    @app_commands.command(name="setup_verify", description="Опубликовать панель верификации в канал")
    @app_commands.describe(channel="Канал, куда отправить сообщение с кнопкой")
    @app_commands.default_permissions(administrator=True)
    async def setup_verify(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        # Сохраняем ID роли в базу
        await self.bot.db.set_setting("verify_role_id", str(role.id))

        emb = discord.Embed(
            title="🛡️ Верификация на сервере MetaGrief",
            description="Нажми на кнопку **«Пройти верификацию»** ниже, чтобы подтвердить, что ты не робот, и получить доступ к чатам.",
            color=discord.Color.green()
        )
        emb.set_footer(text="MetaAssistant Security")

        msg = await channel.send(embed=emb, view=VerifyView(self.bot))
        await interaction.response.send_message(f"✅ Панель верификации успешно опубликована: {msg.jump_url}",
                                                ephemeral=True)


async def setup(bot):
    await bot.add_cog(Verify(bot))