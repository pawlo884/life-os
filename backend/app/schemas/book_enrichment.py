from datetime import date

from pydantic import BaseModel, Field


class BookEnrichmentResult(BaseModel):
    title: str
    author: str | None = None
    total_pages: int | None = Field(default=None, gt=0)
    cover_url: str | None = None
    language: str | None = Field(default=None, description="ISO 639-1 code, e.g. pl, en, de")
    source: str = "ai"
    confidence: str = "medium"
    page_samples: list[int] = Field(default_factory=list, exclude=True)
