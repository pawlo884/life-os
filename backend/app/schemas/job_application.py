from datetime import date

from pydantic import BaseModel, ConfigDict


class JobApplicationBase(BaseModel):
    company: str
    role: str
    status: str
    tech_stack: str | None = None
    notes: str | None = None
    applied_date: date | None = None


class JobApplicationCreate(JobApplicationBase):
    pass


class JobApplicationUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    status: str | None = None
    tech_stack: str | None = None
    notes: str | None = None
    applied_date: date | None = None


class JobApplicationRead(JobApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
