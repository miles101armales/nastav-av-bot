import gspread
from oauth2client.service_account import ServiceAccountCredentials
from app.database.models import User, UserStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

# Настройка аутентификации
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('app/google/nice-script-413614-cb7ad51ac23d.json', scope)
client = gspread.authorize(creds)

# URL вашей Google Таблицы
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1XtQDtT2boACxE_glBcH2MNWL0Rq2yyIgfDztzUqJ2yg/edit#gid=0'
sheet = client.open_by_url(SHEET_URL).sheet1

async def update_google_sheet(session: AsyncSession):
    # Получение всех пользователей из базы данных
    result = await session.execute(select(User))
    users = result.scalars().all()

    # Получение всех данных из таблицы
    all_values = sheet.get_all_values()
    headers = all_values[0]
    existing_data = {int(row[0]): row for row in all_values[1:] if row[0].isdigit()}

    # Подготовка данных для обновления и добавления
    rows_to_update = []
    rows_to_append = []

    for user in users:
        user_data = [
            user.telegram_id,
            user.name,
            user.phone,
            user.telegram,
            user.email,
            user.age,
            user.occupation,
            user.city,
            user.crypto_experience,
            ', '.join(user.programs) if isinstance(user.programs, list) else str(user.programs),
            user.captain_motivation,
            user.status.value,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]

        if user.telegram_id in existing_data:
            # Обновление существующей записи
            row_num = all_values.index(existing_data[user.telegram_id]) + 1
            rows_to_update.append({'row': row_num, 'values': user_data})
        else:
            # Добавление новой записи
            rows_to_append.append(user_data)

    # Обновление существующих записей
    for row in rows_to_update:
        sheet.update(f'A{row["row"]}:M{row["row"]}', [row['values']])

    # Добавление новых записей
    if rows_to_append:
        sheet.append_rows(rows_to_append)

    print(f"Updated {len(rows_to_update)} existing rows and added {len(rows_to_append)} new rows in Google Sheet.")

def start_scheduler(session_maker):
    scheduler = AsyncIOScheduler()
    
    async def scheduled_update():
        async for session in session_maker():
            try:
                await update_google_sheet(session)
            finally:
                await session.close()

    scheduler.add_job(
        scheduled_update,
        trigger=IntervalTrigger(hours=30),
        id='update_google_sheet',
        replace_existing=True
    )
    
    scheduler.start()

# Эту функцию нужно вызвать при запуске бота
async def setup_google_sheet_update(session_maker):
    start_scheduler(session_maker)