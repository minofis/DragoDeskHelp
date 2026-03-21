import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandObject
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

STATUS_NAMES = {
    0: "Нова",
    1: "В роботі",
    2: "Виконано",
    3: "Закрито",
}

STATUS_ICONS = {
    0: "🆕",
    1: "🔧",
    2: "✅",
    3: "🔒",
}


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


def build_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Нові", callback_data="list:0"),
         InlineKeyboardButton(text="🔧 В роботі", callback_data="list:1")],
        [InlineKeyboardButton(text="✅ Виконано", callback_data="list:2"),
         InlineKeyboardButton(text="🔒 Закрито", callback_data="list:3")],
        [InlineKeyboardButton(text="📂 Мої заявки", callback_data="my_tickets")],
    ])


async def fetch_tickets(status: int | None = None, assignee_id: str | None = None) -> list[dict] | None:
    """Запрашивает список заявок из API."""
    try:
        params = {}
        if status is not None:
            params["status"] = status
        if assignee_id is not None:
            params["assigneeId"] = assignee_id
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE_URL}/api/tickets", params=params)
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception as e:
        logger.error(f"Ошибка при получении заявок: {e}")
        return None


async def fetch_ticket(ticket_id: int) -> dict | None:
    """Запрашивает одну заявку по ID из API."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE_URL}/api/tickets/{ticket_id}")
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception as e:
        logger.error(f"Ошибка при получении заявки {ticket_id}: {e}")
        return None


def format_ticket_detail(t: dict) -> str:
    """Форматирует полную информацию о заявке."""
    status_text = t.get("statusText", "Невідомо")
    assignee = t.get("assigneeId") or "Не призначено"
    return (
        f"📋 <b>Заявка #{t['id']}</b>\n\n"
        f"🏠 <b>Аудиторія:</b> {t['roomNumber']}\n"
        f"👤 <b>Заявник:</b> {t['authorName']}\n"
        f"📝 <b>Опис:</b> {t['description']}\n"
        f"📊 <b>Статус:</b> {status_text}\n"
        f"🧑‍🔧 <b>Виконавець:</b> {assignee}\n"
        f"📅 <b>Створено:</b> {t['createdAt']}"
    )


def format_ticket_list(tickets: list[dict], title: str) -> str:
    """Форматирует список заявок."""
    if not tickets:
        return f"{title}\n\nЗаявок не знайдено."
    lines = [title, ""]
    for t in tickets:
        status_text = t.get("statusText", "?")
        lines.append(
            f"• <b>#{t['id']}</b> | 🏠 {t['roomNumber']} | {status_text}\n"
            f"  {t['description'][:80]}"
        )
    lines.append(f"\nВсього: {len(tickets)}")
    lines.append("\nВикористайте /ticket <номер> для деталей.")
    return "\n".join(lines)


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


async def update_ticket_status(ticket_id: str, status: int, assignee_id: str | None = None) -> bool:
    """Отправляет PATCH-запрос на бэкенд для обновления статуса заявки."""
    try:
        payload = {"status": status}
        if assignee_id is not None:
            payload["assigneeId"] = assignee_id
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{API_BASE_URL}/api/tickets/{ticket_id}/status",
                json=payload,
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

    success = await update_ticket_status(ticket_id, 1, assignee_id=str(user_id))  # InProgress
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


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id not in ALLOWED_TELEGRAM_IDS:
        await message.answer("У вас немає доступу.")
        return
    await message.answer(
        "👋 <b>ADHD HelpDesk Бот</b>\n\n"
        "📋 <b>Оберіть категорію заявок:</b>\n\n"
        "Або використайте /ticket <номер> для деталей.",
        reply_markup=build_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("ticket"))
async def cmd_ticket(message: Message, command: CommandObject):
    if message.from_user.id not in ALLOWED_TELEGRAM_IDS:
        await message.answer("У вас немає доступу.")
        return

    if not command.args or not command.args.strip().isdigit():
        await message.answer("Вкажіть номер заявки: /ticket <номер>")
        return

    ticket_id = int(command.args.strip())
    ticket = await fetch_ticket(ticket_id)

    if ticket is None:
        await message.answer(f"Заявку #{ticket_id} не знайдено.")
        return

    await message.answer(format_ticket_detail(ticket), parse_mode="HTML")


@router.message(Command("tickets"))
async def cmd_tickets(message: Message):
    if message.from_user.id not in ALLOWED_TELEGRAM_IDS:
        await message.answer("У вас немає доступу.")
        return

    await message.answer(
        "📋 <b>Оберіть категорію заявок:</b>",
        reply_markup=build_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("list:"))
async def on_list_by_status(callback: CallbackQuery):
    if callback.from_user.id not in ALLOWED_TELEGRAM_IDS:
        await callback.answer("У вас немає доступу.", show_alert=True)
        return

    status = int(callback.data.split(":", 1)[1])
    tickets = await fetch_tickets(status=status)

    if tickets is None:
        await callback.answer("Помилка при отриманні заявок.", show_alert=True)
        return

    icon = STATUS_ICONS.get(status, "📋")
    name = STATUS_NAMES.get(status, "Невідомо")
    title = f"{icon} <b>Заявки зі статусом: {name}</b>"

    await callback.message.answer(format_ticket_list(tickets, title), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "my_tickets")
async def on_my_tickets(callback: CallbackQuery):
    if callback.from_user.id not in ALLOWED_TELEGRAM_IDS:
        await callback.answer("У вас немає доступу.", show_alert=True)
        return

    user_id = str(callback.from_user.id)
    tickets = await fetch_tickets(assignee_id=user_id)

    if tickets is None:
        await callback.answer("Помилка при отриманні заявок.", show_alert=True)
        return

    title = f"📂 <b>Мої заявки ({callback.from_user.full_name})</b>"

    await callback.message.answer(format_ticket_list(tickets, title), parse_mode="HTML")
    await callback.answer()


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
