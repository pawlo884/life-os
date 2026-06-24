from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.book import Book
from app.models.reading_log import ReadingLog
from app.schemas.book import (
    BookCreate,
    BookRead,
    BookUpdate,
    ReadingLogCreate,
    ReadingLogRead,
    ReadingOverview,
    ReadingSessionResult,
)
from app.schemas.book_enrichment import BookEnrichmentResult
from app.services.book_enrichment import enrich_book as enrich_book_details, format_enrich_error
from app.services.books import enrich_book, log_reading_session, set_active_book

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=list[BookRead])
async def list_books(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Book).order_by(Book.is_active.desc(), Book.id.desc()))
    books = result.scalars().all()
    return [await enrich_book(db, book) for book in books]


@router.post("", response_model=BookRead, status_code=201)
async def create_book(payload: BookCreate, db: AsyncSession = Depends(get_db)):
    if payload.current_page > payload.total_pages:
        raise HTTPException(status_code=400, detail="current_page cannot exceed total_pages")

    if payload.is_active:
        active = await db.execute(select(Book).where(Book.is_active.is_(True)))
        for book in active.scalars().all():
            book.is_active = False

    status = payload.status
    if payload.current_page >= payload.total_pages:
        status = "COMPLETED"
    elif payload.is_active:
        status = "READING"

    book = Book(
        title=payload.title,
        author=payload.author,
        total_pages=payload.total_pages,
        current_page=payload.current_page,
        status=status,
        is_active=payload.is_active,
        cover_url=payload.cover_url,
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return await enrich_book(db, book)


@router.get("/overview", response_model=ReadingOverview)
async def reading_overview(db: AsyncSession = Depends(get_db)):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    pages_today = await db.execute(
        select(func.coalesce(func.sum(ReadingLog.pages_read), 0)).where(ReadingLog.log_date == today)
    )
    pages_week = await db.execute(
        select(func.coalesce(func.sum(ReadingLog.pages_read), 0)).where(ReadingLog.log_date >= week_start)
    )
    reading_count = await db.execute(select(func.count(Book.id)).where(Book.status == "READING"))
    completed_count = await db.execute(select(func.count(Book.id)).where(Book.status == "COMPLETED"))

    active = await db.execute(select(Book).where(Book.is_active.is_(True)).limit(1))
    active_book = active.scalar_one_or_none()

    return ReadingOverview(
        pages_today=pages_today.scalar() or 0,
        pages_this_week=pages_week.scalar() or 0,
        active_book=await enrich_book(db, active_book) if active_book else None,
        books_reading=reading_count.scalar() or 0,
        books_completed=completed_count.scalar() or 0,
    )


@router.get("/heatmap")
async def reading_heatmap(days: int = Query(default=365, ge=30, le=730), db: AsyncSession = Depends(get_db)):
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(ReadingLog.log_date, func.sum(ReadingLog.pages_read))
        .where(ReadingLog.log_date >= since)
        .group_by(ReadingLog.log_date)
    )
    return {row[0].isoformat(): int(row[1]) for row in result.all()}


@router.post("/enrich", response_model=BookEnrichmentResult)
async def enrich_book_metadata(
    title: str | None = Form(None),
    author: str | None = Form(None),
    url: str | None = Form(None),
    language: str | None = Form(None),
    cover_only: str | None = Form(None),
    image: UploadFile | None = File(None),
):
    image_bytes = None
    image_mime = None
    if image and image.filename:
        image_bytes = await image.read()
        image_mime = image.content_type

    cover_only_flag = bool(cover_only and str(cover_only).lower() not in ("false", "0", ""))

    try:
        return await enrich_book_details(
            title=title.strip() if title else None,
            author=author.strip() if author else None,
            url=url.strip() if url else None,
            image_bytes=image_bytes,
            image_mime=image_mime,
            language=language.strip() if language else None,
            cover_only=cover_only_flag,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=format_enrich_error(exc)) from exc


@router.post("/read", response_model=ReadingSessionResult)
async def log_reading(payload: ReadingLogCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await log_reading_session(
            db,
            current_page=payload.current_page,
            book_id=payload.book_id,
            title=payload.title,
            log_date=payload.log_date,
            note=payload.note,
        )
    except ValueError as exc:
        detail = str(exc)
        not_found = detail in {"Book not found"} or detail.startswith("No book") or detail.startswith("No active book")
        raise HTTPException(status_code=404 if not_found else 400, detail=detail) from exc


@router.delete("/{book_id}", status_code=204)
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    was_active = book.is_active
    await db.execute(delete(ReadingLog).where(ReadingLog.book_id == book_id))
    await db.delete(book)
    await db.flush()

    if was_active:
        result = await db.execute(
            select(Book)
            .where(Book.status.in_(("READING", "QUEUED")))
            .order_by(Book.id.desc())
            .limit(1)
        )
        next_book = result.scalar_one_or_none()
        if next_book:
            next_book.is_active = True
            if next_book.status == "QUEUED":
                next_book.status = "READING"

    await db.commit()


@router.get("/{book_id}", response_model=BookRead)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return await enrich_book(db, book)


@router.patch("/{book_id}", response_model=BookRead)
async def update_book(book_id: int, payload: BookUpdate, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    data = payload.model_dump(exclude_unset=True)
    if "total_pages" in data and data["total_pages"] < book.current_page:
        raise HTTPException(
            status_code=400,
            detail="total_pages cannot be less than current_page",
        )

    if data.get("is_active"):
        active = await db.execute(select(Book).where(Book.is_active.is_(True), Book.id != book_id))
        for other in active.scalars().all():
            other.is_active = False

    for key, value in data.items():
        setattr(book, key, value)

    if book.current_page >= book.total_pages:
        book.current_page = book.total_pages
        book.status = "COMPLETED"
        book.is_active = False

    await db.commit()
    await db.refresh(book)
    return await enrich_book(db, book)


@router.post("/{book_id}/activate", response_model=BookRead)
async def activate_book(book_id: int, db: AsyncSession = Depends(get_db)):
    try:
        book = await set_active_book(db, book_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await enrich_book(db, book)


@router.get("/{book_id}/logs", response_model=list[ReadingLogRead])
async def list_reading_logs(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    result = await db.execute(
        select(ReadingLog).where(ReadingLog.book_id == book_id).order_by(ReadingLog.log_date.desc())
    )
    return result.scalars().all()
