from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Convert Supabase URI (postgresql://) to async SQLAlchemy format."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Paste connection string from Supabase Dashboard → Settings → Database
    # Session pooler (recommended): port 5432
    # Transaction pooler: port 6543
    database_url: str = ""

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    google_calendar_credentials_path: str | None = None
    strava_client_id: str | None = None
    strava_client_secret: str | None = None
    strava_webhook_verify_token: str | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o-mini"

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db_url(cls, value: str) -> str:
        if not value:
            return value
        return normalize_database_url(value)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_connect_args(self) -> dict:
        """Supabase requires SSL; transaction pooler needs statement cache disabled."""
        if "supabase" not in self.database_url:
            return {}
        args: dict = {"ssl": "require"}
        if ":6543/" in self.database_url:
            args["statement_cache_size"] = 0
        return args


settings = Settings()
