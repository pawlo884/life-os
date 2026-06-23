import base64
import json
import re
import statistics
from html import unescape

import httpx
from pydantic import BaseModel, ValidationError, field_validator

from app.schemas.book_enrichment import BookEnrichmentResult
from app.services.ai_client import ai_source_label, get_ai_client, get_text_model, get_vision_model

MAX_URL_BYTES = 120_000
MAX_IMAGE_BYTES = 8 * 1024 * 1024
OPEN_LIBRARY_EDITION_LIMIT = 12

# ISO 639-1 → Open Library language codes
LANGUAGE_TO_OPEN_LIBRARY: dict[str, str] = {
    "pl": "pol",
    "en": "eng",
    "de": "ger",
    "fr": "fre",
    "es": "spa",
    "it": "ita",
    "cs": "cze",
    "uk": "ukr",
    "ru": "rus",
    "nl": "dut",
    "pt": "por",
    "sv": "swe",
}

LANGUAGE_LABELS: dict[str, str] = {
    "pl": "Polish",
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "cs": "Czech",
    "uk": "Ukrainian",
    "ru": "Russian",
    "nl": "Dutch",
    "pt": "Portuguese",
    "sv": "Swedish",
}


LANGUAGE_ALIASES: dict[str, str] = {
    "polish": "pl",
    "polski": "pl",
    "pol": "pl",
    "english": "en",
    "angielski": "en",
    "eng": "en",
    "german": "de",
    "niemiecki": "de",
    "ger": "de",
    "deu": "de",
    "french": "fr",
    "francuski": "fr",
    "fre": "fr",
    "fra": "fr",
    "spanish": "es",
    "hiszpanski": "es",
    "hiszpański": "es",
    "spa": "es",
    "czech": "cs",
    "czeski": "cs",
    "cze": "cs",
    "ukrainian": "uk",
    "ukrainski": "uk",
    "ukraiński": "uk",
    "ukr": "uk",
}


class _AiBookPayload(BaseModel):
    title: str
    author: str | None = None
    total_pages: int | None = None
    language: str | None = None
    confidence: str = "medium"

    @field_validator("title", mode="before")
    @classmethod
    def _require_title(cls, value: object) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("AI could not identify the book title.")
        return text

    @field_validator("total_pages", mode="before")
    @classmethod
    def _positive_pages(cls, value: object) -> int | None:
        if value is None or value == "":
            return None
        pages = int(value)
        return pages if pages > 0 else None


def _normalize_language_code(value: str | None) -> str | None:
    if not value:
        return None
    code = value.strip().lower().split("-")[0]
    if code in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[code]
    if len(code) == 2 and code.isalpha():
        return code
    if len(code) == 3:
        for iso, ol_code in LANGUAGE_TO_OPEN_LIBRARY.items():
            if ol_code == code:
                return iso
    return None


def _payload_to_result(payload: _AiBookPayload, *, source: str) -> BookEnrichmentResult:
    return BookEnrichmentResult(
        title=payload.title,
        author=payload.author,
        total_pages=payload.total_pages,
        language=_normalize_language_code(payload.language),
        source=source,
        confidence=payload.confidence,
    )


def _parse_ai_book_payload(raw: str) -> _AiBookPayload:
    try:
        return _AiBookPayload.model_validate(json.loads(raw))
    except json.JSONDecodeError as exc:
        raise ValueError("AI returned invalid JSON.") from exc
    except ValidationError as exc:
        raise ValueError("AI returned incomplete book data.") from exc


def _to_open_library_language(language: str | None) -> str | None:
    code = _normalize_language_code(language)
    if not code:
        return None
    return LANGUAGE_TO_OPEN_LIBRARY.get(code, code)


def _language_label(language: str | None) -> str:
    code = _normalize_language_code(language)
    if not code:
        return "this language"
    return LANGUAGE_LABELS.get(code, code)


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


