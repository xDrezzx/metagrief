# MetaAssistant — Discord-бот для MetaGrief

Проверка заявок через Gemini (Ютубер / Хелпер / Жалобы / Техподдержка), анонсы видео, учёт активности.

## Структура
```
MetaAssistant/
├── main.py            # запуск бота
├── config.py          # константы (пороги, IP, сайт, промокод)
├── database.py        # SQLite: настройки, активность, кулдауны
├── gemini_ai.py       # промпты и вызовы Gemini (JSON-ответ)
├── youtube.py         # реальная статистика видео через YouTube Data API
├── knowledge_base.py  # база знаний техподдержки (РЕДАКТИРУЙ!)
├── cogs/
│   ├── admin.py       # /set_ping /set_channel /config ...
│   ├── forums.py      # обработка новых тем на форумах
│   ├── announce.py    # анонсы видео
│   └── activity.py    # учёт сообщений, /activity
├── requirements.txt
└── .env.example
```

## Создание бота от А до Я

### 1. Приложение и токен
1. Открой https://discord.com/developers/applications → **New Application** → назови `MetaAssistant`.
2. Вкладка **Bot** → **Reset Token** → скопируй токен (никому не показывай!).
3. Там же включи **Privileged Gateway Intents**: **Server Members Intent** и **Message Content Intent**.

### 2. Приглашение на сервер
1. **OAuth2 → URL Generator**: scopes `bot` и `applications.commands`.
2. Права: View Channels, Send Messages, Send Messages in Threads, Embed Links, Read Message History,
   Manage Messages (удаление ссылок в анонсах), Manage Threads (теги на темах), Mention Everyone (для пингов ролей).
3. Открой сгенерированную ссылку и добавь бота на сервер.

### 3. Ключи API
- **Gemini**: https://aistudio.google.com/apikey → Create API key.
- **YouTube Data API** (нужен, чтобы бот видел просмотры и описание видео): https://console.cloud.google.com →
  создай проект → *APIs & Services → Library* → **YouTube Data API v3** → Enable → *Credentials → Create API key*.

### 4. Установка
Нужен Python 3.10+ (https://python.org).
```bash
cd MetaAssistant
python -m venv venv
venv\Scripts\activate          # Windows;  Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # Windows: copy .env.example .env
```
Заполни `.env`: `DISCORD_TOKEN`, `GEMINI_API_KEY`, `YOUTUBE_API_KEY`, `GUILD_ID`
(ID сервера: Настройки → Расширенные → Режим разработчика, затем ПКМ по серверу → «Копировать ID»).

### 5. Запуск
```bash
python main.py
```

### 6. Настройка в Discord
1. Создай 4 канала типа **Форум** (по желанию добавь теги: «Принято», «Отказано», «На рассмотрении»).
2. Привяжи их: `/set_channel kind:Подача на Ютубера channel:#...` — и так для всех четырёх.
3. Создай текстовый канал для анонсов: `/set_channel kind:Канал анонсов видео channel:#...`
   (опционально `/set_youtuber_role` — кто может кидать ссылки).
4. Ответственные: `/set_ping forum:Подача на Хелпера user1:@xDrezzx23 user2:@TheLokser`
5. Проверь всё командой `/config`. Создай тестовую тему на форуме — бот ответит.
6. Дай боту доступ к форум-каналам (View Channel, Send Messages in Threads).

### 7. Хостинг 24/7
Дешёвый VPS (Ubuntu): скопируй проект, создай venv, и запусти через `systemd` или `tmux`/`pm2`.
Пример `/etc/systemd/system/metaassistant.service`:
```
[Unit]
Description=MetaAssistant
After=network.target
[Service]
WorkingDirectory=/opt/MetaAssistant
ExecStart=/opt/MetaAssistant/venv/bin/python main.py
Restart=always
[Install]
WantedBy=multi-user.target
```
`sudo systemctl enable --now metaassistant`

## Важно знать
- Gemini **не открывает ссылки** и не видит просмотры. Поэтому `youtube.py` получает статистику
  сам и передаёт её модели как факты. Без `YOUTUBE_API_KEY` заявки Ютуберов уйдут в `manual_check`.
- Закреплённый комментарий бот не проверяет: если рекламы нет в описании — отправит на ручную проверку.
- Активность считается с момента запуска бота (старые сообщения не импортируются).
- Дополни `knowledge_base.py` реальными инструкциями (особенно по привязке аккаунта).
- Не публикуй `.env` и токен. Если токен утёк — сразу сделай Reset Token.
