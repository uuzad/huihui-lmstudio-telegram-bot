# Huihui Qwen Telegram Bot (LM Studio)

Личный Telegram-бот, который отправляет сообщения в локальную модель LM Studio через OpenAI-compatible API.

## Как работает

Telegram → Render → Cloudflare Tunnel → LM Studio на твоём ПК → ответ в Telegram.

Бот разрешает общение только Telegram-пользователю с `OWNER_ID`.

## 1. Подготовь LM Studio на ПК

1. Загрузи модель в LM Studio.
2. Открой Developer / Local Server и запусти сервер.
3. Убедись, что OpenAI-compatible API доступен по адресу `http://127.0.0.1:1234/v1`.
4. Включи API authentication и создай API key.
5. Запусти Cloudflare Quick Tunnel на локальный порт LM Studio:

   ```powershell
   cloudflared tunnel --url http://localhost:1234
   ```

6. Скопируй выданный HTTPS URL. Не публикуй API key и не отключай аутентификацию.

Важно: Quick Tunnel может выдавать новый адрес после перезапуска. Тогда обнови `LM_STUDIO_BASE_URL` в Render. Компьютер, LM Studio и tunnel должны оставаться включёнными.

## 2. Создай Telegram-бота

Через BotFather создай бота и скопируй токен. Если старый токен когда-либо публиковался в чатах или логах, сначала отзови его через BotFather и используй новый.

## 3. Загрузи проект на GitHub

Создай пустой репозиторий и загрузи все файлы этого проекта. Не загружай `.env` и никогда не добавляй токены или API keys в код.

## 4. Разверни на Render

1. Создай на Render новый **Web Service** и подключи репозиторий.
2. Render может определить настройки из `render.yaml`. Если нет:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn bot:app --host 0.0.0.0 --port $PORT`
3. Добавь Environment Variables:

| Key | Value |
|---|---|
| `TELEGRAM_TOKEN` | токен Telegram-бота |
| `OWNER_ID` | твой числовой Telegram ID |
| `LM_STUDIO_BASE_URL` | адрес туннеля + `/v1` |
| `LM_STUDIO_API_KEY` | API key из LM Studio |
| `LM_STUDIO_MODEL` | `huihui-qwen3.8-27b-abliterated` |

4. Запусти Deploy.

## Команды бота

- `/start` — начать работу
- `/reset` — очистить историю диалога
- `/model` — показать модель и адрес API

## Важные ограничения

- История хранится в оперативной памяти Render и очищается при перезапуске.
- Бесплатный Web Service на Render может засыпать при простое.
- Если ПК выключен, LM Studio закрыта или Cloudflare Tunnel остановлен, модель будет недоступна.
- Не публикуй токены Telegram, API key LM Studio или URL с секретами.