async def _fetch_edition_pages(client: httpx.AsyncClient, edition_key: str) -> int | None:
    response = await client.get(f"https://openlibrary.org/books/{edition_key}.json")
    response.raise_for_status()
    pages = response.json().get("number_of_pages")
    return int(pages) if pages else None


def _robust_page_count(page_counts: list[int]) -> int | None:
    if not page_counts:
        return None

    counts = sorted(page_counts)
    if len(counts) >= 4:
        q1, _, q3 = statistics.quantiles(counts, n=4)
        iqr = q3 - q1
        if iqr > 0:
            upper_fence = q3 + 1.5 * iqr
            filtered = [count for count in counts if count <= upper_fence]
            if filtered:
                counts = filtered

    if len(counts) >= 2 and counts[-1] / counts[0] > 1.15:
        mid = statistics.median(counts)
        lower_cluster = [count for count in counts if count <= mid]
        if lower_cluster:
            return int(statistics.median(lower_cluster))

    return int(statistics.median(counts))


def _resolve_page_count(*, library_samples: list[int], ai_pages: int | None) -> tuple[int | None, str]:
    """Combine catalog editions + AI; prefer typical paperback when editions diverge."""
    samples = list(library_samples)
    if ai_pages:
        samples.append(ai_pages)
    if not samples:
        return None, ""

    chosen = _robust_page_count(samples)
    if not chosen:
        return None, ""

    if ai_pages and chosen == ai_pages and (not library_samples or chosen not in library_samples):
        return chosen, "ai"
    if library_samples and chosen in library_samples:
        return chosen, "open_library"
    if ai_pages and library_samples:
        return chosen, "ai" if abs(chosen - ai_pages) <= abs(chosen - statistics.median(library_samples)) else "open_library"
    if ai_pages:
        return chosen, "ai"
    return chosen, "open_library"


async def _open_library_lookup(query: str, *, language: str | None = None) -> BookEnrichmentResult | None:
    ol_lang = _to_open_library_language(language)
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                "https://openlibrary.org/search.json",
                params={
                    "q": query,
                    "limit": 8,
                    "fields": "title,author_name,number_of_pages_median,cover_i,edition_key,language",
                },
            )
            response.raise_for_status()
            docs = response.json().get("docs") or []
            doc = _pick_library_doc(docs, ol_lang)
            if not doc:
                return None

            cover_id = doc.get("cover_i")
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None
            page_counts: list[int] = []
            median_pages = doc.get("number_of_pages_median")
            if median_pages:
                page_counts.append(int(median_pages))
            for edition_key in (doc.get("edition_key") or [])[:OPEN_LIBRARY_EDITION_LIMIT]:
                try:
                    edition_pages = await _fetch_edition_pages(client, edition_key)
                except httpx.HTTPError:
                    edition_pages = None
                if edition_pages:
                    page_counts.append(edition_pages)
            pages = _robust_page_count(page_counts)
            doc_langs = doc.get("language") or []
            detected_lang = language or _from_open_library_language(doc_langs[0] if doc_langs else None)

            return BookEnrichmentResult(
                title=doc.get("title") or query,
                author=(doc.get("author_name") or [None])[0],
                total_pages=pages,
                cover_url=cover_url,
                language=detected_lang,
                source="open_library",
                confidence="high" if pages else "medium",
                page_samples=page_counts,
            )
    except httpx.HTTPError:
        return None


def _from_open_library_language(ol_code: str | None) -> str | None:
    if not ol_code:
        return None
    for iso, code in LANGUAGE_TO_OPEN_LIBRARY.items():
        if code == ol_code:
            return iso
    return None


def _pick_library_doc(docs: list[dict], ol_lang: str | None) -> dict | None:
    if not docs:
        return None
    if ol_lang:
        for doc in docs:
            if ol_lang in (doc.get("language") or []):
                return doc
        return None
    return docs[0]


