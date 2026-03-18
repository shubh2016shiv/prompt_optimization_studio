"""
Application configuration using Pydantic Settings.

Loads settings from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = "APOST API"
    app_version: str = "4.0.0"
    debug: bool = False

    # CORS settings
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # LLM Provider API Keys (optional - can be passed per-request)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    # Default model for internal optimization calls
    optimizer_model: str = "claude-sonnet-4-20250514"

    # API rate limiting
    max_tokens_gap_analysis: int = 1500
    max_tokens_optimization: int = 4096
    max_tokens_chat: int = 2048

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
