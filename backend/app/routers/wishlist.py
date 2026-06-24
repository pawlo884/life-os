from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.book import Book
from app.models.wishlist_book import WishlistBook
from app.schemas.book import BookRead
from app.schemas.wishlist_book import (
    WishlistBookCreate,
    WishlistBookRead,
    WishlistBookUpdate,
    WishlistMoveToShelf,
)
from app.services.books import enrich_book

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.get("", response_model=list[WishlistBookRead])
async def list_wishlist(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WishlistBook).order_by(WishlistBook.id.desc()))
    return result.scalars().all()


@router.post("", response_model=WishlistBookRead, status_code=201)
async def create_wishlist_item(payload: WishlistBookCreate, db: AsyncSession = Depends(get_db)):
    item = WishlistBook(**payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/{item_id}", response_model=WishlistBookRead)
async def get_wishlist_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(WishlistBook, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Wishlist item not found")
    return item


@router.patch("/{item_id}", response_model=WishlistBookRead)
async def update_wishlist_item(
    item_id: int,
    payload: WishlistBookUpdate,
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(WishlistBook, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Wishlist item not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_wishlist_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(WishlistBook, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Wishlist item not found")
    await db.delete(item)
    await db.commit()


@router.post("/{item_id}/move-to-shelf", response_model=BookRead, status_code=201)
async def move_wishlist_to_shelf(
    item_id: int,
    payload: WishlistMoveToShelf,
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(WishlistBook, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Wishlist item not found")

    total_pages = payload.total_pages or item.total_pages
    if not total_pages:
        raise HTTPException(
            status_code=400,
            detail="total_pages is required — set it on the wishlist item or in the request body",
        )

    if payload.is_active:
        active = await db.execute(select(Book).where(Book.is_active.is_(True)))
        for book in active.scalars().all():
            book.is_active = False

    book = Book(
        title=item.title,
        author=item.author,
        total_pages=total_pages,
        current_page=0,
        status=payload.status if not payload.is_active else "READING",
        is_active=payload.is_active,
        cover_url=item.cover_url,
    )
    db.add(book)
    await db.delete(item)
    await db.commit()
    await db.refresh(book)
    return await enrich_book(db, book)
