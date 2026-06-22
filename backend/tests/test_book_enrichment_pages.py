import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.book_enrichment import BookEnrichmentResult
from app.services import book_enrichment
from app.services.book_enrichment import _resolve_page_count, _robust_page_count, enrich_book
from tests.conftest import MINIMAL_PNG


def _install_vision_mock(monkeypatch: pytest.MonkeyPatch, *, total_pages: int | None = None) -> None:
    payload = json.dumps(
        {
            "title": "Dune",
            "author": "Frank Herbert",
            "total_pages": total_pages,
            "confidence": "medium",
        }
    )

    async def fake_create(**_kwargs):
        class Message:
            content = payload

        class Choice:
            message = Message()

        class Response:
            choices = [Choice()]

        return Response()

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=fake_create)
    monkeypatch.setattr(book_enrichment, "get_ai_client", lambda: mock_client)
    monkeypatch.setattr(book_enrichment, "get_vision_model", lambda: "openai/gpt-4o-mini")
    monkeypatch.setattr(book_enrichment, "ai_source_label", lambda: "openrouter")


def test_robust_page_count_prefers_paperback_cluster():
    assert _robust_page_count([170, 176, 180, 244]) <= 180
    assert _robust_page_count([244, 180]) == 180


def test_resolve_page_count_picks_lower_when_hardcover_outlier():
    pages, source = _resolve_page_count(library_samples=[244], ai_pages=180)
    assert pages == 180
    assert source == "ai"


def test_resolve_page_count_uses_ai_when_library_missing():
    pages, source = _resolve_page_count(library_samples=[], ai_pages=176)
    assert pages == 176
    assert source == "ai"


@pytest.mark.asyncio
async def test_enrich_prefers_paperback_when_catalog_and_ai_diverge(monkeypatch, minimal_png):
    _install_vision_mock(monkeypatch, total_pages=None)
    library_hit = BookEnrichmentResult(
        title="Dune",
        author="Frank Herbert",
        total_pages=244,
        cover_url="https://covers.openlibrary.org/b/id/123-M.jpg",
        source="open_library",
        confidence="high",
        page_samples=[244, 176, 180],
    )
    monkeypatch.setattr(book_enrichment, "_open_library_lookup", AsyncMock(return_value=library_hit))
    monkeypatch.setattr(book_enrichment, "_ask_ai_pages", AsyncMock(return_value=180))

    result = await enrich_book(image_bytes=minimal_png, image_mime="image/png")

    assert result.total_pages == 180
    assert result.cover_url == library_hit.cover_url


@pytest.mark.asyncio
async def test_enrich_fills_pages_from_ai_when_library_has_none(monkeypatch, minimal_png):
    _install_vision_mock(monkeypatch, total_pages=None)
    library_hit = BookEnrichmentResult(
        title="Dune",
        author="Frank Herbert",
        total_pages=None,
        source="open_library",
        confidence="medium",
    )
    monkeypatch.setattr(book_enrichment, "_open_library_lookup", AsyncMock(return_value=library_hit))
    monkeypatch.setattr(book_enrichment, "_ask_ai_pages", AsyncMock(return_value=688))

    result = await enrich_book(image_bytes=minimal_png, image_mime="image/png")

    assert result.total_pages == 688
    assert result.source == "openrouter_vision"


@pytest.mark.asyncio
async def test_enrich_always_calls_ai_page_lookup(monkeypatch, minimal_png):
    _install_vision_mock(monkeypatch, total_pages=688)
    monkeypatch.setattr(book_enrichment, "_open_library_lookup", AsyncMock(return_value=None))
    ai_pages = AsyncMock(return_value=None)
    monkeypatch.setattr(book_enrichment, "_ask_ai_pages", ai_pages)

    await enrich_book(image_bytes=minimal_png, image_mime="image/png")

    ai_pages.assert_awaited_once_with("Dune", "Frank Herbert", language=None)
