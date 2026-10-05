"""Слеш-команды настройки: пинги, каналы форумов, роль ютубера, кулдауны."""
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config

FORUM_CHOICES = [app_commands.Choice(name=label, value=key) for key, label in config.FORUMS.items()]

admin_only = [
    app_commands.default_permissions(administrator=True),
    app_commands.checks.has_permissions(administrator=True),
    app_commands.guild_only()
]


def apply(decorators):
    def wrap(func):
        for d in reversed(decorators):
            func = d(func)
        return func
    return wrap


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "⛔ Эта команда только для администраторов."
        else:
            msg = f"⚠️ Ошибка: {error}"

        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="set_ping", description="Кого пинговать на форуме (до 3 людей + роль)")
    @app_commands.describe(
        forum="Выберите форум",
        user1="Ответственный 1",
        user2="Ответственный 2",
        user3="Ответственный 3",
        role="Роль (необязательно)"
    )
    @app_commands.choices(forum=FORUM_CHOICES)
    @apply(admin_only)
    async def set_ping(
        self, interaction: discord.Interaction,
        forum: app_commands.Choice[str],
        user1: Optional[discord.Member] = None,
        user2: Optional[discord.Member] = None,
        user3: Optional[discord.Member] = None,
        role: Optional[discord.Role] = None
    ):
        users = [u.id for u in (user1, user2, user3) if u]
        roles = [role.id] if role else []

        if not users and not roles:
            return await interaction.response.send_message(
                "Укажите хотя бы одного человека или роль. Чтобы убрать пинги — используйте /clear_ping.",
                ephemeral=True
            )

        await self.bot.db.set_ping(forum.value, list(dict.fromkeys(users)), roles)
        pretty = " ".join([f"<@{i}>" for i in users] + [f"<@&{i}>" for i in roles])

        await interaction.response.send_message(
            f"✅ Ответственные для **{forum.name}**: {pretty}",
            allowed_mentions=discord.AllowedMentions.none()
        )

    @app_commands.command(name="clear_ping", description="Убрать пинги для конкретного форума")
    @app_commands.choices(forum=FORUM_CHOICES)
    @apply(admin_only)
    async def clear_ping(self, interaction: discord.Interaction, forum: app_commands.Choice[str]):
        await self.bot.db.set_ping(forum.value, [], [])
        await interaction.response.send_message(f"🗑 Пинги для **{forum.name}** успешно очищены.", ephemeral=True)

    @app_commands.command(name="set_forum", description="Привязать канал-форум к определенной категории заявок")
    @app_commands.describe(forum_type="Категория форума", channel="Выберите канал-форум на сервере")
    @app_commands.choices(forum_type=FORUM_CHOICES)
    @apply(admin_only)
    async def set_forum(
        self, interaction: discord.Interaction,
        forum_type: app_commands.Choice[str],
        channel: discord.abc.GuildChannel
    ):
        # Проверяем вручную, является ли выбранный канал форумом
        if not isinstance(channel, discord.ForumChannel):
            return await interaction.response.send_message(
                "⚠️ Ошибка: выбранный канал должен быть именно каналом типа **«Форум»**!",
                ephemeral=True
            )

        key = f"forum:{forum_type.value}"
        await self.bot.db.set_setting(key, str(channel.id))
        await interaction.response.send_message(
            f"✅ Форум для категории **{forum_type.name}** успешно привязан к {channel.mention}!",
            ephemeral=True
        )

    @app_commands.command(name="set_announce", description="Установить текстовый канал для автоматических анонсов видео")
    @app_commands.describe(channel="Выберите обычный текстовый канал")
    @apply(admin_only)
    async def set_announce(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel):
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "⚠️ Ошибка: выбранный канал должен быть обычным **текстовым** каналом!",
                ephemeral=True
            )

        await self.bot.db.set_setting("announce_channel", str(channel.id))
        await interaction.response.send_message(
            f"✅ Канал для анонсов видео установлен: {channel.mention}!",
            ephemeral=True
        )

    @app_commands.command(name="set_youtuber_role", description="Роль, которой разрешено публиковать видео в канале анонсов")
    @app_commands.describe(role="Роль (оставьте пустым, чтобы разрешить публикацию всем)")
    @apply(admin_only)
    async def set_youtuber_role(self, interaction: discord.Interaction, role: Optional[discord.Role] = None):
        if role:
            await self.bot.db.set_setting("youtuber_role", str(role.id))
            text = f"✅ Анонсы теперь разрешены только роли {role.mention}"
        else:
            await self.bot.db.delete_setting("youtuber_role")
            text = "✅ Ограничение по роли снято. Публиковать могут все."

        await interaction.response.send_message(text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="reset_cooldown", description="Сбросить кулдаун подачи заявки на Ютубера для участника")
    @apply(admin_only)
    async def reset_cooldown(self, interaction: discord.Interaction, member: discord.Member):
        await self.bot.db.reset_cooldown("media", member.id)
        await interaction.response.send_message(
            f"✅ Кулдаун для участника {member.mention} сброшен.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none()
        )

    @app_commands.command(name="config", description="Показать текущие настройки привязок каналов и пингов бота")
    @apply(admin_only)
    async def show_config(self, interaction: discord.Interaction):
        db = self.bot.db
        emb = discord.Embed(title="⚙️ Конфигурация MetaAssistant", color=discord.Color.blurple())

        for key, label in config.FORUMS.items():
            ch = await db.get_setting(f"forum:{key}")
            ping = await db.get_ping(key)
            who = " ".join([f"<@{i}>" for i in ping["users"]] + [f"<@&{i}>" for i in ping["roles"]]) or "—"
            emb.add_field(
                name=label,
                value=f"Канал: {f'<#{ch}>' if ch else '❌ не задан'}\nПинги: {who}",
                inline=False
            )

        ann = await db.get_setting("announce_channel")
        role = await db.get_setting("youtuber_role")
        emb.add_field(
            name="Анонсы видео",
            value=f"Канал: {f'<#{ann}>' if ann else '❌ не задан'}\nРоль: {f'<@&{role}>' if role else 'все участники'}",
            inline=False
        )

        await interaction.response.send_message(embed=emb, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


async def setup(bot):
    await bot.add_cog(Admin(bot))