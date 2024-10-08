import types
from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ContentType, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import User, UserStatus
from app.database.models import get_session
from app.google.google import update_google_sheet
import app.keyboards as kb
import logging
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import update
import re
from .constants import start_message, character_captain, congratulation_prticipant, congratulation_captain
import csv
from pathlib import Path

# Путь к CSV файлу
CSV_PATH = Path(__file__).parent / 'database' / 'emails.csv'
CSV_PATH_LINKS = Path(__file__).parent / 'links.csv'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
router = Router()

def read_links_from_csv(file_path):
    logger.info('START READ CSV LINKS FILE')
    links_dict = {}
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=',')  # ожидаем разделитель ';'
        for row in reader:
            logger.info(f'{row} START WORKING')
            telegram_id = int(row['telegramId'])
            link = row['link'].strip()
            links_dict[telegram_id] = link
    return links_dict

def validate_name(name):
    # Простая проверка: имя должно содержать хотя бы два слова
    return len(name.split()) >= 2

def validate_phone(phone):
    # Регулярное выражение для проверки формата телефона
    pattern = r'^(\+?\d{1,4})?[-.\s]?\(?[0-9]{1,4}\)?[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}$'
    return re.match(pattern, phone) is not None

def validate_email(email):
    # Простая проверка email
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def read_emails_from_csv(file_path):
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        return set(email.strip().lower() for row in reader for email in row)
    
# Загрузим emails при запуске приложения
ALLOWED_EMAILS = read_emails_from_csv(CSV_PATH)

class UserState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_age = State()
    waiting_for_occupation = State()
    waiting_for_city = State()
    waiting_for_crypto_experience = State()
    waiting_for_programs = State()
    waiting_for_captain_motivation = State()

questions = [
    "Напишите полностью ваше ФИО 👇",
    "Напишите ваш номер телефона 👇",
    "Супер. Введите почту, с которой вы зарегистрировались в обучении.\n\nЭто поможет нам корректно распределить вас по группам обучения 👌",
    "Принято 👍\n\nЕще совсем немного вопросов🙂 Сколько вам лет? (Введите только цифру)",
    "Ваш род деятельности?",
    "В каком городе вы проживаете?",
    "Отлично. Напишите, есть ли у вас опыт работы с криптовалютой 👇",
    "Участвовали ли вы ранее в продуктах Азата Валеева? Если да, укажите в каких. (Вы можете выбрать несколько)\n\nПосле выбора нажмите на кнопку «Подтвердить выбор»",
    "Подробно опишите свою мотивацию стать Капитаном?"
]

state_order = [
    UserState.waiting_for_name,
    UserState.waiting_for_phone,
    UserState.waiting_for_email,
    UserState.waiting_for_age,
    UserState.waiting_for_occupation,
    UserState.waiting_for_city,
    UserState.waiting_for_crypto_experience,
    UserState.waiting_for_programs
]

async def check_user_data_completeness(user):
    required_fields = ['name', 'phone', 'email', 'age', 'occupation', 'city', 'crypto_experience', 'programs']
    for field in required_fields:
        value = getattr(user, field)
        if field == 'age':
            if not isinstance(value, int) or value <= 0:
                logger.info(f"Field {field} is not complete: {value}")
                return False
        elif field == 'programs':
            if not isinstance(value, list) or len(value) == 0:
                logger.info(f"Field {field} is not complete: {value}")
                return False
        else:
            if value is None or (isinstance(value, str) and value.strip() == ''):
                logger.info(f"Field {field} is not complete: {value}")
                return False
    return True

