from openai import AsyncOpenAI

from app.config import settings


def get_ai_client() -> AsyncOpenAI:
    if settings.openrouter_api_key:
        headers: dict[str, str] = {}
        if settings.openrouter_app_url:
            headers["HTTP-Referer"] = settings.openrouter_app_url
        if settings.openrouter_app_name:
            headers["X-Title"] = settings.openrouter_app_name
        return AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_headers=headers or None,
        )
    if settings.openai_api_key:
        return AsyncOpenAI(api_key=settings.openai_api_key)
    raise ValueError(
        "AI is not configured. Set OPENROUTER_API_KEY in .env "
        "(get one at https://openrouter.ai/keys)."
    )


def get_text_model() -> str:
    if settings.openrouter_api_key:
        return settings.openrouter_model
    return settings.openai_model


def get_vision_model() -> str:
    if settings.openrouter_api_key:
        return settings.openrouter_vision_model
    return settings.openai_vision_model


def ai_source_label() -> str:
    if settings.openrouter_api_key:
        return "openrouter"
    return "openai"
