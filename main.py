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
from models import Event, User
from keyboards import get_event_keyboard, get_cancel_keyboard, get_confirmation_keyboard, get_edit_profile_keyboard
from database import db

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


class RegistrationStates(StatesGroup):
    awaiting_full_name = State()
    awaiting_group = State()
    awaiting_username = State()


class EditProfileStates(StatesGroup):
    awaiting_edit_choice = State()
    awaiting_new_full_name = State()
    awaiting_new_group = State()
    awaiting_new_username = State()


class RemoveUserStates(StatesGroup):
    awaiting_user_id = State()


# Вспомогательная функция для проверки ФИО
def validate_full_name(full_name: str) -> bool:
    # Проверяем, что ФИО состоит из минимум 3 слов (Фамилия Имя Отчество)
    parts = full_name.strip().split()
    return len(parts) >= 3 and all(len(part) > 1 for part in parts)


# Регистрация пользователя
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # Проверяем, есть ли пользователь в БД
    user_data = await db.get_user(user_id)

    if not user_data:
        if user_id == ADMIN_ID:
            # Регистрируем руководителя
            await db.add_user(
                user_id=user_id,
                role="leader",
                name=message.from_user.full_name,
                full_name=message.from_user.full_name,
                username=message.from_user.username
            )
            await message.answer(
                "Вы зарегистрированы как **руководитель**!\n\n"
                "Отправьте команду /help, чтобы увидеть список доступных команд."
            )
        else:
            # Начинаем процесс регистрации активиста
            await message.answer(
                "Добро пожаловать! Для регистрации в системе необходимо заполнить информацию.\n\n"
                "Пожалуйста, введите ваше ФИО полностью (например: Иванов Иван Иванович):"
            )
            await state.set_state(RegistrationStates.awaiting_full_name)
            await state.update_data(user_id=user_id, name=message.from_user.full_name)
    else:
        if user_data['role'] == "leader":
            await message.answer(
                "Вы уже зарегистрированы как руководитель.\n\n"
                "Отправьте команду /help, чтобы увидеть список доступных команд."
            )
        else:
            profile_info = (
                f"Ваш профиль:\n"
                f"ФИО: {user_data['full_name'] or 'Не указано'}\n"
                f"Группа: {user_data['group'] or 'Не указана'}\n"
                f"Username: @{user_data['username'] or 'Не указан'}\n\n"
                f"Используйте /edit_profile чтобы изменить данные."
            )
            await message.answer(profile_info)


