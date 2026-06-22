import os

# Must be set before app modules import the database engine.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from unittest.mock import AsyncMock

import pytest

from app.services import book_enrichment

# 1x1 PNG
MINIMAL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


@pytest.fixture(autouse=True)
def mock_ai_pages_lookup(monkeypatch):
    """Dedicated AI page lookup is mocked by default; override per test when needed."""
    monkeypatch.setattr(book_enrichment, "_ask_ai_pages", AsyncMock(return_value=None))


@pytest.fixture
def minimal_png() -> bytes:
    return MINIMAL_PNG


@pytest.fixture
async def api_client():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
