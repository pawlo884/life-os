"""Create all SQLAlchemy tables in the database configured via DATABASE_URL."""

import asyncio

from sqlalchemy import text

import app.models  # noqa: F401 — register all models on Base.metadata
from app.database import Base, engine


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE books ADD COLUMN IF NOT EXISTS cover_url VARCHAR(512)"))
    print("Database schema ready.")


if __name__ == "__main__":
    asyncio.run(init_db())
