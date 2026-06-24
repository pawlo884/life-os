from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.reading_log import ReadingLog


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_pages: Mapped[int] = mapped_column(Integer)
    current_page: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="READING")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    cover_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    reading_logs: Mapped[list["ReadingLog"]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
    )
