import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.book_enrichment import BookEnrichmentResult
from app.services import book_enrichment
from app.services.book_enrichment import MAX_IMAGE_BYTES, enrich_book
from tests.conftest import MINIMAL_PNG


def _vision_ai_response(
    *,
    title: str = "Dune",
    author: str = "Frank Herbert",
    total_pages: int | None = 688,
    confidence: str = "high",
) -> str:
    return json.dumps(
        {
            "title": title,
            "author": author,
            "total_pages": total_pages,
            "confidence": confidence,
        }
    )


def _install_vision_mock(monkeypatch: pytest.MonkeyPatch, ai_json: str | None = None) -> dict:
    payload = ai_json or _vision_ai_response()
    captured: dict = {}

    async def fake_create(**kwargs):
        captured["kwargs"] = kwargs

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
    return captured


@pytest.mark.asyncio
async def test_enrich_from_image_returns_vision_result(monkeypatch, minimal_png):
    captured = _install_vision_mock(monkeypatch)
    monkeypatch.setattr(book_enrichment, "_open_library_lookup", AsyncMock(return_value=None))

    result = await enrich_book(image_bytes=minimal_png, image_mime="image/png")

    assert result.title == "Dune"
    assert result.author == "Frank Herbert"
    assert result.total_pages == 688
    assert result.source == "openrouter_vision"
    assert result.confidence == "high"
    assert result.cover_url is None

    kwargs = captured["kwargs"]
    assert kwargs["model"] == "openai/gpt-4o-mini"
    user_content = kwargs["messages"][1]["content"]
    image_part = next(part for part in user_content if part["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_enrich_from_image_merges_open_library_metadata(monkeypatch, minimal_png):
    _install_vision_mock(monkeypatch)
    library_hit = BookEnrichmentResult(
        title="Dune",
        author="Frank Herbert",
        total_pages=412,
        cover_url="https://covers.openlibrary.org/b/id/123-M.jpg",
        source="open_library",
        confidence="high",
        page_samples=[412],
    )
    monkeypatch.setattr(book_enrichment, "_open_library_lookup", AsyncMock(return_value=library_hit))

    result = await enrich_book(image_bytes=minimal_png, image_mime="image/png")

    assert result.title == "Dune"
    assert result.author == "Frank Herbert"
    assert result.total_pages == 412
    assert result.cover_url == "https://covers.openlibrary.org/b/id/123-M.jpg"
    assert result.source == "open_library"


@pytest.mark.asyncio
async def test_enrich_from_image_passes_title_hint_to_vision(monkeypatch, minimal_png):
    captured = _install_vision_mock(monkeypatch)
    monkeypatch.setattr(book_enrichment, "_open_library_lookup", AsyncMock(return_value=None))

    await enrich_book(
        title="maybe Dune Messiah",
        image_bytes=minimal_png,
        image_mime="image/png",
    )

    user_content = captured["kwargs"]["messages"][1]["content"]
    text_part = next(part for part in user_content if part["type"] == "text")
    assert "Additional hint: maybe Dune Messiah" in text_part["text"]


@pytest.mark.asyncio
async def test_enrich_from_image_defaults_to_jpeg_mime(monkeypatch, minimal_png):
    captured = _install_vision_mock(monkeypatch)
    monkeypatch.setattr(book_enrichment, "_open_library_lookup", AsyncMock(return_value=None))

    await enrich_book(image_bytes=minimal_png, image_mime=None)

    user_content = captured["kwargs"]["messages"][1]["content"]
    image_part = next(part for part in user_content if part["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/jpeg;base64,")


@pytest.mark.asyncio
async def test_enrich_from_image_rejects_oversized_file():
    oversized = b"x" * (MAX_IMAGE_BYTES + 1)
    with pytest.raises(ValueError, match="too large"):
        await enrich_book(image_bytes=oversized, image_mime="image/png")


@pytest.mark.asyncio
async def test_enrich_from_image_rejects_non_image_mime(minimal_png):
    with pytest.raises(ValueError, match="must be an image"):
        await enrich_book(image_bytes=minimal_png, image_mime="application/pdf")


@pytest.mark.asyncio
async def test_enrich_requires_at_least_one_input():
    with pytest.raises(ValueError, match="Provide a title, link, or cover photo"):
        await enrich_book()


@pytest.mark.asyncio
async def test_enrich_endpoint_accepts_image_upload(api_client, monkeypatch, minimal_png):
    _install_vision_mock(monkeypatch)
    monkeypatch.setattr(book_enrichment, "_open_library_lookup", AsyncMock(return_value=None))

    response = await api_client.post(
        "/api/v1/books/enrich",
        files={"image": ("cover.png", minimal_png, "image/png")},
        data={"title": "Dune"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Dune"
    assert body["source"] == "openrouter_vision"


@pytest.mark.asyncio
async def test_enrich_endpoint_rejects_oversized_image(api_client, minimal_png):
    huge = minimal_png + b"x" * MAX_IMAGE_BYTES

    response = await api_client.post(
        "/api/v1/books/enrich",
        files={"image": ("cover.png", huge, "image/png")},
    )

    assert response.status_code == 400
    assert "too large" in response.json()["detail"]


@pytest.mark.asyncio
async def test_enrich_endpoint_rejects_non_image_upload(api_client, minimal_png):
    response = await api_client.post(
        "/api/v1/books/enrich",
        files={"image": ("notes.pdf", minimal_png, "application/pdf")},
    )

    assert response.status_code == 400
    assert "must be an image" in response.json()["detail"]


@pytest.mark.asyncio
async def test_enrich_endpoint_returns_502_when_vision_fails(api_client, monkeypatch, minimal_png):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("upstream down"))
    monkeypatch.setattr(book_enrichment, "get_ai_client", lambda: mock_client)
    monkeypatch.setattr(book_enrichment, "get_vision_model", lambda: "openai/gpt-4o-mini")

    response = await api_client.post(
        "/api/v1/books/enrich",
        files={"image": ("cover.png", minimal_png, "image/png")},
    )

    assert response.status_code == 502
    assert "Book lookup failed" in response.json()["detail"]
