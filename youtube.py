"""Разбор YouTube-ссылок и получение РЕАЛЬНОЙ статистики через YouTube Data API v3.
Gemini не умеет открывать ссылки и видеть просмотры, поэтому факты собираем здесь."""
import datetime as dt
import re
from typing import Optional

import aiohttp

import config

YT_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?"
    r"(?:youtube\.com/(watch\?(?:\S*?&)?v=|shorts/|live/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})")


def extract_videos(text: str) -> list[dict]:
    seen, out = set(), []
    for m in YT_RE.finditer(text or ""):
        vid = m.group(2)
        if vid in seen:
            continue
        seen.add(vid)
        is_short = (m.group(1) or "").startswith("shorts")
        url = f"https://www.youtube.com/shorts/{vid}" if is_short else f"https://www.youtube.com/watch?v={vid}"
        out.append({"id": vid, "url": url, "is_short_url": is_short})
    return out


def _duration_seconds(iso: str) -> int:
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def check_ad(description: str) -> dict:
    low = (description or "").lower()
    return {
        "ip": any(ip.lower() in low for ip in config.SERVER_IPS),
        "site": "metagriefs.fun" in low,
        "promo": re.search(r"(?<![\wА-Яа-я])meta(?![\wА-Яа-я])", description or "", re.I) is not None,
    }


async def fetch_video(session: aiohttp.ClientSession, video_id: str) -> Optional[dict]:
    if not config.YOUTUBE_API_KEY:
        return None
    params = {"part": "snippet,statistics,contentDetails", "id": video_id, "key": config.YOUTUBE_API_KEY}
    try:
        async with session.get("https://www.googleapis.com/youtube/v3/videos", params=params,
                               timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                return None
            data = await r.json()
    except Exception:
        return None
    items = data.get("items") or []
    if not items:
        return None
    it = items[0]
    sn, st, cd = it["snippet"], it.get("statistics", {}), it.get("contentDetails", {})
    published = dt.datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
    days = max((dt.datetime.now(dt.timezone.utc) - published).total_seconds() / 86400, 1.0)
    views = int(st.get("viewCount", 0))
    return {
        "title": sn.get("title", ""), "description": sn.get("description", ""),
        "channel": sn.get("channelTitle", ""), "views": views, "days": round(days, 1),
        "views_per_day": round(views / days, 1), "duration": _duration_seconds(cd.get("duration", "")),
    }


async def build_media_facts(text: str) -> str:
    """Текстовый блок FACTS для Gemini по всем ссылкам в заявке."""
    videos = extract_videos(text)
    if not videos:
        return "В заявке НЕТ ни одной ссылки на YouTube-видео."
    if not config.YOUTUBE_API_KEY:
        return (f"Найдено ссылок на YouTube: {len(videos)}, но YouTube API не настроен — "
                "просмотры и описание проверить автоматически НЕЛЬЗЯ (ставь manual_check по этим пунктам).")
    lines = []
    async with aiohttp.ClientSession() as session:
        for v in videos[:5]:
            info = await fetch_video(session, v["id"])
            if not info:
                lines.append(f"- {v['url']}: не удалось получить данные (видео скрыто/удалено/ошибка API).")
                continue
            is_short = v["is_short_url"] or 0 < info["duration"] <= 60
            need = config.MIN_VIEWS_PER_DAY_SHORTS if is_short else config.MIN_VIEWS_PER_DAY_VIDEO
            ok = info["views_per_day"] >= need
            ad = check_ad(info["description"])
            lines.append(
                f"- {v['url']} | тип: {'Shorts' if is_short else 'обычное видео'} | канал: {info['channel']}\n"
                f"  название: {info['title']}\n"
                f"  просмотров: {info['views']}, возраст видео: {info['days']} дн., "
                f"≈{info['views_per_day']} просм./день (порог {need}) -> {'ДОСТАТОЧНО' if ok else 'НЕДОСТАТОЧНО'}\n"
                f"  реклама в ОПИСАНИИ: IP={'да' if ad['ip'] else 'нет'}, сайт={'да' if ad['site'] else 'нет'}, "
                f"промокод META={'да' if ad['promo'] else 'нет'}\n"
                f"  описание (начало): {info['description'][:400]!r}")
    lines.append("Закреплённый комментарий автоматически НЕ проверяется.")
    return "\n".join(lines)