@router.message(F.text == '/start join')
async def cmd_start(message: Message, state: FSMContext):
    async for session in get_session():
        try:
            # Поиск пользователя в базе данных
            query = select(User).where(User.telegram_id == message.from_user.id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()

            if user:
                is_complete = await check_user_data_completeness(user)
                logger.info(f"User data completeness: {is_complete}")
                if is_complete:
                    await message.answer(
                        "Вы уже внесены в список участников! Ожидайте распределения!\n"
                        "Если вы хотите отредактировать свою информацию, перейдите в меню справа снизу. Там указана команда для обновления данных!"
                    )
                else:
                    await message.answer(
                        "Вы начали регистрацию, но не завершили ее. Перейдите в меню справа снизу. Там указана команда для обновления данных!"
                    )
                    await state.set_state(UserState.waiting_for_name)
            else:
                # Если пользователь не найден, создаем нового
                new_user = User(
                    telegram_id=message.from_user.id,
                    telegram=message.from_user.username,
                    status=UserStatus.student
                )
                session.add(new_user)
                await session.commit()

                # Запускаем опрос с первого шага
                await message.answer(start_message, reply_markup=kb.start_keyboard)
                await state.set_state(UserState.waiting_for_name)

        except Exception as e:
            logger.error(f"Error in cmd_start: {e}", exc_info=True)
            await session.rollback()
            await message.answer("Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.")
        finally:
            await session.close()
    

@router.callback_query(F.data == "become_participant")
async def process_callback_become_participant(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserState.waiting_for_name)
    await callback.message.edit_text("Отлично!🙂\nДавайте познакомимся\n\n" + questions[0])

async def save_to_db(session, telegram_id, data):
    try:
        # Проверяем, существует ли пользователь
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Если пользователь существует, обновляем данные
            stmt = update(User).where(User.telegram_id == telegram_id).values(**data)
            await session.execute(stmt)
        else:
            # Если пользователя нет, создаем нового
            stmt = insert(User).values(telegram_id=telegram_id, **data)
            await session.execute(stmt)

        await session.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving user data to DB: {e}", exc_info=True)
        await session.rollback()
        return False

@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext):
    await state.clear()  # Очищаем текущее состояние
    await state.set_state(UserState.waiting_for_name)
    await message.answer("Давайте обновим вашу информацию. " + questions[0])

@router.callback_query(F.data == "edit_info")
async def cmd_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()  # Очищаем текущее состояние
    await state.set_state(UserState.waiting_for_name)
    await callback.message.answer("Давайте обновим вашу информацию. " + questions[0])

