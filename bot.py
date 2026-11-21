import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger("private-telegram-bot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
OWNER_ID_RAW = os.getenv("OWNER_ID", "").strip()
API_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:31415/v1").strip().rstrip("/")
API_KEY = os.getenv("LM_STUDIO_API_KEY", "").strip()
MODEL = os.getenv("LM_STUDIO_MODEL", "auto").strip() or "auto"
MAX_HISTORY_MESSAGES = max(2, int(os.getenv("MAX_HISTORY_MESSAGES", "20")))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "180"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("Environment variable TELEGRAM_TOKEN is missing.")
if not OWNER_ID_RAW.isdigit():
    raise RuntimeError("OWNER_ID must be your numeric Telegram user ID.")
OWNER_ID = int(OWNER_ID_RAW)

# История хранится только в памяти процесса и очищается после перезапуска.
history: dict[int, list[dict[str, str]]] = {}
user_locks: dict[int, asyncio.Lock] = {}

SYSTEM_PROMPT = (
    "Ты универсальный русскоязычный AI-помощник. "
    "Помогай с разными темами: отвечай на вопросы, объясняй сложное простыми словами, "
    "помогай с программированием, текстами, учёбой, идеями и повседневными задачами. "
    "Не ограничивай себя одной областью или конкретной платформой. "
    "Когда пишешь код, используй подходящий язык и форматируй его блоками Markdown. "
    "Если данных недостаточно, задай один конкретный уточняющий вопрос. "
    "Не утверждай, что запускал или проверял код, если этого не делал."
)


def is_owner(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == OWNER_ID)


async def call_model(messages: list[dict[str, str]]) -> str:
    payload: dict[str, Any] = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        "temperature": 0.7,
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"API returned no choices: {data}")
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    answer = str(content).strip()
    if not answer:
        raise RuntimeError("The model returned an empty response.")
    return answer


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner(update):
        return
    await update.effective_message.reply_text(
        "Бот запущен и готов к работе.\n\n"
        "Просто отправь сообщение — я отвечу через модель на твоём ПК.\n"
        "/reset — очистить историю\n"
        "/model — показать настройки модели"
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner(update):
        return
    user_id = update.effective_user.id
    history.pop(user_id, None)
    await update.effective_message.reply_text("История диалога очищена.")


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner(update):
        return
    await update.effective_message.reply_text(
        f"Модель: {MODEL}\n"
        f"API: {API_BASE_URL}\n"
        "Ключ API: настроен" if API_KEY else
        f"Модель: {MODEL}\nAPI: {API_BASE_URL}\nКлюч API: не задан"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner(update):
        return

    message = update.effective_message
    if message is None or not message.text:
        return

    user_id = update.effective_user.id
    lock = user_locks.setdefault(user_id, asyncio.Lock())

    async with lock:
        messages = history.setdefault(user_id, [])
        messages.append({"role": "user", "content": message.text})
        messages[:] = messages[-MAX_HISTORY_MESSAGES:]

        try:
            await context.bot.send_chat_action(
                chat_id=message.chat_id,
                action=ChatAction.TYPING,
            )
            answer = await call_model(messages)
            messages.append({"role": "assistant", "content": answer})
            messages[:] = messages[-MAX_HISTORY_MESSAGES:]

            # Telegram ограничивает длину одного сообщения.
            for offset in range(0, len(answer), 4000):
                await message.reply_text(answer[offset : offset + 4000])
        except httpx.HTTPStatusError as exc:
            logger.warning("Model API returned HTTP %s", exc.response.status_code)
            messages.pop()  # Удаляем неотвеченный запрос из истории.
            await message.reply_text(
                f"Ошибка API модели: HTTP {exc.response.status_code}. "
                "Проверь FreeLLMAPI и настройки Render."
            )
        except httpx.RequestError:
            logger.exception("Could not reach model API")
            messages.pop()
            await message.reply_text(
                "Не удалось подключиться к API на ПК. "
                "Проверь, что FreeLLMAPI и Cloudflare Tunnel запущены."
            )
        except Exception:
            logger.exception("Unexpected error while processing Telegram message")
            if messages and messages[-1].get("role") == "user":
                messages.pop()
            await message.reply_text("Произошла ошибка при обработке сообщения. Проверь логи Render.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("reset", reset_command))
    telegram_app.add_handler(CommandHandler("model", model_command))
    telegram_app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    await telegram_app.initialize()
    await telegram_app.start()
    if telegram_app.updater is None:
        raise RuntimeError("Telegram updater is not available.")
    await telegram_app.updater.start_polling(drop_pending_updates=True)
    app.state.telegram_app = telegram_app
    logger.info("Telegram polling started; model=%s", MODEL)

    try:
        yield
    finally:
        if telegram_app.updater and telegram_app.updater.running:
            await telegram_app.updater.stop()
        if telegram_app.running:
            await telegram_app.stop()
        await telegram_app.shutdown()
        logger.info("Telegram bot stopped")


app = FastAPI(title="Private AI Telegram Bot", lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "ok", "service": "private-ai-telegram-bot"}


@app.get("/health")
async def health():
    telegram_app = getattr(app.state, "telegram_app", None)
    return {
        "status": "ok" if telegram_app and telegram_app.running else "starting",
        "model": MODEL,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("bot:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
