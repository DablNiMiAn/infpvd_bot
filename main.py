import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import BOT_TOKEN, ADMIN_ID
from models import Event, User, events, users
from keyboards import get_event_keyboard, get_cancel_keyboard

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния для FSM
class EventCreationStates(StatesGroup):
    awaiting_event_name = State()
    awaiting_event_date = State()
    awaiting_event_time = State()
    awaiting_event_description = State()
    awaiting_event_required_people = State()
    awaiting_decline_reason = State()

# Регистрация пользователя
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        if user_id == ADMIN_ID:
            users[user_id] = User(id=user_id, role="leader", name=message.from_user.full_name)
            await message.answer(
                "Вы зарегистрированы как **руководитель**!\n\n"
                "Отправьте команду /help, чтобы увидеть список доступных команд."
            )
        else:
            users[user_id] = User(id=user_id, role="activist", name=message.from_user.full_name)
            await message.answer("Вы зарегистрированы как активист!")
    else:
        if user_id == ADMIN_ID:
            await message.answer(
                "Вы уже зарегистрированы как руководитель.\n\n"
                "Отправьте команду /help, чтобы увидеть список доступных команд."
            )
        else:
            await message.answer("Вы уже зарегистрированы!")

@dp.message(Command("activists"))
async def show_activists(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для просмотра списка активистов!")
        return

    if not users:
        await message.answer("Список активистов пуст.")
        return

    activists_list = []
    for user_id, user in users.items():
        if user.role == "activist":
            username = f"@{user.name}" if user.name.startswith("@") else f"@{user.name.replace(' ', '_')}"
            activists_list.append(f"{username} (ID: {user_id})")

    if not activists_list:
        await message.answer("Активистов нет.")
    else:
        await message.answer("Список активистов:\n" + "\n".join(activists_list))

# Создание мероприятия (только для руководителя)
@dp.message(Command("create_event"))
async def create_event(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для создания мероприятий!")
        return
    await message.answer("Введите название мероприятия:")
    await state.set_state(EventCreationStates.awaiting_event_name)

# Обработка ввода данных о мероприятии
@dp.message(EventCreationStates.awaiting_event_name)
async def process_event_name(message: Message, state: FSMContext):
    await state.update_data(event_name=message.text)
    await message.answer("Введите дату мероприятия (ДД.ММ.ГГГГ):")
    await state.set_state(EventCreationStates.awaiting_event_date)

@dp.message(EventCreationStates.awaiting_event_date)
async def process_event_date(message: Message, state: FSMContext):
    await state.update_data(event_date=message.text)
    await message.answer("Введите время мероприятия (ЧЧ:ММ):")
    await state.set_state(EventCreationStates.awaiting_event_time)

@dp.message(EventCreationStates.awaiting_event_time)
async def process_event_time(message: Message, state: FSMContext):
    await state.update_data(event_time=message.text)
    await message.answer("Введите описание мероприятия:")
    await state.set_state(EventCreationStates.awaiting_event_description)

@dp.message(EventCreationStates.awaiting_event_description)
async def process_event_description(message: Message, state: FSMContext):
    await state.update_data(event_description=message.text)
    await message.answer("Сколько человек нужно?")
    await state.set_state(EventCreationStates.awaiting_event_required_people)

@dp.message(EventCreationStates.awaiting_event_required_people)
async def process_event_required_people(message: Message, state: FSMContext):
    user_data = await state.get_data()
    event_id = len(events) + 1
    events[event_id] = Event(
        id=event_id,
        name=user_data["event_name"],
        date=user_data["event_date"],
        time=user_data["event_time"],
        description=user_data["event_description"],
        required_people=int(message.text),
        participants=[],
        approved_participants=[]
    )
    await state.clear()
    await message.answer("Мероприятие создано!")

    # Отправляем уведомление всем активистам
    for user in users.values():
        if user.role == "activist":
            await bot.send_message(
                user.id,
                f"Новое мероприятие: {user_data['event_name']}\n"
                f"Дата: {user_data['event_date']}\n"
                f"Время: {user_data['event_time']}\n"
                f"Описание: {user_data['event_description']}\n"
                f"Требуется участников: {message.text}",
                reply_markup=get_event_keyboard(event_id)
            )

# Обработка ответов активистов
@dp.callback_query(F.data.startswith("join_"))
async def handle_join(callback: CallbackQuery):
    user_id = callback.from_user.id
    event_id = int(callback.data.split("_")[1])
    event = events[event_id]

    if user_id not in event.participants:
        event.participants.append(user_id)
        username = callback.from_user.username or callback.from_user.full_name
        await bot.send_message(
            ADMIN_ID,
            f"Активист @{username} хочет участвовать в мероприятии {event.name}.\n"
            f"Подтвердите участие:",
            reply_markup=get_leader_approval_keyboard(user_id, event_id)
        )
        await callback.message.edit_text(
            f"Вы записаны на мероприятие {event.name}!\n"
            f"Дата: {event.date}\n"
            f"Время: {event.time}\n"
            f"Описание: {event.description}\n\n"
            f"Ожидайте подтверждения от руководителя."
        )
    else:
        await callback.answer("Вы уже записаны на это мероприятие!")

@dp.callback_query(F.data.startswith(("approve_", "reject_")))
async def handle_leader_decision(callback: CallbackQuery):
    data = callback.data.split("_")
    activist_id = int(data[1])
    event_id = int(data[2])
    event = events[event_id]

    if data[0] == "approve":
        if activist_id not in event.approved_participants:
            event.approved_participants.append(activist_id)
            username = (await bot.get_chat(activist_id)).username or (await bot.get_chat(activist_id)).full_name
            await bot.send_message(
                activist_id,
                f"Руководитель подтвердил ваше участие в мероприятии {event.name}!"
            )
            await callback.answer(f"Активист @{username} подтверждён.")

            # Проверяем, набралось ли нужное количество участников
            if len(event.approved_participants) >= event.required_people:
                await notify_rejected_participants(event)
        else:
            await callback.answer("Этот активист уже подтверждён.")
    elif data[0] == "reject":
        username = (await bot.get_chat(activist_id)).username or (await bot.get_chat(activist_id)).full_name
        await bot.send_message(
            activist_id,
            f"К сожалению, вас не выбрали на мероприятие {event.name}."
        )
        await callback.answer(f"Активист @{username} отклонён.")

async def notify_rejected_participants(event: Event):
    for participant in event.participants:
        if participant not in event.approved_participants:
            username = (await bot.get_chat(participant)).username or (await bot.get_chat(participant)).full_name
            await bot.send_message(
                participant,
                f"К сожалению, на мероприятие {event.name} выбрано достаточно участников.\n"
                f"В следующий раз вам обязательно повезёт!"
            )

@dp.message(Command("help"))
async def send_help(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Эта команда доступна только руководителю.")
        return

    help_text = """
📌 Доступные команды для руководителя:

/create_event — Создать новое мероприятие.
/activists — Посмотреть список всех активистов.
/help — Показать это сообщение с подсказками.

📌 Как создать мероприятие:
1. Отправьте команду /create_event.
2. Следуйте инструкциям бота, чтобы ввести название, дату, время, описание и количество участников.
3. После создания мероприятия все активисты получат уведомление.

📌 Как посмотреть список активистов:
Отправьте команду /activists.
    """
    await message.answer(help_text)


@dp.callback_query(F.data.startswith("decline_"))
async def handle_decline(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    event_id = int(callback.data.split("_")[1])
    await state.update_data(event_id=event_id)
    await callback.message.edit_text("Пожалуйста, напишите причину отказа:")
    await state.set_state(EventCreationStates.awaiting_decline_reason)

@dp.callback_query(F.data.startswith("maybe_"))
async def handle_maybe(callback: CallbackQuery):
    user_id = callback.from_user.id
    event_id = int(callback.data.split("_")[1])
    await callback.message.edit_text("Напомним вам через 3 дня!")
    asyncio.create_task(send_reminder(user_id, event_id, 3))


# Обработка причины отказа
@dp.message(EventCreationStates.awaiting_decline_reason)
async def process_decline_reason(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    event_id = user_data["event_id"]
    event = events[event_id]
    username = message.from_user.username or message.from_user.full_name
    await bot.send_message(ADMIN_ID, f"Активист @{username} отказался от {event.name}. Причина: {message.text}")
    await message.answer("Спасибо за ответ!")
    await state.clear()


# Напоминание через 3 дня
async def send_reminder(user_id: int, event_id: int, days: int):
    await asyncio.sleep(days * 86400)
    event = events[event_id]
    await bot.send_message(
        user_id,
        f"Напоминаем о мероприятии: {event.name}\n"
        f"Дата: {event.date}\n"
        f"Время: {event.time}\n"
        f"Описание: {event.description}",
        reply_markup=get_event_keyboard(event_id)
    )

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

