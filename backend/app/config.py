"""
Application configuration using Pydantic Settings.

Loads settings from environment variables with sensible defaults.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.

    API keys are NOT stored here — they are entered by the user in the UI
    and sent per-request to the backend.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "APOST API"
    app_version: str = "4.0.0"
    debug: bool = False

    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Token budget per operation type
    max_tokens_gap_analysis: int = 1500
    max_tokens_optimization: int = 4096
    max_tokens_chat: int = 2048

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
