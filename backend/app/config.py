"""
Centralized runtime configuration using Pydantic Settings.

This module is the single source of truth for environment-driven runtime
behavior, including prompt optimization defaults and safety guardrails.
"""

from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderFormattingRule(BaseModel):
    """Formatting behavior for a target provider's prompt layout."""

    delimiter_style: Literal["xml", "markdown"]
    section_header_format: str
    constraint_position: Literal["primacy", "middle", "recency"] = "primacy"
    supports_prefill: bool = False
    supports_restate_critical: bool = True


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env.

    API keys are not persisted in this object. They are supplied per request.
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
    redis_url: str = "redis://redis:6379/0"
    redis_max_connections: int = 100
    redis_socket_timeout_seconds: float = 5.0
    redis_key_prefix: str = "apost:v4:"
    redis_fail_fast: bool = False
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Token budgets per operation type
    max_tokens_gap_analysis: int = 1500
    max_tokens_optimization: int = 4096
    max_tokens_chat: int = 2048
    max_tokens_task_evaluation_generation: int = 2048
    max_tokens_task_evaluation_judging: int = 900
    max_task_evaluation_cases_per_request: int = 100
    task_evaluation_max_concurrency: int = 10
    task_evaluation_judge_retry_attempts: int = 3
    task_evaluation_judge_retry_base_delay_seconds: float = 0.5
    task_evaluation_judge_retry_max_delay_seconds: float = 4.0
    task_evaluation_judge_retry_jitter_seconds: float = 0.25
    optimization_job_worker_processes: int = 2

    # OpenAI fast model for scoring and internal optimization sub-tasks
    openai_subtask_model: str = "gpt-4.1-nano"
    task_evaluation_case_pass_threshold: int = 70
    task_evaluation_pairwise_margin: int = 5
    task_evaluation_pairwise_adjustment: int = 2

    # TCRTE scorer (OpenAI Chat Completions)
    openai_chat_completions_url: str = "https://api.openai.com/v1/chat/completions"
    tcrte_score_max_tokens: int = 350
    tcrte_score_timeout_seconds: float = 20.0
    tcrte_score_max_prompt_chars: int = 2000

    # Overall TCRTE score weighting; must sum to 1.0
    tcrte_weight_task: float = 0.25
    tcrte_weight_context: float = 0.15
    tcrte_weight_role: float = 0.15
    tcrte_weight_tone: float = 0.15
    tcrte_weight_execution: float = 0.30

    # Prompt optimization runtime controls
    optimization_llm_sub_task_provider: str = "openai"
    optimization_max_tokens_component_extraction: int = 2048
    optimization_max_tokens_synthetic_example_generation: int = 1500
    optimization_max_tokens_textgrad_evaluation: int = 1200
    optimization_max_tokens_textgrad_gradient: int = 800
    optimization_max_tokens_textgrad_update: int = 2048
    optimization_max_tokens_tcrte_dimension_fill: int = 1500
    optimization_max_tokens_variant_score_estimation: int = 350
    optimization_max_tokens_failure_mode_analysis: int = 1500
    optimization_max_tokens_core_criticality_analysis: int = 1200
    optimization_max_tokens_ral_constraint_extraction: int = 1000
    optimization_max_tokens_opro_proposal: int = 2500
    optimization_max_tokens_sammo_structural_parse: int = 1500
    optimization_max_tokens_kernel_rewrite: int = 2200
    optimization_max_tokens_xml_rewrite: int = 2200
    optimization_max_tokens_create_rewrite: int = 2200
    optimization_max_tokens_progressive_rewrite: int = 2200

    optimization_textgrad_default_iteration_count: int = 3
    optimization_textgrad_evaluation_temperature: float = 0.0
    optimization_textgrad_update_temperature: float = 0.3

    optimization_opro_default_iteration_count: int = 3
    optimization_opro_candidates_per_iteration: int = 2
    optimization_opro_trajectory_keep_top: int = 20
    optimization_opro_exemplars_in_meta_prompt: int = 3
    optimization_opro_max_training_cases: int = 12
    optimization_opro_proposal_temperature: float = 0.8

    optimization_sammo_min_tcrte_threshold: int = 60
    optimization_sammo_token_weight: float = 0.30
    optimization_sammo_tcrte_weight: float = 0.70

    optimization_core_minimum_repetition_count: int = 2
    optimization_core_maximum_repetition_count: int = 5

    optimization_prefill_suggestion_by_task_type: dict[str, str] = Field(
        default_factory=lambda: {
            "extraction": "{",
            "qa": "{",
            "routing": "{",
            "analysis": "## ",
            "coding": "```",
            "planning": "## ",
            "reasoning": "<thinking>",
            "creative": "",
        }
    )
    optimization_prefill_default: str = "{"

    optimization_provider_formatting_rules: dict[str, ProviderFormattingRule] = Field(
        default_factory=lambda: {
            "anthropic": ProviderFormattingRule(
                delimiter_style="xml",
                section_header_format="<{name}>\n{content}\n</{name}>",
                constraint_position="primacy",
                supports_prefill=True,
                supports_restate_critical=True,
            ),
            "openai": ProviderFormattingRule(
                delimiter_style="markdown",
                section_header_format="### {name}\n{content}",
                constraint_position="primacy",
                supports_prefill=False,
                supports_restate_critical=True,
            ),
            "google": ProviderFormattingRule(
                delimiter_style="xml",
                section_header_format="<{name}>\n{content}\n</{name}>",
                constraint_position="primacy",
                supports_prefill=False,
                supports_restate_critical=True,
            ),
        }
    )
    optimization_provider_formatting_default_provider: str = "openai"

    optimization_system_prompt_for_json_extraction: str = (
        "You are a precision text parser. Return ONLY valid JSON matching the specified "
        "schema. No markdown fences, no explanation."
    )

    @model_validator(mode="after")
    def tcrte_weights_sum_to_one(self) -> "Settings":
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

    @model_validator(mode="after")
    def task_evaluation_runtime_config_is_valid(self) -> "Settings":
        if self.task_evaluation_max_concurrency < 1:
            raise ValueError("task_evaluation_max_concurrency must be >= 1.")
        if self.task_evaluation_judge_retry_attempts < 1:
            raise ValueError("task_evaluation_judge_retry_attempts must be >= 1.")
        if self.task_evaluation_judge_retry_base_delay_seconds < 0:
            raise ValueError("task_evaluation_judge_retry_base_delay_seconds must be >= 0.")
        if self.task_evaluation_judge_retry_max_delay_seconds < 0:
            raise ValueError("task_evaluation_judge_retry_max_delay_seconds must be >= 0.")
        if self.task_evaluation_judge_retry_jitter_seconds < 0:
            raise ValueError("task_evaluation_judge_retry_jitter_seconds must be >= 0.")
        return self

    @model_validator(mode="after")
    def optimization_runtime_config_is_valid(self) -> "Settings":
        positive_int_fields = {
            "optimization_max_tokens_component_extraction": self.optimization_max_tokens_component_extraction,
            "optimization_max_tokens_synthetic_example_generation": self.optimization_max_tokens_synthetic_example_generation,
            "optimization_max_tokens_textgrad_evaluation": self.optimization_max_tokens_textgrad_evaluation,
            "optimization_max_tokens_textgrad_gradient": self.optimization_max_tokens_textgrad_gradient,
            "optimization_max_tokens_textgrad_update": self.optimization_max_tokens_textgrad_update,
            "optimization_max_tokens_tcrte_dimension_fill": self.optimization_max_tokens_tcrte_dimension_fill,
            "optimization_max_tokens_variant_score_estimation": self.optimization_max_tokens_variant_score_estimation,
            "optimization_max_tokens_failure_mode_analysis": self.optimization_max_tokens_failure_mode_analysis,
            "optimization_max_tokens_core_criticality_analysis": self.optimization_max_tokens_core_criticality_analysis,
            "optimization_max_tokens_ral_constraint_extraction": self.optimization_max_tokens_ral_constraint_extraction,
            "optimization_max_tokens_opro_proposal": self.optimization_max_tokens_opro_proposal,
            "optimization_max_tokens_sammo_structural_parse": self.optimization_max_tokens_sammo_structural_parse,
            "optimization_max_tokens_kernel_rewrite": self.optimization_max_tokens_kernel_rewrite,
            "optimization_max_tokens_xml_rewrite": self.optimization_max_tokens_xml_rewrite,
            "optimization_max_tokens_create_rewrite": self.optimization_max_tokens_create_rewrite,
            "optimization_max_tokens_progressive_rewrite": self.optimization_max_tokens_progressive_rewrite,
            "optimization_textgrad_default_iteration_count": self.optimization_textgrad_default_iteration_count,
            "optimization_opro_default_iteration_count": self.optimization_opro_default_iteration_count,
            "optimization_opro_candidates_per_iteration": self.optimization_opro_candidates_per_iteration,
            "optimization_opro_trajectory_keep_top": self.optimization_opro_trajectory_keep_top,
            "optimization_opro_exemplars_in_meta_prompt": self.optimization_opro_exemplars_in_meta_prompt,
            "optimization_opro_max_training_cases": self.optimization_opro_max_training_cases,
            "optimization_core_minimum_repetition_count": self.optimization_core_minimum_repetition_count,
            "optimization_core_maximum_repetition_count": self.optimization_core_maximum_repetition_count,
        }
        for field_name, value in positive_int_fields.items():
            if value <= 0:
                raise ValueError(f"{field_name} must be > 0.")

        temperature_fields = {
            "optimization_textgrad_evaluation_temperature": self.optimization_textgrad_evaluation_temperature,
            "optimization_textgrad_update_temperature": self.optimization_textgrad_update_temperature,
            "optimization_opro_proposal_temperature": self.optimization_opro_proposal_temperature,
        }
        for field_name, value in temperature_fields.items():
            if value < 0 or value > 2:
                raise ValueError(f"{field_name} must be in the range [0, 2].")

        if self.optimization_core_minimum_repetition_count > self.optimization_core_maximum_repetition_count:
            raise ValueError(
                "optimization_core_minimum_repetition_count must be <= "
                "optimization_core_maximum_repetition_count."
            )

        sammo_total = self.optimization_sammo_token_weight + self.optimization_sammo_tcrte_weight
        if abs(sammo_total - 1.0) > 0.001:
            raise ValueError(
                "SAMMO weights must sum to 1.0; "
                f"got {sammo_total:.4f} from optimization_sammo_token_weight "
                "and optimization_sammo_tcrte_weight."
            )

        if self.optimization_provider_formatting_default_provider not in self.optimization_provider_formatting_rules:
            raise ValueError(
                "optimization_provider_formatting_default_provider must exist in "
                "optimization_provider_formatting_rules."
            )

        if not self.optimization_prefill_suggestion_by_task_type:
            raise ValueError("optimization_prefill_suggestion_by_task_type cannot be empty.")

        return self

    @property
    def tcrte_dimension_weights(self) -> dict[str, float]:
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

    @property
    def optimization_provider_formatting_rules_dict(self) -> dict[str, dict[str, Any]]:
        return {
            provider: rule.model_dump()
            for provider, rule in self.optimization_provider_formatting_rules.items()
        }

    @property
    def optimization_provider_formatting_default(self) -> dict[str, Any]:
        default_provider = self.optimization_provider_formatting_default_provider
        return self.optimization_provider_formatting_rules_dict[default_provider]


@lru_cache
def get_settings() -> Settings:
    return Settings()
