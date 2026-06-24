"""Populate the database with demo books and reading history."""

import asyncio
from datetime import date, timedelta

from sqlalchemy import func, select

from app.database import async_session
from app.models.book import Book
from app.models.reading_log import ReadingLog


async def seed() -> None:
    async with async_session() as db:
        existing = await db.execute(select(func.count(Book.id)))
        if (existing.scalar() or 0) > 0:
            print("Books already seeded — skipping.")
            return

        today = date.today()

        fluent = Book(
            title="Fluent Python",
            author="Luciano Ramalho",
            total_pages=800,
            current_page=0,
            status="READING",
            is_active=True,
        )
        ddia = Book(
            title="Designing Data-Intensive Applications",
            author="Martin Kleppmann",
            total_pages=616,
            current_page=0,
            status="QUEUED",
            is_active=False,
        )
        db.add_all([fluent, ddia])
        await db.flush()

        current_page = 0
        for days_ago in range(13, -1, -1):
            if days_ago % 2 == 0:
                pages = 25 + (days_ago % 4) * 5
                current_page += pages
                db.add(
                    ReadingLog(
                        book_id=fluent.id,
                        pages_read=pages,
                        log_date=today - timedelta(days=days_ago),
                    )
                )

        fluent.current_page = min(current_page, fluent.total_pages)
        await db.commit()
        print(f"Seeded 2 books with {current_page} pages logged on Fluent Python.")


if __name__ == "__main__":
    asyncio.run(seed())
