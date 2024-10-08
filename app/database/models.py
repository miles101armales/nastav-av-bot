from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import BigInteger, ARRAY, Integer, String, Enum, UniqueConstraint
from decouple import config
import enum

DATABASE_URL = 'postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}'.format(
    user=config('DB_USERNAME'),
    password=config('DB_PASSWORD'),
    host=config('DB_HOST'),
    port=config('DB_PORT'),
    name=config('DB_NAME')
)

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }
)

async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    async with async_session() as session:
        yield session

class Base(AsyncAttrs, DeclarativeBase):
	pass

class UserStatus(enum.Enum):
    student = 'ученик'
    captain = 'капитан'

class User(Base):
    __tablename__ = 'nastavnichestvo'
    __table_args__ = (UniqueConstraint('telegram_id', name='uq_telegram_id'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    telegram: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    occupation: Mapped[str] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    crypto_experience: Mapped[str] = mapped_column(String, nullable=True)
    programs: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    captain_motivation: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.student)
       