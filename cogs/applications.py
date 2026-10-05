import json
import os
import time
import discord
from discord.ext import commands
from discord import app_commands

CONFIG_FILE = "curators_config.json"

CRITERIA = {
    "MEDIA": (
        "📋 **Критерии на должность «MEDIA» (Ютубер):**\n"
        "• Возраст: от 13 лет.\n"
        "• Наличие IP сервера в описании (`mc.MetaGriefs.xyz`).\n"
        "• Активность: от 70 просмотров на видео / Shorts.\n"
        "• Качественный и адекватный контент по Minecraft."
    ),
    "ХЕЛПЕР": (
        "🛡️ **Критерии на должность «ХЕЛПЕР» (КП):**\n"
        "• Возраст: от 14 лет (возможны исключения).\n"
        "• Отличное знание правил сервера.\n"
        "• Адекватность, стрессоустойчивость и активность в игре.\n"
        "• Наличие исправного микрофона."
    ),
    "ЖАЛОБА": (
        "⚠️ **Правила подачи жалобы:**\n"
        "• Обязательно прикладывайте видео-доказательства (нарушение должно быть четко видно).\n"
        "• Скриншоты принимаются в редких случаях (для чата).\n"
        "• Указывайте точный ник нарушителя."
    ),
    "ТЕХ-ПОДДЕРЖКА": (
        "🛠️ **Правила тех-поддержки:**\n"
        "• Опишите вашу проблему максимально подробно.\n"
        "• Прикрепите скриншоты ошибки, если они есть.\n"
        "• Ожидайте ответа специалиста в ЛС."
    )
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "COOLDOWNS" not in data:
                    data["COOLDOWNS"] = {}
                if "ROLES" not in data:
                    data["ROLES"] = {"MEDIA": None, "ХЕЛПЕР": None, "SUPPORT": None}
                return data
        except Exception:
            pass
    return {
        "MEDIA": [],
        "ХЕЛПЕР": [],
        "SUPPORT": [],
        "ROLES": {"MEDIA": None, "ХЕЛПЕР": None, "SUPPORT": None},
        "COOLDOWNS": {}
    }


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


class ApplicationModal(discord.ui.Modal):
    def __init__(self, form_type: str):
        super().__init__(title=f"Заявка: {form_type}")
        self.form_type = form_type

        self.ign = discord.ui.TextInput(
            label="Игровой никнейм",
            placeholder="Ваш ник на сервере...",
            required=True,
            max_length=50
        )
        self.age = discord.ui.TextInput(
            label="Реальный возраст",
            placeholder="Сколько вам лет (цифрой)...",
            required=True,
            max_length=3
        )

        if form_type in ["MEDIA", "ХЕЛПЕР"]:
            link_label = "Ссылка на YouTube / портфолио" if form_type == "MEDIA" else "Ссылка на профиль / о себе"
            self.extra_field = discord.ui.TextInput(
                label=link_label,
                placeholder="https://...",
                required=True,
                max_length=200
            )
        else:
            self.extra_field = discord.ui.TextInput(
                label="Суть обращения / Описание",
                placeholder="Подробно опишите проблему или жалобу...",
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=500
            )

        self.add_item(self.ign)
        self.add_item(self.age)
        self.add_item(self.extra_field)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        config = load_config()

        # Проверка КД (ЧС на 5 дней после отказа)
        cooldown_key = f"{interaction.user.id}_{self.form_type}"
        current_time = time.time()
        if cooldown_key in config.get("COOLDOWNS", {}):
            expire_time = config["COOLDOWNS"][cooldown_key]
            if current_time < expire_time:
                remaining_hours = int((expire_time - current_time) / 3600)
                remaining_days = remaining_hours // 24
                rem_hours_mod = remaining_hours % 24

                time_str = f"{remaining_days} дн. {rem_hours_mod} час." if remaining_days > 0 else f"{remaining_hours} час."
                await interaction.followup.send(
                    f"❌ Вы не можете подать заявку в эту категорию, так как находитесь в черном списке (КД после отказа).\n"
                    f"⏳ До окончания блокировки осталось: **{time_str}**.",
                    ephemeral=True
                )
                return
            else:
                del config["COOLDOWNS"][cooldown_key]
                save_config(config)

        if self.form_type == "MEDIA":
            target_ids = config.get("MEDIA", [])
        elif self.form_type == "ХЕЛПЕР":
            target_ids = config.get("ХЕЛПЕР", [])
        else:
            target_ids = config.get("SUPPORT", [])

        if not target_ids:
            await interaction.followup.send(
                "❌ Ошибка: Для этого типа заявок еще не назначены кураторы! Сообщите администрации.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📩 Новая заявка: [{self.form_type}]",
            description=(
                f"👤 **Игрок:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                f"🏷 **Никнейм:** `{self.ign.value}`\n"
                f"🎂 **Возраст:** `{self.age.value}`\n"
                f"📌 **Информация/Ссылка:** {self.extra_field.value}"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"ID игрока: {interaction.user.id}")

        sent_count = 0
        for curator_id in target_ids:
            try:
                curator = interaction.client.get_user(curator_id) or await interaction.client.fetch_user(curator_id)
                if curator:
                    await curator.send(embed=embed,
                                       view=AdminActionView(interaction.user.id, self.form_type, interaction.guild_id))
                    sent_count += 1
            except Exception:
                pass

        if sent_count > 0:
            await interaction.followup.send(
                "✅ Ваша заявка успешно отправлена кураторам на рассмотрение! Ожидайте ответа в ЛС.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ Ошибка: Не удалось доставить заявку кураторам (возможно, у них закрыты ЛС).",
                ephemeral=True
            )


class DeclineReasonModal(discord.ui.Modal, title="Причина отклонения заявки"):
    def __init__(self, applicant_id: int, form_type: str, original_message: discord.Message, guild_id: int):
        super().__init__()
        self.applicant_id = applicant_id
        self.form_type = form_type
        self.original_message = original_message
        self.guild_id = guild_id

        self.reason = discord.ui.TextInput(
            label="Укажите причину отказа",
            placeholder="Например: Не подходите по возрасту, мало просмотров...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        reason_text = self.reason.value

        config = load_config()
        if "COOLDOWNS" not in config:
            config["COOLDOWNS"] = {}

        cooldown_duration = 5 * 24 * 60 * 60  # КД на 5 дней
        config["COOLDOWNS"][f"{self.applicant_id}_{self.form_type}"] = time.time() + cooldown_duration
        save_config(config)

        dm_sent = True
        try:
            applicant = await interaction.client.fetch_user(self.applicant_id)
            if applicant:
                embed_user = discord.Embed(
                    title=f"❌ Результат рассмотрения заявки [{self.form_type}]",
                    description=(
                        "К сожалению, ваша заявка на проект **MetaGrief** была **отклонена**.\n\n"
                        f"📌 **Причина от куратора:**\n> {reason_text}\n\n"
                        "⏳ **Внимание:** Из-за отклонения заявки вам установлен **черный список (КД) на 5 дней** для повторной подачи."
                    ),
                    color=discord.Color.red()
                )
                await applicant.send(embed=embed_user)
        except Exception:
            dm_sent = False

        embed = self.original_message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Статус",
                        value=f"❌ **Отклонено** куратором {interaction.user.mention}.\n**Причина:** {reason_text}\n⏳ *Установлен КД на 5 дней.*",
                        inline=False)

        note = "" if dm_sent else "\n*(⚠️ Игроку не удалось отправить ЛС)*"
        await self.original_message.edit(embed=embed, view=None)
        await interaction.followup.send(f"✅ Заявка отклонена, игроку выдан КД на 5 дней и отправлена причина.{note}",
                                        ephemeral=True)


class AdminActionView(discord.ui.View):
    def __init__(self, applicant_id: int, form_type: str, guild_id: int):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.form_type = form_type
        self.guild_id = guild_id

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.green, custom_id="curator_accept_v4")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        config = load_config()
        roles_dict = config.get("ROLES", {})
        role_id = roles_dict.get(self.form_type)

        role_assigned_status = ""
        guild = interaction.client.get_guild(self.guild_id) if self.guild_id else None

        if guild and role_id:
            try:
                member = guild.get_member(self.applicant_id) or await guild.fetch_member(self.applicant_id)
                role = guild.get_role(role_id)
                if member and role:
                    await member.add_roles(role,
                                           reason=f"Одобрена заявка [{self.form_type}] куратором {interaction.user}")
                    role_assigned_status = f"\n✨ Роль **{role.name}** успешно выдана!"
            except Exception as e:
                role_assigned_status = f"\n⚠️️ Не удалось выдать роль автоматически: `{e}`"

        dm_sent = True
        try:
            applicant = await interaction.client.fetch_user(self.applicant_id)
            if applicant:
                embed_user = discord.Embed(
                    title=f"🎉 Поздравляем! Заявка [{self.form_type}] одобрена!",
                    description=(
                        "Ваша заявка на проект **MetaGrief** успешно прошла отбор!\n"
                        f"{role_assigned_status}\n\n"
                        "✨ **Что делать дальше?**\n"
                        "Свяжитесь с куратором в Discord для получения дальнейших инструкций."
                    ),
                    color=discord.Color.green()
                )
                await applicant.send(embed=embed_user)
        except Exception:
            dm_sent = False

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Статус",
                        value=f"✅ **Одобрено** куратором {interaction.user.mention}{role_assigned_status}",
                        inline=False)

        note = "" if dm_sent else "\n*(⚠️ Игроку не удалось отправить ЛС)*"
        await interaction.message.edit(embed=embed, view=None)
        await interaction.followup.send(f"✅ Вы приняли заявку!{note}", ephemeral=True)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.red, custom_id="curator_decline_v4")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            DeclineReasonModal(self.applicant_id, self.form_type, interaction.message, self.guild_id))