async def _lookup_library_for_book(
    title: str,
    author: str | None = None,
    *,
    language: str | None = None,
    fallback_query: str | None = None,
) -> BookEnrichmentResult | None:
    primary_query = f"{title} {author}".strip() if author else title.strip()
    hit = await _open_library_lookup(primary_query, language=language)
    if hit and (hit.total_pages or hit.page_samples):
        return hit

    if fallback_query and fallback_query.strip().casefold() != primary_query.casefold():
        fallback_hit = await _open_library_lookup(fallback_query.strip(), language=language)
        if fallback_hit:
            return _merge(fallback_hit, hit) if hit else fallback_hit

    return hit


class _AiPagesPayload(BaseModel):
    total_pages: int | None = None

    @field_validator("total_pages", mode="before")
    @classmethod
    def _positive_pages(cls, value: object) -> int | None:
        if value is None or value == "":
            return None
        pages = int(value)
        return pages if pages > 0 else None


async def _ask_ai_pages(title: str, author: str | None, *, language: str | None = None) -> int | None:
    byline = f'"{title}"'
    if author:
        byline += f" by {author}"
    lang_hint = (
        f" Use the {_language_label(language)} edition (as printed on the cover), not a translation."
        if language
        else " Use the edition in the book's original cover language, not an English translation."
    )
    try:
        client = get_ai_client()
        response = await client.chat.completions.create(
            model=get_text_model(),
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You look up bibliographic data for books. "
                        "Return JSON with key total_pages (integer or null). "
                        "Use the mass-market paperback page count for the requested language edition."
                        + lang_hint
                    ),
                },
                {"role": "user", "content": f"What is the page count for {byline}?"},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        try:
            payload = _AiPagesPayload.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError):
            return None
        return payload.total_pages
    except Exception:
        return None


async def _finalize_result(
    ai_result: BookEnrichmentResult,
    library: BookEnrichmentResult | None,
    *,
    language: str | None = None,
    fallback_query: str | None = None,
) -> BookEnrichmentResult:
    effective_language = _normalize_language_code(language) or _normalize_language_code(ai_result.language)
    merged = _merge(ai_result, library)
    if effective_language:
        merged = merged.model_copy(update={"language": effective_language})

    library_samples = list(merged.page_samples)

    if not library_samples:
        extra_library = await _lookup_library_for_book(
            merged.title,
            merged.author,
            language=effective_language,
            fallback_query=fallback_query,
        )
        if extra_library:
            merged = _merge(merged, extra_library)
            library_samples = list(merged.page_samples)

    ai_pages = await _ask_ai_pages(merged.title, merged.author, language=effective_language)
    if not ai_pages:
        ai_pages = ai_result.total_pages

    total_pages, page_source = _resolve_page_count(library_samples=library_samples, ai_pages=ai_pages)

    if not total_pages:
        return merged

    source = merged.source
    if page_source == "open_library":
        source = "open_library"
    elif page_source == "ai":
        source = ai_result.source

    return merged.model_copy(update={"total_pages": total_pages, "source": source, "language": effective_language})


_AI_BOOK_SYSTEM = (
    "You identify books and return JSON with keys: "
    "title (string), author (string or null), total_pages (integer or null), "
    "language (ISO 639-1 code, e.g. pl, en, de), confidence (high|medium|low). "
    "Keep title and author in the language shown on the cover or in the query — do not translate. "
    "Page count must match that language edition when known."
)


