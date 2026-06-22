import pytest

from app.services.book_enrichment import _AiBookPayload, _parse_ai_book_payload, format_enrich_error


def test_parse_ai_book_payload_coerces_zero_pages_to_none():
    payload = _parse_ai_book_payload(
        '{"title": "Test", "author": "Author", "total_pages": 0, "language": "pl", "confidence": "high"}'
    )
    assert payload.total_pages is None


def test_format_enrich_error_handles_empty_message():
    assert "manually" in format_enrich_error(Exception())
