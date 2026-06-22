from datetime import date

from sqlalchemy import Boolean, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FitnessLog(Base):
    __tablename__ = "fitness_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32))
    activity_type: Mapped[str] = mapped_column(String(32))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)
    streak_impact: Mapped[bool] = mapped_column(Boolean, default=True)