# Обработка ввода ФИО
@dp.message(RegistrationStates.awaiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    if not validate_full_name(message.text):
        await message.answer(
            "Пожалуйста, введите ФИО полностью (минимум 3 слова).\n"
            "Пример: Иванов Иван Иванович\n"
            "Попробуйте еще раз:"
        )
        return

    await state.update_data(full_name=message.text)
    await message.answer("Отлично! Теперь введите вашу учебную группу:")
    await state.set_state(RegistrationStates.awaiting_group)


# Обработка ввода группы
@dp.message(RegistrationStates.awaiting_group)
async def process_group(message: Message, state: FSMContext):
    await state.update_data(group=message.text)
    await message.answer("Теперь введите ваш username (например: @username или просто username):")
    await state.set_state(RegistrationStates.awaiting_username)


# Обработка ввода username
@dp.message(RegistrationStates.awaiting_username)
async def process_username(message: Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = user_data["user_id"]

    # Очищаем username от @ если он есть
    username = message.text.strip().lstrip('@')

    # Сохраняем пользователя в БД
    success = await db.add_user(
        user_id=user_id,
        role="activist",
        name=user_data["name"],
        full_name=user_data["full_name"],
        user_group=user_data["group"],
        username=username
    )

    if success:
        await state.clear()
        profile_info = (
            f"✅ Регистрация завершена!\n\n"
            f"Ваш профиль:\n"
            f"ФИО: {user_data['full_name']}\n"
            f"Группа: {user_data['group']}\n"
            f"Username: @{username}\n\n"
            f"Используйте /edit_profile чтобы изменить данные."
        )
        await message.answer(profile_info)
    else:
        await message.answer("Произошла ошибка при регистрации. Пожалуйста, попробуйте еще раз.")


# Команда для редактирования профиля
@dp.message(Command("edit_profile"))
async def edit_profile(message: Message):
    user_id = message.from_user.id

    # Проверяем, есть ли пользователь в БД
    user_data = await db.get_user(user_id)
    if not user_data:
        await message.answer("Сначала зарегистрируйтесь с помощью /start")
        return

    if user_data['role'] == "leader":
        await message.answer("Руководители не могут редактировать профиль через эту команду.")
        return

    keyboard = get_edit_profile_keyboard(user_id)
    await message.answer("Что вы хотите изменить?", reply_markup=keyboard)


# Обработка выбора редактирования
@dp.callback_query(F.data.startswith("edit_"))
async def handle_edit_choice(callback: CallbackQuery, state: FSMContext):
    data_parts = callback.data.split("_")
    action = data_parts[1]
    user_id = int(data_parts[2]) if len(data_parts) > 2 else callback.from_user.id

    if action == "cancel":
        await callback.message.edit_text("Изменение профиля отменено.")
        return

    user_data = await db.get_user(user_id)
    if not user_data:
        await callback.answer("Пользователь не найден.")
        return

    if action == "full_name":
        await callback.message.edit_text(
            f"Текущее ФИО: {user_data['full_name']}\n"
            f"Введите новое ФИО (полностью, минимум 3 слова):"
        )
        await state.set_state(EditProfileStates.awaiting_new_full_name)
        await state.update_data(user_id=user_id, message_id=callback.message.message_id)

    elif action == "group":
        await callback.message.edit_text(
            f"Текущая группа: {user_data['group']}\n"
            f"Введите новую учебную группу:"
        )
        await state.set_state(EditProfileStates.awaiting_new_group)
        await state.update_data(user_id=user_id, message_id=callback.message.message_id)

    elif action == "username":
        await callback.message.edit_text(
            f"Текущий username: @{user_data['username'] or 'Не указан'}\n"
            f"Введите новый username (например: @username или просто username):"
        )
        await state.set_state(EditProfileStates.awaiting_new_username)
        await state.update_data(user_id=user_id, message_id=callback.message.message_id)


# Обработка нового ФИО
@dp.message(EditProfileStates.awaiting_new_full_name)
async def process_new_full_name(message: Message, state: FSMContext):
    if not validate_full_name(message.text):
        await message.answer(
            "Пожалуйста, введите ФИО полностью (минимум 3 слова).\n"
            "Пример: Иванов Иван Иванович\n"
            "Попробуйте еще раз:"
        )
        return

    user_data = await state.get_data()
    user_id = user_data["user_id"]

    success = await db.update_user(user_id, full_name=message.text)
    if success:
        await state.clear()
        await message.answer(f"✅ ФИО успешно изменено на: {message.text}")
    else:
        await message.answer("❌ Произошла ошибка при изменении ФИО.")


# Обработка новой группы
@dp.message(EditProfileStates.awaiting_new_group)
async def process_new_group(message: Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = user_data["user_id"]

    success = await db.update_user(user_id, user_group=message.text)
    if success:
        await state.clear()
        await message.answer(f"✅ Группа успешно изменена на: {message.text}")
    else:
        await message.answer("❌ Произошла ошибка при изменении группы.")


# Обработка нового username
@dp.message(EditProfileStates.awaiting_new_username)
async def process_new_username(message: Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = user_data["user_id"]

    # Очищаем username от @ если он есть
    username = message.text.strip().lstrip('@')

    success = await db.update_user(user_id, username=username)
    if success:
        await state.clear()
        await message.answer(f"✅ Username успешно изменен на: @{username}")
    else:
        await message.answer("❌ Произошла ошибка при изменении username.")


# Команда для удаления активиста (только для руководителя)
@dp.message(Command("remove_activist"))
async def remove_activist(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для удаления активистов!")
        return

    # Получаем список активистов из БД
    activists = await db.get_all_activists()

    if not activists:
        await message.answer("Список активистов пуст.")
        return

    activists_list = []
    for activist in activists:
        activists_list.append(f"ID: {activist['id']} | ФИО: {activist['full_name']} | Группа: {activist['group']}")

    activists_text = "Список активистов:\n" + "\n".join(activists_list)
    activists_text += "\n\nВведите ID активиста, которого хотите удалить:"

    await message.answer(activists_text)
    await state.set_state(RemoveUserStates.awaiting_user_id)


# Обработка ввода ID для удаления
@dp.message(RemoveUserStates.awaiting_user_id)
async def process_remove_user(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)

        # Проверяем, существует ли пользователь
        user_data = await db.get_user(user_id)
        if not user_data:
            await message.answer(f"Пользователь с ID {user_id} не найден.")
            await state.clear()
            return

        if user_data['role'] != "activist":
            await message.answer("Можно удалять только активистов!")
            await state.clear()
            return

        # Удаляем пользователя из всех мероприятий
        events = await db.get_all_events()
        for event in events:
            if user_id in event['participants']:
                event['participants'].remove(user_id)
                await db.update_event_participants(event['id'], event['participants'])

        # Удаляем пользователя из БД
        success = await db.delete_user(user_id)
        if success:
            await message.answer(
                f"✅ Активист удален:\n"
                f"ФИО: {user_data['full_name']}\n"
                f"Группа: {user_data['group']}\n"
                f"Username: @{user_data['username']}"
            )
        else:
            await message.answer("❌ Произошла ошибка при удалении активиста.")

        await state.clear()

    except ValueError:
        await message.answer("Пожалуйста, введите корректный числовой ID.")
        return


# Обновленная команда /activists для руководителя
@dp.message(Command("activists"))
async def show_activists(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для просмотра списка активистов!")
        return

    # Получаем всех активистов из БД
    activists = await db.get_all_activists()

    if not activists:
        await message.answer("Активистов нет.")
        return

    activists_list = []
    for activist in activists:
        activists_list.append(
            f"ID: {activist['id']}\n"
            f"ФИО: {activist['full_name'] or 'Не указано'}\n"
            f"Группа: {activist['group'] or 'Не указана'}\n"
            f"Username: @{activist['username'] or 'Не указан'}\n"
            f"Дата регистрации: {activist['created_at'][:10] if activist['created_at'] else 'Неизвестно'}\n"
            f"{'-' * 30}"
        )

    text = "📋 Список активистов:\n\n" + "\n".join(activists_list)
    text += "\n\nДля удаления активиста используйте /remove_activist"

    # Разбиваем сообщение на части, если оно слишком длинное
    if len(text) > 4096:
        parts = []
        while len(text) > 4096:
            part = text[:4096]
            last_newline = part.rfind('\n')
            if last_newline != -1:
                parts.append(text[:last_newline])
                text = text[last_newline + 1:]
            else:
                parts.append(part)
                text = text[4096:]
        parts.append(text)

        for part in parts:
            await message.answer(part)
    else:
        await message.answer(text)


# Обработка "Смогу"
@dp.callback_query(F.data.startswith("join_"))
async def handle_join(callback: CallbackQuery):
    user_id = callback.from_user.id
    event_id = int(callback.data.split("_")[1])

    # Получаем мероприятие из БД
    event = await db.get_event(event_id)
    if not event:
        await callback.answer("Мероприятие не найдено!")
        return

    # Получаем пользователя из БД
    user_data = await db.get_user(user_id)
    if not user_data:
        await callback.answer("Сначала зарегистрируйтесь с помощью /start")
        return

    # Проверяем, не записан ли уже пользователь
    if user_id in event['participants']:
        await callback.answer("Вы уже записаны на это мероприятие!")
        return

    # Сохраняем ответ в БД
    await db.add_event_response(event_id, user_id, "pending")

    # Отправляем руководителю уведомление
    user_info = (
        f"✅ Активист сможет прийти на мероприятие:\n"
        f"Мероприятие: {event['name']}\n"
        f"ФИО: {user_data['full_name']}\n"
        f"Группа: {user_data['group']}\n"
        f"Username: @{user_data['username']}\n"
        f"ID: {user_id}\n\n"
        f"Подтвердите запись активиста:"
    )

    confirm_keyboard = get_confirmation_keyboard(event_id, user_id)
    await bot.send_message(ADMIN_ID, user_info, reply_markup=confirm_keyboard)

    # Сообщаем активисту, что его запрос отправлен руководителю
    await callback.message.edit_text(
        f"✅ Ваша заявка на участие отправлена руководителю!\n\n"
        f"Название: {event['name']}\n"
        f"Дата: {event['date']}\n"
        f"Время: {event['time']}\n\n"
        f"Ожидайте подтверждения от руководителя."
    )


# Обработка подтверждения от руководителя
@dp.callback_query(F.data.startswith("confirm_"))
async def handle_confirmation(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    event_id = int(data_parts[1])
    user_id = int(data_parts[2])

    # Получаем данные из БД
    event = await db.get_event(event_id)
    user_data = await db.get_user(user_id)

    if not event or not user_data:
        await callback.answer("Данные не найдены!")
        return

    # Добавляем активиста в список участников
    participants = event['participants']
    if user_id not in participants:
        participants.append(user_id)
        await db.update_event_participants(event_id, participants)

    # Обновляем статус ответа в БД
    await db.add_event_response(event_id, user_id, "confirmed")

    # Уведомляем руководителя
    await callback.message.edit_text(
        f"✅ Вы подтвердили запись активиста:\n"
        f"{user_data['full_name']} на мероприятие {event['name']}"
    )

    # Отправляем уведомление активисту
    try:
        await bot.send_message(
            user_id,
            f"✅ Ваша запись на мероприятие подтверждена руководителем!\n\n"
            f"Название: {event['name']}\n"
            f"Дата: {event['date']}\n"
            f"Время: {event['time']}\n"
            f"Описание: {event['description']}\n\n"
            f"Требуется участников: {event['required_people']}\n"
            f"Текущее количество: {len(participants)}"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление активисту: {e}")


# Обработка отклонения от руководителя
@dp.callback_query(F.data.startswith("reject_"))
async def handle_rejection(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    event_id = int(data_parts[1])
    user_id = int(data_parts[2])

    # Получаем данные из БД
    event = await db.get_event(event_id)
    user_data = await db.get_user(user_id)

    if not event or not user_data:
        await callback.answer("Данные не найдены!")
        return

    # Обновляем статус ответа в БД
    await db.add_event_response(event_id, user_id, "rejected")

    # Уведомляем руководителя
    await callback.message.edit_text(
        f"❌ Вы отклонили запись активиста:\n"
        f"{user_data['full_name']} на мероприятие {event['name']}"
    )

    # Отправляем уведомление активисту
    try:
        await bot.send_message(
            user_id,
            f"❌ К сожалению, ваша запись на мероприятие была отклонена руководителем.\n\n"
            f"Мероприятие: {event['name']}\n"
            f"Дата: {event['date']}\n\n"
            f"Вы можете выбрать другое мероприятие."
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление активисту: {e}")


# Обработка отказа с причиной
@dp.callback_query(F.data.startswith("decline_"))
async def handle_decline(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    event_id = int(callback.data.split("_")[1])

    # Проверяем, есть ли пользователь в БД
    user_data = await db.get_user(user_id)
    if not user_data:
        await callback.answer("Сначала зарегистрируйтесь с помощью /start")
        return

    await state.update_data(event_id=event_id, user_id=user_id)
    await callback.message.edit_text("Пожалуйста, напишите причину, почему не сможете прийти:")
    await state.set_state(EventCreationStates.awaiting_decline_reason)


# Обработка причины отказа
@dp.message(EventCreationStates.awaiting_decline_reason)
async def process_decline_reason(message: Message, state: FSMContext):
    user_data = await state.get_data()
    event_id = user_data["event_id"]
    user_id = user_data["user_id"]

    # Получаем данные из БД
    event = await db.get_event(event_id)
    user_data_db = await db.get_user(user_id)

    if not event or not user_data_db:
        await message.answer("Ошибка: данные не найдены!")
        await state.clear()
        return

    # Сохраняем ответ в БД
    await db.add_event_response(event_id, user_id, "declined", message.text)

    # Отправляем руководителю подробную информацию об отказе
    decline_info = (
        f"❌ Активист не сможет прийти на мероприятие:\n"
        f"Мероприятие: {event['name']}\n"
        f"ФИО: {user_data_db['full_name']}\n"
        f"Группа: {user_data_db['group']}\n"
        f"Username: @{user_data_db['username']}\n"
        f"ID: {user_id}\n"
        f"Причина: {message.text}"
    )
    await bot.send_message(ADMIN_ID, decline_info)

    await message.answer("Спасибо за ответ! Информация передана руководителю.")
    await state.clear()


# Обработка "Пока не знаю"
@dp.callback_query(F.data.startswith("maybe_"))
async def handle_maybe(callback: CallbackQuery):
    user_id = callback.from_user.id
    event_id = int(callback.data.split("_")[1])

    # Проверяем, есть ли пользователь в БД
    user_data = await db.get_user(user_id)
    if not user_data:
        await callback.answer("Сначала зарегистрируйтесь с помощью /start")
        return

    # Получаем мероприятие из БД
    event = await db.get_event(event_id)
    if not event:
        await callback.answer("Мероприятие не найдено!")
        return

    # Сохраняем ответ в БД
    await db.add_event_response(event_id, user_id, "maybe")

    # Уведомляем руководителя
    maybe_info = (
        f"⏳ Активист еще не определился:\n"
        f"Мероприятие: {event['name']}\n"
        f"ФИО: {user_data['full_name']}\n"
        f"Группа: {user_data['group']}\n"
        f"Username: @{user_data['username']}\n"
        f"ID: {user_id}"
    )
    await bot.send_message(ADMIN_ID, maybe_info)

    await callback.message.edit_text(
        "⏳ Вы отложили решение.\n"
        "Мы напомним вам через 3 дня!"
    )
    asyncio.create_task(send_reminder(user_id, event_id, 3))


# Напоминание через 3 дня
async def send_reminder(user_id: int, event_id: int, days: int):
    await asyncio.sleep(days * 86400)

    # Проверяем, существуют ли пользователь и мероприятие
    user_data = await db.get_user(user_id)
    event = await db.get_event(event_id)

    if not user_data or not event:
        return

    try:
        await bot.send_message(
            user_id,
            f"🔔 Напоминаем о мероприятии!\n\n"
            f"Название: {event['name']}\n"
            f"Дата: {event['date']}\n"
            f"Время: {event['time']}\n"
            f"Описание: {event['description']}\n\n"
            f"Пожалуйста, примите решение:",
            reply_markup=get_event_keyboard(event_id)
        )
    except Exception as e:
        print(f"Не удалось отправить напоминание пользователю {user_id}: {e}")


# Создание мероприятия
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

    # Сохраняем мероприятие в БД
    event_id = await db.add_event(
        name=user_data["event_name"],
        date=user_data["event_date"],
        time=user_data["event_time"],
        description=user_data["event_description"],
        required_people=int(message.text)
    )

    if event_id == -1:
        await message.answer("❌ Ошибка при создании мероприятия.")
        await state.clear()
        return

    await state.clear()
    await message.answer("✅ Мероприятие создано!")

    # Отправляем уведомление всем активистам
    activists = await db.get_all_activists()

    if not activists:
        await message.answer("⚠️ Нет активистов для отправки уведомлений.")
        return

    success_count = 0
    failed_count = 0

    for activist in activists:
        try:
            await bot.send_message(
                activist['id'],
                f"📢 Новое мероприятие!\n\n"
                f"Название: {user_data['event_name']}\n"
                f"Дата: {user_data['event_date']}\n"
                f"Время: {user_data['event_time']}\n"
                f"Описание: {user_data['event_description']}\n"
                f"Требуется участников: {message.text}",
                reply_markup=get_event_keyboard(event_id)
            )
            success_count += 1
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {activist['id']}: {e}")
            failed_count += 1

    await message.answer(
        f"✅ Уведомления отправлены:\n"
        f"Успешно: {success_count}\n"
        f"Не удалось: {failed_count}"
    )


# Команда /help
@dp.message(Command("help"))
async def send_help(message: Message):
    if message.from_user.id == ADMIN_ID:
        help_text = """
📌 Доступные команды для руководителя:

/create_event — Создать новое мероприятие.
/activists — Посмотреть список всех активистов с подробной информацией.
/remove_activist — Удалить активиста из системы.
/help — Показать это сообщение с подсказками.

📌 Как создать мероприятие:
1. Отправьте команду /create_event.
2. Следуйте инструкциям бота, чтобы ввести название, дату, время, описание и количество участников.
3. После создания мероприятия все активисты получат уведомление.

📌 Управление активистами:
• /activists — просмотр полного списка с ФИО, группой и username
• /remove_activist — удаление активиста по ID

📌 Подтверждение записей:
• При нажатии активистом "Смогу" вы получите уведомление
• Используйте кнопки ✔️ Подтвердить или ❌ Отклонить
        """
    else:
        help_text = """
📌 Доступные команды для активиста:

/edit_profile — Изменить данные профиля (ФИО, группа, username)
/help — Показать список команд

📌 Как работать с мероприятиями:
1. При создании мероприятия вы получите уведомление.
2. Используйте кнопки под сообщением:
   • "✔️ Смогу" — сообщить о возможности прийти (требует подтверждения руководителя)
   • "❌ Не смогу" — отказаться с указанием причины
   • "Пока не знаю" — отложить решение (напоминание через 3 дня)
3. После подтверждения руководителем вы получите уведомление.
        """

    await message.answer(help_text)


# Запуск бота
async def main():
    # Инициализируем базу данных
    await db.init_db()

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())