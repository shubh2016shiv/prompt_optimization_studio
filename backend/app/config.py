"""
Application configuration using Pydantic Settings.

Loads settings from environment variables with sensible defaults.
"""

from functools import lru_cache

from pydantic import model_validator
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
    log_level: str = "INFO"
    health_probe_timeout_seconds: float = 5.0

    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Token budget per operation type
    max_tokens_gap_analysis: int = 1500
    max_tokens_optimization: int = 4096
    max_tokens_chat: int = 2048

    # OpenAI fast model for TCRTE rubric scoring and optimizer internal sub-tasks
    openai_subtask_model: str = "gpt-4.1-nano"

    # TCRTE scorer (OpenAI Chat Completions) — see app.services.scoring.tcrte_scorer
    openai_chat_completions_url: str = "https://api.openai.com/v1/chat/completions"
    tcrte_score_max_tokens: int = 350
    tcrte_score_timeout_seconds: float = 20.0
    tcrte_score_max_prompt_chars: int = 2000

    # Overall TCRTE score = weighted blend (APOST_v4_Documentation.md §3.3); must sum to 1.0
    tcrte_weight_task: float = 0.25
    tcrte_weight_context: float = 0.15
    tcrte_weight_role: float = 0.15
    tcrte_weight_tone: float = 0.15
    tcrte_weight_execution: float = 0.30

    @model_validator(mode="after")
    def tcrte_weights_sum_to_one(self):
        total = (
            self.tcrte_weight_task
            + self.tcrte_weight_context
            + self.tcrte_weight_role
            + self.tcrte_weight_tone
            + self.tcrte_weight_execution
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                "TCRTE dimension weights must sum to 1.0; "
                f"got {total:.4f} from task/context/role/tone/execution weights."
            )
        return self

    @property
    def tcrte_dimension_weights(self) -> dict[str, float]:
        """Canonical weights for TCRTE overall score (same keys as gap-analysis dimensions)."""
        return {
            "task": self.tcrte_weight_task,
            "context": self.tcrte_weight_context,
            "role": self.tcrte_weight_role,
            "tone": self.tcrte_weight_tone,
            "execution": self.tcrte_weight_execution,
        }

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
