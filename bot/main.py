import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import uvicorn

from config import BOT_TOKEN, API_BASE_URL, ALLOWED_TELEGRAM_IDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

app = FastAPI()

# Хранилище голосов: {ticket_id: {"rejected": set(user_ids), "message_ids": {user_id: (chat_id, message_id)}}}
votes: dict[str, dict] = {}


class NotifyPayload(BaseModel):
    id: str
    room: str
    author: str
    description: str


def build_ticket_keyboard(ticket_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Прийняти", callback_data=f"accept:{ticket_id}"),
            InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject:{ticket_id}"),
        ]
    ])


def build_ticket_message(payload: NotifyPayload) -> str:
    return (
        f"📋 <b>Нова заявка #{payload.id}</b>\n\n"
        f"🏠 <b>Аудиторія:</b> {payload.room}\n"
        f"👤 <b>Заявник:</b> {payload.author}\n"
        f"📝 <b>Опис:</b> {payload.description}"
    )


@app.post("/notify")
async def notify(payload: NotifyPayload):
    """Получает уведомление от API о новой заявке и рассылает всем разрешённым пользователям."""
    ticket_id = payload.id
    text = build_ticket_message(payload)
    keyboard = build_ticket_keyboard(ticket_id)

    votes[ticket_id] = {"rejected": set(), "message_ids": {}}

    for user_id in ALLOWED_TELEGRAM_IDS:
        try:
            msg = await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            votes[ticket_id]["message_ids"][user_id] = (user_id, msg.message_id)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

    return {"status": "ok"}


async def update_ticket_status(ticket_id: str, status: int) -> bool:
    """Отправляет PATCH-запрос на бэкенд для обновления статуса заявки."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{API_BASE_URL}/api/tickets/{ticket_id}/status",
                json={"status": status},
            )
            return resp.status_code == 200
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса заявки {ticket_id}: {e}")
        return False


async def remove_keyboards_for_ticket(ticket_id: str, result_text: str):
    """Убирает inline-кнопки у всех сообщений по заявке и добавляет результат."""
    ticket_data = votes.get(ticket_id)
    if not ticket_data:
        return
    for user_id, (chat_id, message_id) in ticket_data["message_ids"].items():
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, reply_markup=None
            )
            await bot.send_message(
                chat_id=chat_id,
                text=result_text,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения для {user_id}: {e}")


@router.callback_query(F.data.startswith("accept:"))
async def on_accept(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ALLOWED_TELEGRAM_IDS:
        await callback.answer("У вас немає доступу.", show_alert=True)
        return

    ticket_id = callback.data.split(":", 1)[1]

    if ticket_id not in votes:
        await callback.answer("Заявка вже оброблена.", show_alert=True)
        return

    success = await update_ticket_status(ticket_id, 1)  # InProgress
    if success:
        result_text = f"✅ Заявку <b>#{ticket_id}</b> прийнято користувачем <b>{callback.from_user.full_name}</b>"
        await remove_keyboards_for_ticket(ticket_id, result_text)
        del votes[ticket_id]
        await callback.answer("Заявку прийнято!", show_alert=True)
    else:
        await callback.answer("Помилка при оновленні статусу.", show_alert=True)


@router.callback_query(F.data.startswith("reject:"))
async def on_reject(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ALLOWED_TELEGRAM_IDS:
        await callback.answer("У вас немає доступу.", show_alert=True)
        return

    ticket_id = callback.data.split(":", 1)[1]

    if ticket_id not in votes:
        await callback.answer("Заявка вже оброблена.", show_alert=True)
        return

    votes[ticket_id]["rejected"].add(user_id)

    # Убираем кнопки у этого пользователя
    msg_data = votes[ticket_id]["message_ids"].get(user_id)
    if msg_data:
        try:
            await bot.edit_message_reply_markup(
                chat_id=msg_data[0], message_id=msg_data[1], reply_markup=None
            )
        except Exception:
            pass

    # Проверяем: все ли отклонили
    if votes[ticket_id]["rejected"] == set(votes[ticket_id]["message_ids"].keys()):
        success = await update_ticket_status(ticket_id, 3)  # Closed
        if success:
            result_text = f"❌ Заявку <b>#{ticket_id}</b> відхилено усіма користувачами."
            # Отправляем уведомление всем (кнопки уже убраны у каждого при reject)
            for uid in votes[ticket_id]["message_ids"]:
                try:
                    await bot.send_message(chat_id=uid, text=result_text, parse_mode="HTML")
                except Exception:
                    pass
            del votes[ticket_id]
        await callback.answer("Заявку відхилено усіма.", show_alert=True)
    else:
        await callback.answer("Ви відхилили заявку. Очікуємо рішення інших.", show_alert=True)


async def start_polling():
    """Запускает polling aiogram в фоне."""
    await dp.start_polling(bot)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_polling())
    logger.info(f"Бот запущен. Разрешённые ID: {ALLOWED_TELEGRAM_IDS}")


@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
