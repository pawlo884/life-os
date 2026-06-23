from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.reading_log import ReadingLog
from app.schemas.book import BookRead, ReadingSessionResult

BOOK_STATUSES = ("READING", "COMPLETED", "PAUSED", "QUEUED")
LOOKBACK_DAYS = 14


def _book_to_read(book: Book, avg_pages: float | None = None, eta: date | None = None) -> BookRead:
    remaining = max(book.total_pages - book.current_page, 0)
    percent = round((book.current_page / book.total_pages) * 100, 1) if book.total_pages else 0.0
    return BookRead(
        id=book.id,
        title=book.title,
        author=book.author,
        total_pages=book.total_pages,
        current_page=book.current_page,
        status=book.status,
        is_active=book.is_active,
        cover_url=book.cover_url,
        completion_percent=percent,
        remaining_pages=remaining,
        avg_pages_per_day=avg_pages,
        estimated_completion_date=eta,
    )


async def _avg_pages_for_book(db: AsyncSession, book_id: int) -> float | None:
    since = date.today() - timedelta(days=LOOKBACK_DAYS)
    result = await db.execute(
        select(func.coalesce(func.sum(ReadingLog.pages_read), 0), func.count(func.distinct(ReadingLog.log_date)))
        .where(ReadingLog.book_id == book_id, ReadingLog.log_date >= since)
    )
    total_pages, active_days = result.one()
    if not active_days:
        return None
    return round(total_pages / active_days, 1)


async def _eta_for_book(db: AsyncSession, book: Book) -> date | None:
    avg = await _avg_pages_for_book(db, book.id)
    if not avg:
        return None
    remaining = max(book.total_pages - book.current_page, 0)
    if remaining == 0:
        return date.today()
    days_left = int(remaining / avg)
    return date.today() + timedelta(days=days_left)


async def enrich_book(db: AsyncSession, book: Book) -> BookRead:
    avg = await _avg_pages_for_book(db, book.id)
    eta = await _eta_for_book(db, book) if avg else None
    return _book_to_read(book, avg, eta)


async def get_active_book(db: AsyncSession) -> Book | None:
    result = await db.execute(select(Book).where(Book.is_active.is_(True)).limit(1))
    return result.scalar_one_or_none()


async def resolve_book(db: AsyncSession, book_id: int | None, title: str | None) -> Book:
    if book_id:
        book = await db.get(Book, book_id)
        if not book:
            raise ValueError("Book not found")
        return book

    if title:
        result = await db.execute(select(Book).where(Book.title.ilike(f"%{title}%")).limit(1))
        book = result.scalar_one_or_none()
        if book:
            return book
        raise ValueError(f'No book matching "{title}"')

    book = await get_active_book(db)
    if book:
        return book

    result = await db.execute(
        select(Book).where(Book.status == "READING").order_by(Book.is_active.desc(), Book.id.desc()).limit(1)
    )
    book = result.scalar_one_or_none()
    if not book:
        raise ValueError("No active book. Add a book or set one as active first.")
    return book


async def set_active_book(db: AsyncSession, book_id: int) -> Book:
    book = await db.get(Book, book_id)
    if not book:
        raise ValueError("Book not found")

    result = await db.execute(select(Book).where(Book.is_active.is_(True)))
    for other in result.scalars().all():
        other.is_active = False

    book.is_active = True
    if book.status == "QUEUED":
        book.status = "READING"
    await db.commit()
    await db.refresh(book)
    return book


async def log_reading_session(
    db: AsyncSession,
    current_page: int,
    book_id: int | None = None,
    title: str | None = None,
    log_date: date | None = None,
    note: str | None = None,
) -> ReadingSessionResult:
    book = await resolve_book(db, book_id, title)
    session_date = log_date or date.today()

    if current_page > book.total_pages:
        raise ValueError(f"Current page cannot exceed total pages ({book.total_pages}).")
    if current_page < book.current_page:
        raise ValueError(
            f"Current page cannot be less than already logged progress ({book.current_page})."
        )

    pages_logged = current_page - book.current_page
    book.current_page = current_page
    if book.current_page >= book.total_pages:
        book.status = "COMPLETED"
        book.is_active = False

    if pages_logged > 0:
        db.add(
            ReadingLog(
                book_id=book.id,
                pages_read=pages_logged,
                log_date=session_date,
                note=note,
            )
        )
    await db.commit()
    await db.refresh(book)
    return ReadingSessionResult(
        book=await enrich_book(db, book),
        pages_logged=pages_logged,
        current_page=book.current_page,
        log_date=session_date,
    )
