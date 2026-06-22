from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskBase(BaseModel):
    title: str
    due_date: datetime | None = None
    status: str = "TODO"
    is_sla_critical: bool = False
    google_event_id: str | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    due_date: datetime | None = None
    status: str | None = None
    is_sla_critical: bool | None = None
    google_event_id: str | None = None


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
