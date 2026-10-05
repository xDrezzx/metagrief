import discord
from discord import app_commands

# Безопасные упоминания (чтобы бот случайно не пинговал @everyone или @here)
SAFE_MENTIONS = discord.AllowedMentions(everyone=False, roles=False, users=True)

# Проверка на валидность ссылки
def is_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")

# Парсинг цвета
def parse_color(color_str: str) -> discord.Color:
    try:
        color_str = color_str.strip("#")
        return discord.Color(int(color_str, 16))
    except Exception:
        return discord.Color.default()

# Безопасная отправка ответа на инпут (Именно этого не хватало!)
async def reply(interaction: discord.Interaction, content: str, ephemeral: bool = False, **kwargs):
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=ephemeral, **kwargs)
    else:
        await interaction.response.send_message(content, ephemeral=ephemeral, **kwargs)