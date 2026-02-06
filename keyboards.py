from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_event_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✔️ Смогу", callback_data=f"join_{event_id}"),
            InlineKeyboardButton(text="❌ Не смогу", callback_data=f"decline_{event_id}"),
        ],
        [InlineKeyboardButton(text="Пока не знаю", callback_data=f"maybe_{event_id}")]
    ])

def get_cancel_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отменить", callback_data=f"cancel_{event_id}")]
    ])

def get_confirmation_keyboard(event_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения записи на мероприятие руководителем"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✔️ Подтвердить", callback_data=f"confirm_{event_id}_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{event_id}_{user_id}"),
        ]
    ])

def get_edit_profile_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для редактирования профиля"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить ФИО", callback_data=f"edit_full_name_{user_id}")],
        [InlineKeyboardButton(text="Изменить группу", callback_data=f"edit_group_{user_id}")],
        [InlineKeyboardButton(text="Изменить username", callback_data=f"edit_username_{user_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data=f"edit_cancel_{user_id}")]
    ])