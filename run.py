from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from decouple import config
import asyncio
# Импорт и подключение роутера
from app.google.google import setup_google_sheet_update
from app.handlers import router

from app.database.models import get_session, init_db

# Инициализация бота и диспетчера
bot = Bot(token=config('TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.include_router(router)

async def on_startup(dispatcher: Dispatcher):
    await init_db()

# Запуск бота
async def main():
    await on_startup(dp)
    await setup_google_sheet_update(get_session)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())