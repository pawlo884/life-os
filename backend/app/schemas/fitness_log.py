from datetime import date

from pydantic import BaseModel, ConfigDict


class FitnessLogBase(BaseModel):
    source: str
    activity_type: str
    duration_minutes: int
    date: date
    streak_impact: bool = True


class FitnessLogCreate(FitnessLogBase):
    pass


class FitnessLogRead(FitnessLogBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class StreakInfo(BaseModel):
    current_streak: int
    last_activity_date: date | None
    at_risk: bool
