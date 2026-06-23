from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class BookBase(BaseModel):
    title: str = Field(max_length=255)
    author: str | None = Field(default=None, max_length=255)
    total_pages: int = Field(gt=0)
    current_page: int = Field(default=0, ge=0)
    status: str = "READING"
    cover_url: str | None = Field(default=None, max_length=512)


class BookCreate(BookBase):
    is_active: bool = False


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    author: str | None = None
    total_pages: int | None = Field(default=None, gt=0)
    current_page: int | None = Field(default=None, ge=0)
    status: str | None = None
    is_active: bool | None = None
    cover_url: str | None = Field(default=None, max_length=512)


class BookRead(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    completion_percent: float = 0.0
    remaining_pages: int = 0
    avg_pages_per_day: float | None = None
    estimated_completion_date: date | None = None


class ReadingLogCreate(BaseModel):
    current_page: int = Field(ge=0)
    book_id: int | None = None
    title: str | None = None
    log_date: date | None = None
    note: str | None = None


class ReadingLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    pages_read: int
    log_date: date
    note: str | None = None


class ReadingSessionResult(BaseModel):
    book: BookRead
    pages_logged: int
    current_page: int
    log_date: date


class ReadingOverview(BaseModel):
    pages_today: int
    pages_this_week: int
    active_book: BookRead | None
    books_reading: int
    books_completed: int
