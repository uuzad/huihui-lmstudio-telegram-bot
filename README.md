# Private AI Telegram Bot

Личный Telegram-бот: Telegram → Render → Cloudflare Tunnel → FreeLLMAPI на твоём ПК.

Бот отвечает только Telegram-пользователю, чей числовой ID указан в \`OWNER_ID\`. История диалога хранится в памяти процесса и очищается при перезапуске.

## Файлы проекта

- \`bot.py\` — Telegram-бот и FastAPI health endpoint.
- \`requirements.txt\` — зависимости Python.
- \`Dockerfile\` — сборка контейнера для Render.
- \`render.yaml\` — настройки Render Blueprint.
- \`.env.example\` — пример переменных окружения без секретов.

## Настройка FreeLLMAPI на Windows

1. Запусти FreeLLMAPI на своём ПК.
2. Убедись, что OpenAI-compatible API доступен локально по адресу \`http://127.0.0.1:31415/v1\`.
3. Включи API-ключ в FreeLLMAPI и сохрани его в переменную Render \`LM_STUDIO_API_KEY\`.
4. Запусти PowerShell и выполни:

   \`\`\`powershell
   cloudflared tunnel --url http://127.0.0.1:31415
   \`\`\`

5. Скопируй выданный HTTPS-адрес и добавь к нему \`/v1\`. Получившийся адрес укажи в Render как \`LM_STUDIO_BASE_URL\`.

Не закрывай FreeLLMAPI и окно Cloudflare Tunnel, пока бот должен работать. Quick Tunnel выдаёт временный адрес; после перезапуска туннеля обнови переменную в Render.

## Переменные Render

| Переменная | Значение |
|---|---|
| \`TELEGRAM_TOKEN\` | Токен бота от BotFather |
| \`OWNER_ID\` | Твой числовой Telegram ID |
| \`LM_STUDIO_BASE_URL\` | HTTPS-адрес Cloudflare Tunnel с окончанием \`/v1\` |
| \`LM_STUDIO_API_KEY\` | API-ключ FreeLLMAPI |
| \`LM_STUDIO_MODEL\` | \`auto\` |
| \`MAX_HISTORY_MESSAGES\` | Необязательно, по умолчанию \`20\` |
| \`REQUEST_TIMEOUT\` | Необязательно, по умолчанию \`180\` |

## Локальный запуск

Установи зависимости:

\`\`\`powershell
py -m pip install -r requirements.txt
\`\`\`

Задай переменные окружения и запусти:

\`\`\`powershell
py -m uvicorn bot:app --host 0.0.0.0 --port 10000
\`\`\`

## Команды

- \`/start\` — начать работу.
- \`/reset\` — очистить историю.
- \`/model\` — показать модель и адрес API.

## Примечания

- Render Free может засыпать после простоя, поэтому первый запрос иногда выполняется с задержкой.
- Если ПК выключен, FreeLLMAPI закрыта или Cloudflare Tunnel остановлен, модель недоступна.
- Не добавляй токены и API-ключи в GitHub. Храни их только в Environment Variables Render.
