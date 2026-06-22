from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    discord_token: str = ""
    discord_guild_id: int | None = None
    api_base_url: str = "http://localhost:8000/api/v1"


settings = Settings()
