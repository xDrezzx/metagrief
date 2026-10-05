"""Учёт сообщений участников + команда /activity."""
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


class Activity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        await self.bot.db.add_message(message.author.id)

    @app_commands.command(name="activity", description="Статистика сообщений участника")
    @app_commands.guild_only()
    async def activity(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        member = member or interaction.user
        a = await self.bot.db.get_activity(member.id)
        emb = discord.Embed(title=f"📊 Активность: {member.display_name}", color=discord.Color.green())
        emb.set_thumbnail(url=member.display_avatar.url)
        emb.add_field(name="Всего сообщений", value=str(a["total"]))
        emb.add_field(name="За 7 дней", value=str(a["last7"]))
        emb.add_field(name="За 30 дней", value=str(a["last30"]))
        emb.add_field(name="Активных дней", value=str(a["active_days"]))
        emb.add_field(name="Учёт с", value=a["first_day"] or "—")
        if member.joined_at:
            emb.add_field(name="На сервере с", value=discord.utils.format_dt(member.joined_at, "D"))
        await interaction.response.send_message(embed=emb)


async def setup(bot):
    await bot.add_cog(Activity(bot))
