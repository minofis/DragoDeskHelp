import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
)
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

# Маппинг Telegram ID -> юзернейм
USER_NAMES: dict[int, str] = {
    568312173: "@minofisss",
    852755803: "@Beneckto",
}


def get_user_display_name(user_id_str: str | None) -> str:
    """Возвращает читаемое имя пользователя по его ID."""
    if not user_id_str:
        return "Не призначено"
    try:
        uid = int(user_id_str)
        return USER_NAMES.get(uid, f"ID {user_id_str}")
    except ValueError:
        return user_id_str


# Persistent keyboard (кнопка под полем ввода)
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📋 Меню")]],
    resize_keyboard=True,
)

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
    assignee = get_user_display_name(t.get("assigneeId"))
    return (
        f"📋 <b>Заявка #{t['id']}</b>\n\n"
        f"🏠 <b>Аудиторія:</b> {t['roomNumber']}\n"
        f"👤 <b>Заявник:</b> {t['authorName']}\n"
        f"📝 <b>Опис:</b> {t['description']}\n"
        f"📊 <b>Статус:</b> {status_text}\n"
        f"🧑‍🔧 <b>Виконавець:</b> {assignee}\n"
        f"📅 <b>Створено:</b> {t['createdAt']}"
    )


def build_ticket_detail_keyboard(ticket: dict, user_id: int) -> InlineKeyboardMarkup | None:
    """Строит inline-кнопки для детальной заявки (закрытие/выполнение)."""
    assignee_id = ticket.get("assigneeId")
    status = ticket.get("status")
    buttons = []

    # Исполнитель может отметить как выполнено (status 1 -> 2)
    if assignee_id == str(user_id) and status == 1:
        buttons.append([
            InlineKeyboardButton(text="✅ Виконано", callback_data=f"done:{ticket['id']}"),
            InlineKeyboardButton(text="🔒 Закрити", callback_data=f"close:{ticket['id']}"),
        ])
    # Исполнитель может закрыть выполненную заявку (status 2 -> 3)
    elif assignee_id == str(user_id) and status == 2:
        buttons.append([
            InlineKeyboardButton(text="🔒 Закрити", callback_data=f"close:{ticket['id']}"),
        ])

    buttons.append([InlineKeyboardButton(text="« Назад до меню", callback_data="menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_ticket_list(tickets: list[dict], title: str) -> tuple[str, InlineKeyboardMarkup]:
    """Форматирует список заявок и возвращает текст + inline-кнопки для каждой заявки."""
    if not tickets:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад до меню", callback_data="menu")],
        ])
        return f"{title}\n\nЗаявок не знайдено.", keyboard

    lines = [title, ""]
    for t in tickets:
        status_text = t.get("statusText", "?")
        lines.append(
            f"• <b>#{t['id']}</b> | 🏠 {t['roomNumber']} | {status_text}\n"
            f"  {t['description'][:80]}"
        )
    lines.append(f"\nВсього: {len(tickets)}")

    # Кнопки для быстрого открытия каждой заявки
    buttons = []
    for t in tickets:
        buttons.append([InlineKeyboardButton(
            text=f"#{t['id']} — {t['roomNumber']}",
            callback_data=f"ticket:{t['id']}",
        )])
    buttons.append([InlineKeyboardButton(text="« Назад до меню", callback_data="menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    return "\n".join(lines), keyboard


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
    # Отправляем persistent keyboard (кнопка внизу)
    await message.answer(
        "👋 <b>ADHD HelpDesk Бот</b>\n\n"
        "Натисніть кнопку <b>📋 Меню</b> нижче для роботи із заявками.",
        reply_markup=main_keyboard,
        parse_mode="HTML",
    )
    # Отправляем inline-меню
    await message.answer(
        "📋 <b>Оберіть категорію заявок:</b>",
        reply_markup=build_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(F.text == "📋 Меню")
async def on_menu_button(message: Message):
    """Обработчик persistent кнопки «Меню»."""
    if message.from_user.id not in ALLOWED_TELEGRAM_IDS:
        await message.answer("У вас немає доступу.")
        return
    await message.answer(
        "📋 <b>Оберіть категорію заявок:</b>",
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

    keyboard = build_ticket_detail_keyboard(ticket, message.from_user.id)
    await message.answer(format_ticket_detail(ticket), reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "menu")
async def on_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    if callback.from_user.id not in ALLOWED_TELEGRAM_IDS:
        await callback.answer("У вас немає доступу.", show_alert=True)
        return
    await callback.message.answer(
        "📋 <b>Оберіть категорію заявок:</b>",
        reply_markup=build_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


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

    text, keyboard = format_ticket_list(tickets, title)
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
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

    text, keyboard = format_ticket_list(tickets, title)
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("ticket:"))
async def on_ticket_detail(callback: CallbackQuery):
    """Показывает детали заявки по нажатию inline-кнопки из списка."""
    if callback.from_user.id not in ALLOWED_TELEGRAM_IDS:
        await callback.answer("У вас немає доступу.", show_alert=True)
        return

    ticket_id = int(callback.data.split(":", 1)[1])
    ticket = await fetch_ticket(ticket_id)

    if ticket is None:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    keyboard = build_ticket_detail_keyboard(ticket, callback.from_user.id)
    await callback.message.answer(
        format_ticket_detail(ticket),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("done:"))
async def on_done(callback: CallbackQuery):
    """Исполнитель отмечает заявку как выполненную (status 1 -> 2)."""
    user_id = callback.from_user.id
    if user_id not in ALLOWED_TELEGRAM_IDS:
        await callback.answer("У вас немає доступу.", show_alert=True)
        return

    ticket_id = callback.data.split(":", 1)[1]
    success = await update_ticket_status(ticket_id, 2)
    if success:
        username = USER_NAMES.get(user_id, str(user_id))
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"✅ Заявку <b>#{ticket_id}</b> виконано ({username})",
            parse_mode="HTML",
        )
        await callback.answer("Заявку позначено як виконану!", show_alert=True)
    else:
        await callback.answer("Помилка при оновленні статусу.", show_alert=True)


@router.callback_query(F.data.startswith("close:"))
async def on_close(callback: CallbackQuery):
    """Исполнитель закрывает свою заявку (-> status 3)."""
    user_id = callback.from_user.id
    if user_id not in ALLOWED_TELEGRAM_IDS:
        await callback.answer("У вас немає доступу.", show_alert=True)
        return

    ticket_id = callback.data.split(":", 1)[1]
    success = await update_ticket_status(ticket_id, 3)
    if success:
        username = USER_NAMES.get(user_id, str(user_id))
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"🔒 Заявку <b>#{ticket_id}</b> закрито ({username})",
            parse_mode="HTML",
        )
        await callback.answer("Заявку закрито!", show_alert=True)
    else:
        await callback.answer("Помилка при оновленні статусу.", show_alert=True)


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
