from unittest.mock import AsyncMock

import pytest

from app.services import book_enrichment
from app.services.book_enrichment import (
    _looks_like_image_url,
    _normalize_cover_url,
    _upscale_lubimyczytac_cover,
    lookup_cover_only,
)


def test_normalize_cover_url_accepts_https():
    assert _normalize_cover_url("https://example.com/cover.jpg") == "https://example.com/cover.jpg"


def test_normalize_cover_url_rejects_non_http():
    assert _normalize_cover_url("ftp://example.com/cover.jpg") is None


def test_looks_like_image_url_detects_extensions():
    assert _looks_like_image_url("https://cdn.example.com/book/cover.webp?size=large")


def test_upscale_lubimyczytac_cover():
    url = "https://s.lubimyczytac.pl/upload/books/1/2/3-70x100.jpg"
    assert _upscale_lubimyczytac_cover(url).endswith("-352x500.jpg")


@pytest.mark.asyncio
async def test_lookup_cover_only_uses_lubimyczytac_for_polish(monkeypatch):
    monkeypatch.setattr(
        book_enrichment,
        "_lubimyczytac_cover_lookup",
        AsyncMock(return_value="https://s.lubimyczytac.pl/upload/books/1/2/3-352x500.jpg"),
    )
    monkeypatch.setattr(book_enrichment, "_ask_ai_cover_url", AsyncMock(return_value=None))

    result = await lookup_cover_only(title="Fenomen poranka", author="Hal Elrod", language="pl")

    assert result.cover_url == "https://s.lubimyczytac.pl/upload/books/1/2/3-352x500.jpg"
    assert result.source == "lubimyczytac"
    book_enrichment._ask_ai_cover_url.assert_not_called()


@pytest.mark.asyncio
async def test_lookup_cover_only_uses_ai_when_polish_source_misses(monkeypatch):
    monkeypatch.setattr(book_enrichment, "_lubimyczytac_cover_lookup", AsyncMock(return_value=None))
    monkeypatch.setattr(
        book_enrichment,
        "_ask_ai_cover_url",
        AsyncMock(return_value="https://empik.pl/covers/fenomen.jpg"),
    )
    monkeypatch.setattr(book_enrichment, "_open_library_lookup", AsyncMock(return_value=None))

    result = await lookup_cover_only(title="Fenomen poranka", author="Hal Elrod", language="pl")

    assert result.cover_url == "https://empik.pl/covers/fenomen.jpg"
    assert result.source == "openrouter"


@pytest.mark.asyncio
async def test_lookup_cover_only_falls_back_to_open_library(monkeypatch):
    from app.schemas.book_enrichment import BookEnrichmentResult

    monkeypatch.setattr(book_enrichment, "_lubimyczytac_cover_lookup", AsyncMock(return_value=None))
    monkeypatch.setattr(book_enrichment, "_ask_ai_cover_url", AsyncMock(return_value=None))
    monkeypatch.setattr(
        book_enrichment,
        "_open_library_lookup",
        AsyncMock(
            return_value=BookEnrichmentResult(
                title="Fenomen poranka",
                cover_url="https://covers.openlibrary.org/b/id/1-M.jpg",
                source="open_library",
            )
        ),
    )

    result = await lookup_cover_only(title="Fenomen poranka", language="pl")

    assert result.cover_url == "https://covers.openlibrary.org/b/id/1-M.jpg"
    assert result.source == "open_library"
