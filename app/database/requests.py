from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from decouple import config
from .models import Base

DATABASE_URL = 'postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}'.format(
    user=config('DB_USERNAME'),
    password=config('DB_PASSWORD'),
    host=config('DB_HOST'),
    port=config('DB_PORT'),
    name=config('DB_NAME')
)

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    async with async_session() as session:
        yield session