class ApplicationView(discord.ui.View):
    def __init__(self, form_type: str):
        super().__init__(timeout=None)
        self.form_type = form_type

    @discord.ui.button(label="Подать заявку", style=discord.ButtonStyle.green, custom_id="apply_btn_v5")
    async def apply_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplicationModal(self.form_type))

    @discord.ui.button(label="📜 Критерии", style=discord.ButtonStyle.blurple, custom_id="criteria_btn_v5")
    async def criteria_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        text = CRITERIA.get(self.form_type, "Критерии не найдены.")
        await interaction.response.send_message(text, ephemeral=True)


class Applications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    curators_group = app_commands.Group(name="curators", description="Управление кураторами и ролями заявок")

    @curators_group.command(name="add", description="Добавить куратора к категории")
    @app_commands.choices(category=[
        app_commands.Choice(name="Media (Ютуберы)", value="MEDIA"),
        app_commands.Choice(name="Helper (КП)", value="ХЕЛПЕР"),
        app_commands.Choice(name="Support (Жалобы/Техника)", value="SUPPORT")
    ])
    @app_commands.default_permissions(administrator=True)
    async def curators_add(self, interaction: discord.Interaction, category: str, member: discord.Member):
        config = load_config()
        if member.id not in config[category]:
            config[category].append(member.id)
            save_config(config)
            await interaction.response.send_message(
                f"✅ Пользователь {member.mention} успешно добавлен в кураторы категории **{category}**!",
                ephemeral=True)
        else:
            await interaction.response.send_message(
                f"⚠️️ {member.mention} уже находится в списке кураторов этой категории.", ephemeral=True)

    @curators_group.command(name="remove", description="Удалить куратора из категории")
    @app_commands.choices(category=[
        app_commands.Choice(name="Media (Ютуберы)", value="MEDIA"),
        app_commands.Choice(name="Helper (КП)", value="ХЕЛПЕР"),
        app_commands.Choice(name="Support (Жалобы/Техника)", value="SUPPORT")
    ])
    @app_commands.default_permissions(administrator=True)
    async def curators_remove(self, interaction: discord.Interaction, category: str, member: discord.Member):
        config = load_config()
        if member.id in config[category]:
            config[category].remove(member.id)
            save_config(config)
            await interaction.response.send_message(
                f"✅ Пользователь {member.mention} удален из кураторов категории **{category}**.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ {member.mention} не найден в списке кураторов этой категории.",
                                                    ephemeral=True)

    @curators_group.command(name="role", description="Установить роль для автовыдачи при одобрении")
    @app_commands.choices(category=[
        app_commands.Choice(name="Media (Ютуберы)", value="MEDIA"),
        app_commands.Choice(name="Helper (КП)", value="ХЕЛПЕР"),
        app_commands.Choice(name="Support (Жалобы/Техника)", value="SUPPORT")
    ])
    @app_commands.default_permissions(administrator=True)
    async def curators_role(self, interaction: discord.Interaction, category: str, role: discord.Role):
        config = load_config()
        if "ROLES" not in config:
            config["ROLES"] = {}
        config["ROLES"][category] = role.id
        save_config(config)
        await interaction.response.send_message(
            f"✅ Автоматическая выдача роли **{role.name}** привязана к категории **{category}**!", ephemeral=True)

    @curators_group.command(name="role_remove", description="Убрать автоматическую выдачу роли для категории")
    @app_commands.choices(category=[
        app_commands.Choice(name="Media (Ютуберы)", value="MEDIA"),
        app_commands.Choice(name="Helper (КП)", value="ХЕЛПЕР"),
        app_commands.Choice(name="Support (Жалобы/Техника)", value="SUPPORT")
    ])
    @app_commands.default_permissions(administrator=True)
    async def curators_role_remove(self, interaction: discord.Interaction, category: str):
        config = load_config()
        if "ROLES" in config and config["ROLES"].get(category):
            config["ROLES"][category] = None
            save_config(config)
            await interaction.response.send_message(
                f"✅ Автоматическая выдача роли для категории **{category}** успешно отключена!", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ У категории **{category}** и так не была привязана роль.",
                                                    ephemeral=True)

    @curators_group.command(name="list", description="Показать список кураторов и привязанные роли")
    @app_commands.default_permissions(administrator=True)
    async def curators_list(self, interaction: discord.Interaction):
        config = load_config()

        def format_members(id_list):
            if not id_list:
                return "*Нет кураторов*"
            return ", ".join([f"<@{uid}>" for uid in id_list])

        roles_dict = config.get("ROLES", {})

        def get_role_mention(cat):
            r_id = roles_dict.get(cat)
            return f"<@&{r_id}>" if r_id else "*Не установлена*"

        embed = discord.Embed(
            title="👥 Настройки кураторов и ролей",
            description=(
                f"**🎬 Media (Ютуберы):**\nКураторы: {format_members(config.get('MEDIA', []))}\nРоль: {get_role_mention('MEDIA')}\n\n"
                f"**🛡️ Helper (КП):**\nКураторы: {format_members(config.get('ХЕЛПЕР', []))}\nРоль: {get_role_mention('ХЕЛПЕР')}\n\n"
                f"**🛠️ Support (Жалобы/Техника):**\nКураторы: {format_members(config.get('SUPPORT', []))}\nРоль: {get_role_mention('SUPPORT')}"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setup_media", description="Отправить форму заявки на ютубера")
    @app_commands.default_permissions(administrator=True)
    async def setup_media(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="📋 ФОРМА ПОДАЧИ ЗАЯВКИ НА ДОЛЖНОСТЬ «MEDIA»",
            description="Нажмите на кнопку ниже, чтобы заполнить анкету, или ознакомьтесь с критериями.",
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=embed, view=ApplicationView("MEDIA"))
        await interaction.followup.send("Форма отправлена!", ephemeral=True)

    @app_commands.command(name="setup_helper", description="Отправить форму заявки на хелпера")
    @app_commands.default_permissions(administrator=True)
    async def setup_helper(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="🛡️ ФОРМА ПОДАЧИ ЗАЯВКИ НА ДОЛЖНОСТЬ «ХЕЛПЕР»",
            description="Нажмите на кнопку ниже, чтобы заполнить заявку, или изучите критерии.",
            color=discord.Color.blue()
        )
        await interaction.channel.send(embed=embed, view=ApplicationView("ХЕЛПЕР"))
        await interaction.followup.send("Форма отправлена!", ephemeral=True)

    @app_commands.command(name="setup_reports", description="Отправить форму жалобы")
    @app_commands.default_permissions(administrator=True)
    async def setup_reports(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="⚠️ ПОДАЧА ЖАЛОБЫ НА ИГРОКА",
            description="Нажмите на кнопку ниже для отправки жалобы.",
            color=discord.Color.orange()
        )
        await interaction.channel.send(embed=embed, view=ApplicationView("ЖАЛОБА"))
        await interaction.followup.send("Форма отправлена!", ephemeral=True)

    @app_commands.command(name="setup_support", description="Отправить форму тех-поддержки")
    @app_commands.default_permissions(administrator=True)
    async def setup_support(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="🛠️ ТЕХНИЧЕСКАЯ ПОДДЕРЖКА",
            description="Нажмите на кнопку ниже, чтобы создать обращение в поддержку.",
            color=discord.Color.purple()
        )
        await interaction.channel.send(embed=embed, view=ApplicationView("ТЕХ-ПОДДЕРЖКА"))
        await interaction.followup.send("Форма отправлена!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Applications(bot))