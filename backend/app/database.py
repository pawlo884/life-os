from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

if not settings.database_url:
    raise RuntimeError(
        "DATABASE_URL is not set. Add your Supabase connection string to .env "
        "(Dashboard → Settings → Database → Connection string)."
    )

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=settings.database_connect_args,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
