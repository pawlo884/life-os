from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class LearningProgressBase(BaseModel):
    resource_type: str
    title: str
    total_units: int = 0
    completed_units: int = 0
    status: str = "IN_PROGRESS"


class LearningProgressCreate(LearningProgressBase):
    pass


class LearningProgressUpdate(BaseModel):
    resource_type: str | None = None
    title: str | None = None
    total_units: int | None = None
    completed_units: int | None = None
    status: str | None = None


class LearningProgressRead(LearningProgressBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    completion_percent: float = Field(default=0.0)


class ReadingLogRequest(BaseModel):
    pages: int = Field(gt=0)
    title: str | None = None


class ReadingEstimate(BaseModel):
    resource_id: int
    title: str
    pages_read: int
    remaining_pages: int
    avg_pages_per_day: float
    estimated_completion_date: date | None = None
