from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

start_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Стать участником", callback_data="become_participant")]
])

edit_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Заполнить заново", callback_data="edit_info")]
])

def get_programs_keyboard(selected_programs=None):
    if selected_programs is None:
        selected_programs = []
    
    programs = [
        "Не являюсь учеником",
        "Деньги под ключ",
        "Миллион на дропах",
        "Мастер инвестиций"
    ]
    keyboard = []
    for program in programs:
        text = f"✅ {program}" if program in selected_programs else program
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"program:{program}")])
    keyboard.append([InlineKeyboardButton(text="Подтвердить выбор", callback_data="confirm_programs")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Клавиатура для информации о капитанах
captain_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="О капитанах", callback_data="about_captains")]
])

yes_no_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Да"), KeyboardButton(text="Нет")]
], resize_keyboard=True)

# Клавиатура для решения стать капитаном
captain_decision_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Не интересно", callback_data="not_interested")],
    [InlineKeyboardButton(text="Стать лидером 🔥", callback_data="become_captain")]
])

# Клавиатура для запроса номера телефона
phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Отправить номер телефона", request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

final_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Стать лидером 🔥", callback_data="become_captain")]
])