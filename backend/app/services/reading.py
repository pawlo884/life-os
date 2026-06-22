from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_progress import LearningProgress
from app.schemas.learning_progress import ReadingEstimate


async def estimate_book_completion(
    db: AsyncSession,
    pages_read: int,
    title: str | None = None,
    lookback_days: int = 14,
) -> ReadingEstimate:
    query = select(LearningProgress).where(LearningProgress.resource_type == "BOOK")
    if title:
        query = query.where(LearningProgress.title.ilike(f"%{title}%"))
    query = query.order_by(LearningProgress.id.desc()).limit(1)

    result = await db.execute(query)
    book = result.scalar_one_or_none()
    if not book:
        raise ValueError("No active book found. Add one via the API first.")

    book.completed_units += pages_read
    if book.total_units and book.completed_units >= book.total_units:
        book.completed_units = book.total_units
        book.status = "COMPLETED"

    await db.commit()
    await db.refresh(book)

    avg_pages = max(pages_read / 1, 1.0)
    remaining = max(book.total_units - book.completed_units, 0)
    days_left = int(remaining / avg_pages) if avg_pages > 0 else None
    estimated = date.today() + timedelta(days=days_left) if days_left is not None else None

    return ReadingEstimate(
        resource_id=book.id,
        title=book.title,
        pages_read=pages_read,
        remaining_pages=remaining,
        avg_pages_per_day=round(avg_pages, 1),
        estimated_completion_date=estimated,
    )
