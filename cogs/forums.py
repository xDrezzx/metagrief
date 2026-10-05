"""Перехват новых тем на 4 форумах -> проверка Gemini -> ответ в теме."""
import asyncio
import logging
import re
import time

import discord
from discord.ext import commands

import config
import youtube
from gemini_ai import ReviewResult

log = logging.getLogger("forums")

STYLE = {
    "accepted": ("✅ Принято", discord.Color.green()),
    "rejected": ("❌ Отказано", discord.Color.red()),
    "manual_check": ("🕓 Нужна ручная проверка", discord.Color.orange()),
}
SUPPORT_STYLE = {"accepted": ("🛠 Ответ поддержки", discord.Color.green())}
LINK_RE = re.compile(r"https?://\S+")


class Forums(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._seen: set[int] = set()

    async def forum_type_of(self, channel_id: int):
        for key in config.FORUMS:
            v = await self.bot.db.get_setting(f"forum:{key}")
            if v and int(v) == channel_id:
                return key
        return None

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if not isinstance(thread.parent, discord.ForumChannel) or thread.id in self._seen:
            return
        ftype = await self.forum_type_of(thread.parent_id)
        if not ftype or thread.owner_id == self.bot.user.id:
            return
        self._seen.add(thread.id)
        try:
            await self.process(thread, ftype)
        except Exception:
            log.exception("Ошибка обработки темы %s", thread.id)
            try:
                await thread.send("⚠️ Произошла ошибка при проверке. Тему рассмотрит администрация.")
            except discord.HTTPException:
                pass

    async def process(self, thread: discord.Thread, ftype: str):
        starter = None
        for _ in range(4):  # первое сообщение появляется не мгновенно
            try:
                starter = await thread.fetch_message(thread.id)
                break
            except discord.NotFound:
                await asyncio.sleep(1.5)
        if starter is None:
            return

        owner_id = thread.owner_id or starter.author.id
        text = f"Заголовок темы: {thread.name}\n\n{starter.content}".strip()
        db = self.bot.db

        async with thread.typing():
            facts = ""
            if ftype == "media":
                now = int(time.time())
                last = await db.get_cooldown("media", owner_id)
                left = last + config.MEDIA_COOLDOWN_DAYS * 86400 - now
                if last and left > 0:
                    h, m = divmod(left // 60, 60)
                    res = ReviewResult(
                        "rejected", "Кулдаун подачи заявки ещё не истёк.",
                        f"Заявку на Ютубера можно подавать раз в {config.MEDIA_COOLDOWN_DAYS} дн. "
                        f"Попробуй снова через **{h} ч {m} мин**.")
                    return await self.finish(thread, ftype, owner_id, res)
                await db.set_cooldown("media", owner_id, now)
                facts = await youtube.build_media_facts(text)

            elif ftype == "helper":
                facts = await self.helper_facts(thread, owner_id)

            elif ftype == "report":
                links = LINK_RE.findall(starter.content)
                facts = (f"Вложений (файлов/скриншотов): {len(starter.attachments)}; ссылок: {len(links)}.\n"
                         f"Доказательства {'ЕСТЬ' if starter.attachments or links else 'ОТСУТСТВУЮТ'} (формально).")

            res = await self.bot.gemini.review(ftype, text, facts)
        await self.finish(thread, ftype, owner_id, res)

    async def helper_facts(self, thread: discord.Thread, owner_id: int) -> str:
        a = await self.bot.db.get_activity(owner_id)
        member = thread.guild.get_member(owner_id)
        joined = member.joined_at.strftime("%Y-%m-%d") if member and member.joined_at else "неизвестно"
        return (f"Активность автора в чате: всего сообщений {a['total']}, за 7 дней {a['last7']}, "
                f"за 30 дней {a['last30']}, активных дней {a['active_days']} (учёт ведётся с {a['first_day'] or '—'}).\n"
                f"На сервере с: {joined}.")

    async def build_pings(self, ftype: str) -> str:
        p = await self.bot.db.get_ping(ftype)
        return " ".join([f"<@{i}>" for i in p["users"]] + [f"<@&{i}>" for i in p["roles"]])

    async def finish(self, thread: discord.Thread, ftype: str, owner_id: int, res: ReviewResult):
        title, color = (SUPPORT_STYLE if ftype == "support" else {}).get(res.status) or STYLE[res.status]
        emb = discord.Embed(title=title, description=res.reply, color=color)
        emb.add_field(name="Причина", value=res.reason, inline=False)
        emb.set_footer(text="MetaAssistant • ИИ-проверка (Gemini). Решение может быть пересмотрено администрацией.")

        # кого пинговать: всё, что не отказ; для техподдержки — только если нужен админ
        need_staff = res.status == "manual_check" or (res.status == "accepted" and ftype != "support")
        pings = await self.build_pings(ftype) if need_staff else ""
        content = f"<@{owner_id}> {pings}".strip()
        await thread.send(content=content, embed=emb,
                          allowed_mentions=discord.AllowedMentions(users=True, roles=True))

        await self.apply_tag(thread, res.status)
        await self.bot.db.log_application(ftype, thread.id, owner_id, res.status, res.reason)

    async def apply_tag(self, thread: discord.Thread, status: str):
        names = config.STATUS_TAGS.get(status, [])
        tag = next((t for t in thread.parent.available_tags if t.name.lower() in names), None)
        if not tag:
            return
        try:
            await thread.add_tags(tag)
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(Forums(bot))
