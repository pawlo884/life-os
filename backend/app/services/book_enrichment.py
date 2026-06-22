import base64
import json
import re
from html import unescape

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.schemas.book_enrichment import BookEnrichmentResult

MAX_URL_BYTES = 120_000
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class _AiBookPayload(BaseModel):
    title: str
    author: str | None = None
    total_pages: int | None = None
    confidence: str = "medium"


def _client() -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured. Add it to your .env file.")
    return AsyncOpenAI(api_key=settings.openai_api_key)


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:6000]


def _meta_from_html(html: str) -> str:
    tags = []
    for pattern in (
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
        r"<title[^>]*>([^<]+)</title>",
    ):
        if match := re.search(pattern, html, flags=re.I):
            tags.append(match.group(1).strip())
    return " | ".join(tags)


async def _open_library_lookup(query: str) -> BookEnrichmentResult | None:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            "https://openlibrary.org/search.json",
            params={"q": query, "limit": 1, "fields": "title,author_name,number_of_pages_median,cover_i"},
        )
        response.raise_for_status()
        docs = response.json().get("docs") or []
        if not docs:
            return None

        doc = docs[0]
        cover_id = doc.get("cover_i")
        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None
        pages = doc.get("number_of_pages_median")
        return BookEnrichmentResult(
            title=doc.get("title") or query,
            author=(doc.get("author_name") or [None])[0],
            total_pages=int(pages) if pages else None,
            cover_url=cover_url,
            source="open_library",
            confidence="high" if pages else "medium",
        )


async def _ask_ai_text(prompt: str) -> BookEnrichmentResult:
    client = _client()
    response = await client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You identify books and return JSON with keys: "
                    "title (string), author (string or null), total_pages (integer or null), "
                    "confidence (high|medium|low). "
                    "Use realistic page counts for the edition when known. "
                    "If unsure about pages, set total_pages to null."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    try:
        payload = _AiBookPayload.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError("AI returned an invalid book payload") from exc

    return BookEnrichmentResult(
        title=payload.title,
        author=payload.author,
        total_pages=payload.total_pages,
        source="ai",
        confidence=payload.confidence,
    )


async def _ask_ai_vision(image_bytes: bytes, mime_type: str, hint: str | None) -> BookEnrichmentResult:
    client = _client()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    hint_text = f" Additional hint: {hint}" if hint else ""
    response = await client.chat.completions.create(
        model=settings.openai_vision_model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Read the book cover image and return JSON with keys: "
                    "title, author, total_pages (null if unknown), confidence (high|medium|low)."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Identify this book cover.{hint_text}"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                    },
                ],
            },
        ],
    )
    raw = response.choices[0].message.content or "{}"
    payload = _AiBookPayload.model_validate(json.loads(raw))
    return BookEnrichmentResult(
        title=payload.title,
        author=payload.author,
        total_pages=payload.total_pages,
        source="ai_vision",
        confidence=payload.confidence,
    )


def _merge(primary: BookEnrichmentResult, fallback: BookEnrichmentResult | None) -> BookEnrichmentResult:
    if not fallback:
        return primary
    return BookEnrichmentResult(
        title=primary.title or fallback.title,
        author=primary.author or fallback.author,
        total_pages=primary.total_pages or fallback.total_pages,
        cover_url=primary.cover_url or fallback.cover_url,
        source=primary.source if primary.source != "ai" else fallback.source,
        confidence=primary.confidence if primary.confidence != "low" else fallback.confidence,
    )


async def enrich_book(
    *,
    title: str | None = None,
    url: str | None = None,
    image_bytes: bytes | None = None,
    image_mime: str | None = None,
) -> BookEnrichmentResult:
    if not any([title, url, image_bytes]):
        raise ValueError("Provide a title, link, or cover photo.")

    if image_bytes:
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise ValueError("Image is too large (max 8 MB).")
        mime = image_mime or "image/jpeg"
        if not mime.startswith("image/"):
            raise ValueError("Uploaded file must be an image.")
        ai_result = await _ask_ai_vision(image_bytes, mime, title)
        library = await _open_library_lookup(ai_result.title)
        return _merge(ai_result, library)

    if url:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text[:MAX_URL_BYTES]
        meta = _meta_from_html(html)
        snippet = _strip_html(html)[:2500]
        prompt = (
            f"Book page URL: {url}\n"
            f"Metadata: {meta}\n"
            f"Page excerpt: {snippet}\n"
            "Infer the book details."
        )
        ai_result = await _ask_ai_text(prompt)
        library = await _open_library_lookup(ai_result.title or meta or url)
        return _merge(ai_result, library)

    query = title.strip()
    library = await _open_library_lookup(query)
    ai_result = await _ask_ai_text(f"Book title query: {query}")
    return _merge(ai_result, library)