async def _ask_ai_text(prompt: str) -> BookEnrichmentResult:
    client = get_ai_client()
    response = await client.chat.completions.create(
        model=get_text_model(),
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _AI_BOOK_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    payload = _parse_ai_book_payload(raw)
    return _payload_to_result(payload, source=ai_source_label())


async def _ask_ai_vision(image_bytes: bytes, mime_type: str, hint: str | None) -> BookEnrichmentResult:
    client = get_ai_client()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    hint_text = f" Additional hint: {hint}" if hint else ""
    response = await client.chat.completions.create(
        model=get_vision_model(),
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Read the book cover image. Return JSON with keys: "
                    "title, author, total_pages, language (ISO 639-1 from cover text), "
                    "confidence (high|medium|low). "
                    "Copy title and author exactly as printed on the cover — do not translate to English. "
                    "Detect language from the cover typography. "
                    "Page count must be for this cover's language edition when known."
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
    payload = _parse_ai_book_payload(raw)
    return _payload_to_result(payload, source=f"{ai_source_label()}_vision")


def _merge(primary: BookEnrichmentResult, fallback: BookEnrichmentResult | None) -> BookEnrichmentResult:
    if not fallback:
        return primary
    return BookEnrichmentResult(
        title=primary.title or fallback.title,
        author=primary.author or fallback.author,
        total_pages=primary.total_pages or fallback.total_pages,
        cover_url=primary.cover_url or fallback.cover_url,
        language=primary.language or fallback.language,
        source=primary.source if primary.source not in ("openrouter", "openai") else fallback.source,
        confidence=primary.confidence if primary.confidence != "low" else fallback.confidence,
        page_samples=[*primary.page_samples, *fallback.page_samples],
    )


async def enrich_book(
    *,
    title: str | None = None,
    url: str | None = None,
    image_bytes: bytes | None = None,
    image_mime: str | None = None,
    language: str | None = None,
) -> BookEnrichmentResult:
    language_hint = _normalize_language_code(language)

    if not any([title, url, image_bytes]):
        raise ValueError("Provide a title, link, or cover photo.")

    if image_bytes:
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise ValueError("Image is too large (max 8 MB).")
        mime = image_mime or "image/jpeg"
        if not mime.startswith("image/"):
            raise ValueError("Uploaded file must be an image.")
        ai_result = await _ask_ai_vision(image_bytes, mime, title)
        effective_language = language_hint or ai_result.language
        library = await _lookup_library_for_book(
            ai_result.title,
            ai_result.author,
            language=effective_language,
            fallback_query=title,
        )
        return await _finalize_result(
            ai_result,
            library,
            language=effective_language,
            fallback_query=title,
        )

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
            "Infer the book details. Keep title/author in the page language — do not translate."
        )
        ai_result = await _ask_ai_text(prompt)
        effective_language = language_hint or ai_result.language
        library = await _lookup_library_for_book(
            ai_result.title,
            ai_result.author,
            language=effective_language,
            fallback_query=url,
        )
        return await _finalize_result(
            ai_result,
            library,
            language=effective_language,
            fallback_query=url,
        )

    query = title.strip()
    lang_note = f" Preferred language: {language_hint}." if language_hint else ""
    ai_result = await _ask_ai_text(f"Book title query: {query}.{lang_note} Keep the original language.")
    effective_language = language_hint or ai_result.language
    library = await _lookup_library_for_book(
        ai_result.title,
        ai_result.author,
        language=effective_language,
        fallback_query=query,
    )
    return await _finalize_result(
        ai_result,
        library,
        language=effective_language,
        fallback_query=query,
    )


def format_enrich_error(exc: Exception) -> str:
    message = str(exc).strip()
    lowered = message.lower()
    if "invalid_image_format" in lowered or "unsupported image" in lowered:
        return "Unsupported image format. Use PNG, JPEG, GIF, or WebP."
    if "api_key" in lowered or "not configured" in lowered:
        return message
    if "rate limit" in lowered or "429" in lowered:
        return "AI service is busy. Please try again in a moment."
    if "timed out" in lowered or "timeout" in lowered:
        return "Book lookup timed out. Please try again."
    if message:
        return f"Book lookup failed: {message.splitlines()[0]}"
    exc_name = type(exc).__name__
    if exc_name in {"ConnectError", "ConnectTimeout", "ReadTimeout", "PoolTimeout", "NetworkError"}:
        return "Book lookup failed: network error. Check your connection and try again."
    if exc_name in {"APIConnectionError", "APITimeoutError"}:
        return "Book lookup failed: AI service unreachable. Please try again."
    return "Book lookup failed. Try again or enter the book details manually."
