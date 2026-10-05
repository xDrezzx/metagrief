"""Модуль автомодерации и логирования событий сервера."""
import discord
from discord import app_commands
from discord.ext import commands

from utils import reply

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        channel_id_str = await self.bot.db.get_setting(f"log_channel_{guild.id}")
        if not channel_id_str:
            return None
        return guild.get_channel(int(channel_id_str))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Простая автомодерация ссылок (если не админ)
        if "http://" in message.content or "https://" in message.content:
            if not message.author.guild_permissions.administrator:
                # Проверяем, разрешены ли ссылки (можно сделать настройку, но пока просто удаляем дискорд-инвайты или сторонние ссылки)
                if "discord.gg/" in message.content or "discord.com/invite/" in message.content:
                    try:
                        await message.delete()
                        warn = await message.channel.send(f"⚠️ {message.author.mention}, ссылки на приглашения в Discord запрещены!")
                        await warn.delete(delay=5)
                    except discord.Forbidden:
                        pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author and message.author.bot:
            return
        log_channel = await self._get_log_channel(message.guild)
        if not log_channel:
            return

        content = message.content or "[Медиа / Вложение без текста]"
        author = f"{message.author} ({message.author.id})" if message.author else "Неизвестный"

        emb = discord.Embed(
            title="🗑️ Сообщение удалено",
            description=f"**Автор:** {author}\n**Канал:** {message.channel.mention}\n**Текст:**\n{content[:1000]}",
            color=discord.Color.red()
        )
        emb.set_footer(text=f"ID пользователя: {message.author.id if message.author else 'N/A'}")
        await log_channel.send(embed=emb)

    @commands.command(name="setlog", description="Установить канал для логов модерации")
    @commands.has_permissions(administrator=True)
    async def setlog(self, ctx: commands.Context, channel: discord.TextChannel):
        await self.bot.db.set_setting(f"log_channel_{ctx.guild.id}", str(channel.id))
        await ctx.send(f"✅ Канал логов успешно установлен: {channel.mention}", delete_after=10)


async def setup(bot):
    await bot.add_cog(Moderation(bot))