@router.message(UserState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    if not validate_name(message.text):
        await message.answer("Пожалуйста, введите полное ФИО (имя и фамилию).")
        return
    await state.update_data(waiting_for_name=message.text)
    async for session in get_session():
        await save_to_db(session, message.from_user.id, {'name': message.text})
    await state.set_state(UserState.waiting_for_phone)
    await message.answer(f"Приятно познакомиться, {message.text.split()[1]} 🙌\n\n{questions[1]}", reply_markup=kb.phone_keyboard)

@router.message(UserState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text if message.content_type != ContentType.CONTACT else message.contact.phone_number
    if not validate_phone(phone):
        await message.answer("Пожалуйста, введите корректный номер телефона в формате: 79871011090, +79871011090, или +7 (987)101-10-90")
        return
    await state.update_data(waiting_for_phone=phone)
    async for session in get_session():
        await save_to_db(session, message.from_user.id, {'phone': phone})
    await state.set_state(UserState.waiting_for_email)
    await message.answer(questions[2], reply_markup=ReplyKeyboardRemove())

@router.message(UserState.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    if not validate_email(message.text):
        await message.answer("Пожалуйста, введите корректный email адрес.")
        return
    
    email = message.text.strip().lower()
    
    if email not in ALLOWED_EMAILS:
        await message.answer("Извините, но данный email не найден в списке участников. Пожалуйста, проверьте правильность введенного адреса или обратитесь к организаторам.")
        return
    
    await state.update_data(waiting_for_email=email)
    async for session in get_session():
        await save_to_db(session, message.from_user.id, {'email': email})
    await state.set_state(UserState.waiting_for_age)
    await message.answer(questions[3])

@router.message(UserState.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 10 or int(message.text) > 100:
        await message.answer("Пожалуйста, введите корректный возраст (число от 10 до 100).")
        return
    age = int(message.text)
    await state.update_data(waiting_for_age=age)
    async for session in get_session():
        await save_to_db(session, message.from_user.id, {'age': age})
    await state.set_state(UserState.waiting_for_occupation)
    await message.answer(questions[4])

@router.message(UserState.waiting_for_occupation)
async def process_occupation(message: Message, state: FSMContext):
    await state.update_data(waiting_for_occupation=message.text)
    async for session in get_session():
        await save_to_db(session, message.from_user.id, {'occupation': message.text})
    await state.set_state(UserState.waiting_for_city)
    await message.answer(questions[5])

@router.message(UserState.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(waiting_for_city=message.text)
    async for session in get_session():
        await save_to_db(session, message.from_user.id, {'city': message.text})
    await state.set_state(UserState.waiting_for_crypto_experience)
    await message.answer(questions[6])

@router.message(UserState.waiting_for_crypto_experience)
async def process_crypto_experience(message: Message, state: FSMContext):
    await state.update_data(waiting_for_crypto_experience=message.text)
    async for session in get_session():
        await save_to_db(session, message.from_user.id, {'crypto_experience': message.text})
    await state.set_state(UserState.waiting_for_programs)
    await message.answer(questions[7], reply_markup=kb.get_programs_keyboard())

@router.callback_query(F.data.startswith("program:"))
async def process_program_selection(callback: CallbackQuery, state: FSMContext):
    program = callback.data.split(":")[1]
    user_data = await state.get_data()
    programs = user_data.get('programs', [])
    
    if program in programs:
        programs.remove(program)
    else:
        programs.append(program)
    
    await state.update_data(programs=programs)  # Сохраняем обновленный список программ в состоянии
    
    async for session in get_session():
        await save_to_db(session, callback.from_user.id, {'programs': programs})
    
    await callback.answer(f"{'Выбрано' if program in programs else 'Отменено'}: {program}")
    await update_programs_message(callback.message, programs)

async def update_programs_message(message: Message, programs: list):
    text = "Выбранные программы:\n" + "\n".join(f"✅ {program}" for program in programs) if programs else "Программы не выбраны"
    await message.edit_text(text, reply_markup=kb.get_programs_keyboard(programs))

@router.callback_query(F.data == "confirm_programs")
async def confirm_programs(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    programs = user_data.get('programs', [])
    
    if not programs:
        await callback.answer("Вы не выбрали ни одной программы. Выберите хотя бы одну или 'Не являюсь участником'.", show_alert=True)
        return
    
    async for session in get_session():
        await save_to_db(session, callback.from_user.id, {'programs': programs})
    
    await state.set_state(UserState.waiting_for_captain_motivation)
    await callback.message.edit_text(congratulation_prticipant, reply_markup=kb.captain_keyboard)

@router.callback_query(F.data == "about_captains")
async def process_callback_about_captains(callback: CallbackQuery):
    await callback.message.edit_text(character_captain, reply_markup=kb.captain_decision_keyboard)

@router.callback_query(F.data == "become_captain")
async def process_callback_become_captain(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserState.waiting_for_captain_motivation)
    await callback.message.edit_text(questions[-1])

# Обновим функцию process_callback_not_interested для обновления существующей записи
@router.callback_query(F.data == "not_interested")
async def process_callback_not_interested(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    
    async for session in get_session():
        try:
            # Получаем существующего пользователя
            existing_user = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
            existing_user = existing_user.scalar_one_or_none()

            if existing_user:
                # Обновляем только предоставленные поля
                update_data = {}
                if 'waiting_for_name' in user_data:
                    update_data['name'] = user_data['waiting_for_name']
                if 'waiting_for_phone' in user_data:
                    update_data['phone'] = user_data['waiting_for_phone']
                if 'waiting_for_email' in user_data:
                    update_data['email'] = user_data['waiting_for_email']
                if 'waiting_for_occupation' in user_data:
                    update_data['occupation'] = user_data['waiting_for_occupation']
                if 'waiting_for_city' in user_data:
                    update_data['city'] = user_data['waiting_for_city']
                if 'waiting_for_crypto_experience' in user_data:
                    update_data['crypto_experience'] = user_data['waiting_for_crypto_experience']
                if 'programs' in user_data:
                    update_data['programs'] = user_data['programs']
                
                update_data['captain_motivation'] = "Не заинтересован"
                update_data['status'] = UserStatus.student

                if 'waiting_for_age' in user_data:
                    age = user_data['waiting_for_age']
                    if isinstance(age, int):
                        update_data['age'] = age
                    elif isinstance(age, str) and age.isdigit():
                        update_data['age'] = int(age)

                # Применяем обновления
                for key, value in update_data.items():
                    setattr(existing_user, key, value)

                await session.commit()
            else:
                logger.warning(f"User with telegram_id {callback.from_user.id} not found in database")

            await callback.message.edit_text(
                "Спасибо за ваш ответ. Вы всегда можете вернуться к выбору роли капитана позже.",
                reply_markup=kb.final_keyboard
            )
            
        except Exception as e:
            logger.error(f"Error updating user data: {e}", exc_info=True)
            await session.rollback()
        finally:
            await session.close()
    
    await state.clear()

@router.callback_query(F.data == "become_captain")
async def process_callback_become_captain(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserState.waiting_for_captain_motivation)
    await callback.message.edit_text(questions[-1])

# Обновим функцию process_captain_motivation для обновления существующей записи
@router.message(UserState.waiting_for_captain_motivation)
async def process_captain_motivation(message: Message, state: FSMContext):
    await state.update_data(captain_motivation=message.text)
    user_data = await state.get_data()
    logger.info(f"Updated state data: {user_data}")
    
    async for session in get_session():
        try:
            update_data = {
                'name': user_data.get('waiting_for_name'),
                'phone': user_data.get('waiting_for_phone'),
                'email': user_data.get('waiting_for_email'),
                'occupation': user_data.get('waiting_for_occupation'),
                'city': user_data.get('waiting_for_city'),
                'crypto_experience': user_data.get('waiting_for_crypto_experience'),
                'programs': user_data.get('programs', []),
                'captain_motivation': user_data.get('captain_motivation'),
                'status': UserStatus.captain
            }

            age = user_data.get('waiting_for_age')
            if age is not None:
                try:
                    update_data['age'] = int(age)
                except ValueError:
                    logger.warning(f"Invalid age value: {age}. Skipping age update.")

            stmt = update(User).where(User.telegram_id == message.from_user.id).values(**update_data)
            
            await session.execute(stmt)
            await session.commit()
            
            logger.info(f"User updated successfully")
            
            await message.answer(congratulation_captain)
        except Exception as e:
            logger.error(f"Error updating user in database: {e}", exc_info=True)
            await session.rollback()
            await message.answer("Произошла ошибка при сохранении данных. Пожалуйста, попробуйте еще раз позже.")
        finally:
            await session.close()
    
    await state.clear()
    logger.info("Finished process_captain_motivation")

@router.message(Command("update_sheet"))
async def cmd_update_sheet(message: Message):
    await message.answer("Начинаю обновление Google таблицы...")
    try:
        async for session in get_session():
            await update_google_sheet(session)
        await message.answer("Google таблица успешно обновлена.")
    except Exception as e:
        logger.error(f"Error updating Google Sheet: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обновлении Google таблицы.")

@router.message(Command('send_links'))
async def send_links_to_all_users(message: Message):
    try:
        # Загружаем данные из CSV
        links_data = read_links_from_csv(CSV_PATH_LINKS)

        # Проходим по каждому пользователю из CSV
        for telegram_id, link in links_data.items():
            try:
                # Отправляем сообщение пользователю с его ссылкой
                await message.bot.send_message(chat_id=telegram_id, text=f"Добрый день! Кажется вы все еще не вошли в свою \"Десятку\" 💫\n\nСкорее переходите по ссылке ниже, чтобы вступить в чат вашей команды:\n{link}")
                logger.info(f"Сообщение отправлено пользователю с ID {telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения пользователю {telegram_id}: {e}")

        await message.answer("Все сообщения были отправлены!")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщений: {e}")
        await message.answer("Произошла ошибка при отправке сообщений.")