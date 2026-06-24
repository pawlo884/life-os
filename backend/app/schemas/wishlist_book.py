from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WishlistBookBase(BaseModel):
    title: str = Field(max_length=255)
    author: str | None = Field(default=None, max_length=255)
    note: str | None = None
    cover_url: str | None = Field(default=None, max_length=512)
    source_url: str | None = Field(default=None, max_length=512)
    total_pages: int | None = Field(default=None, gt=0)


class WishlistBookCreate(WishlistBookBase):
    pass


class WishlistBookUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    author: str | None = None
    note: str | None = None
    cover_url: str | None = Field(default=None, max_length=512)
    source_url: str | None = Field(default=None, max_length=512)
    total_pages: int | None = Field(default=None, gt=0)


class WishlistBookRead(WishlistBookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class WishlistMoveToShelf(BaseModel):
    total_pages: int | None = Field(default=None, gt=0)
    is_active: bool = False
    status: str = "QUEUED"
