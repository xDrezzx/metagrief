"""Модуль выдачи ролей по кнопкам (Reaction / Button Roles)."""
import discord
from discord import app_commands
from discord.ext import commands


class RoleButtonView(discord.ui.View):
    def __init__(self, role_id: int, label: str, emoji: str):
        super().__init__(timeout=None)
        # Уникальный custom_id для персистентности
        self.add_item(RoleButton(role_id, label, emoji))


class RoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str, emoji: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label,
            emoji=emoji,
            custom_id=f"role_btn:{role_id}"
        )
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        role = guild.get_role(self.role_id)
        if not role:
            return await interaction.response.send_message("⚠️ Роль не найдена на сервере.", ephemeral=True)

        user = interaction.user
        if role in user.roles:
            await user.remove_roles(role, reason="Снятие роли через кнопку")
            await interaction.response.send_message(f"❌ Роль {role.name} успешно снята.", ephemeral=True)
        else:
            await user.add_roles(role, reason="Выдача роли через кнопку")
            await interaction.response.send_message(f"✅ Вам добавлена роль {role.name}!", ephemeral=True)


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="role_panel", description="Создать панель выдачи роли по кнопке")
    @app_commands.describe(channel="Куда отправить", role="Какую роль выдавать", label="Текст на кнопке",
                           emoji="Эмодзи на кнопке")
    @app_commands.default_permissions(administrator=True)
    async def role_panel(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role,
                         label: str, emoji: str = "📌"):
        emb = discord.Embed(
            title=f"📌 Получение роли: {role.name}",
            description=f"Нажми на кнопку ниже, чтобы получить или снять роль **{role.name}**.",
            color=discord.Color.blurple()
        )

        view = RoleButtonView(role.id, label, emoji)
        msg = await channel.send(embed=emb, view=view)

        # Регистрируем вьюху в боте, чтобы она работала после перезапуска
        self.bot.add_view(view)

        await interaction.response.send_message(f"✅ Панель ролей опубликована: {msg.jump_url}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))