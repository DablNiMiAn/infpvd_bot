from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_event_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Буду", callback_data=f"join_{event_id}"),
            InlineKeyboardButton(text="Не буду", callback_data=f"decline_{event_id}"),
        ],
        [InlineKeyboardButton(text="Пока не знаю", callback_data=f"maybe_{event_id}")]
    ])

def get_cancel_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отменить", callback_data=f"cancel_{event_id}")]
    ])
def get_leader_approval_keyboard(activist_id: int, event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Отправить", callback_data=f"approve_{activist_id}_{event_id}"),
            InlineKeyboardButton(text="Не отправлять", callback_data=f"reject_{activist_id}_{event_id}"),
        ]
    ])
