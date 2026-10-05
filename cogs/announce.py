"""Анонсы видео ютуберов.

Как работает:
1. Ютубер кидает ссылку на своё видео в СПЕЦИАЛЬНЫЙ канал (/set_channel kind:Канал для ссылок ютуберов).
2. Бот проверяет роль Ютубера и что это ссылка на YouTube, УДАЛЯЕТ сырое сообщение со ссылкой.
3. Бот публикует от своего лица красивый Embed в ОФИЦИАЛЬНЫЙ новостной канал
   (/set_channel kind:Новостной канал; если он не задан — анонс появится в том же канале).
Шаблон: 🎬 У Ютубера **[Ник]** вышло новое видео! Быстрее беги смотреть его -> [Ссылка]
"""
import logging

import discord
from discord.ext import commands

import youtube
from utils import SAFE_MENTIONS

log = logging.getLogger("announce")

MAX_LINKS_PER_MESSAGE = 3


class WatchView(discord.ui.View):
    """Кнопка-ссылка «Смотреть» под анонсом (link-кнопке не нужен callback и custom_id)."""

    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Смотреть на YouTube",
                                        emoji="▶️", url=url))


class Announce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- настройки ----------
    async def _channel(self, guild: discord.Guild, key: str):
        raw = await self.bot.db.get_setting(key)
        ch = guild.get_channel(int(raw)) if raw else None
        return ch if isinstance(ch, discord.TextChannel) else None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        submit_id = await self.bot.db.get_setting("announce_channel")  # спец. канал для ссылок
        if not submit_id or message.channel.id != int(submit_id):
            return

        member = message.author
        # админы могут писать всегда; остальные — только с ролью Ютубера (если роль задана)
        role_id = await self.bot.db.get_setting("youtuber_role")
        is_admin = isinstance(member, discord.Member) and member.guild_permissions.administrator
        if role_id and not is_admin and not any(r.id == int(role_id) for r in getattr(member, "roles", [])):
            return await self._warn(message, "⛔ Сюда могут кидать ссылки только Ютуберы проекта.")

        videos = youtube.extract_videos(message.content)
        if not videos:
            return await self._warn(
                message, "❌ Кидай сюда только ссылку на своё YouTube-видео (обычное, Shorts или трансляцию).")

        # куда публиковать: новостной канал, а если он не задан — туда же, где написали
        news = await self._channel(message.guild, "news_channel") or message.channel
        perms = news.permissions_for(message.guild.me)
        if not (perms.send_messages and perms.embed_links):
            return await self._warn(
                message, f"⚠️ У бота нет прав писать/встраивать ссылки в {news.mention}. Сообщите администрации.")

        posted, duplicates = 0, 0
        for v in videos[:MAX_LINKS_PER_MESSAGE]:
            if await self.bot.db.was_announced(v["id"]):
                duplicates += 1
                continue
            await self._post(news, member, v)
            await self.bot.db.mark_announced(v["id"], member.id)
            posted += 1

        # удаляем сырую ссылку ТОЛЬКО после публикации, чтобы видео не потерялось
        try:
            await message.delete()
        except discord.HTTPException:
            log.warning("Не смог удалить сообщение в %s — нужно право Manage Messages", message.channel.id)

        if duplicates and not posted:
            await message.channel.send(f"{member.mention} ℹ️ Об этом видео уже был анонс.", delete_after=8)
        elif posted and news.id != message.channel.id:
            await message.channel.send(f"{member.mention} ✅ Анонс опубликован в {news.mention}!", delete_after=8)

    async def _post(self, channel: discord.TextChannel, member: discord.Member, v: dict):
        nick = member.display_name
        meta = await youtube.get_title_and_author(v["id"])  # название видео (без API-ключа)

        emb = discord.Embed(
            title=(meta or {}).get("title") or "Новое видео!",
            url=v["url"],
            # Шаблон из ТЗ
            description=(f"🎬 У Ютубера **{nick}** вышло новое видео! "
                         f"Быстрее беги смотреть его -> [Ссылка]({v['url']})"),
            color=discord.Color.red())
        emb.set_author(name=nick, icon_url=member.display_avatar.url)
        emb.set_image(url=f"https://img.youtube.com/vi/{v['id']}/hqdefault.jpg")
        emb.set_footer(text="MetaGrief • Поддержи ютубера лайком и комментарием")

        await channel.send(embed=emb, view=WatchView(v["url"]), allowed_mentions=SAFE_MENTIONS)

    @staticmethod
    async def _warn(message: discord.Message, text: str):
        """Коротко предупреждает автора и чистит канал, чтобы он оставался только для ссылок."""
        try:
            await message.channel.send(f"{message.author.mention} {text}", delete_after=8)
        except discord.HTTPException:
            pass
        try:
            await message.delete()
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(Announce(bot))