from datetime import date

from pydantic import BaseModel, Field


class BookEnrichmentResult(BaseModel):
    title: str
    author: str | None = None
    total_pages: int | None = Field(default=None, gt=0)
    cover_url: str | None = None
    source: str = "ai"
    confidence: str = "medium"
