"""
Pydantic request models for API endpoints.

These define the shape of incoming request bodies with validation.
"""

from typing import Any, Optional, Literal

from pydantic import BaseModel, Field, field_validator


class GapAnalysisRequest(BaseModel):
    """Request body for the gap analysis endpoint."""

    raw_prompt: str = Field(
        ...,
        min_length=1,
        description="The raw prompt to analyze for TCRTE coverage gaps",
    )
    input_variables: Optional[str] = Field(
        default=None,
        description="Declared input variables in the prompt (e.g., '{{documents}} - array of PDFs')",
    )
    task_type: str = Field(
        default="reasoning",
        description="The type of task (planning, reasoning, coding, etc.)",
    )
    provider: str = Field(
        default="anthropic",
        description="The target LLM provider (anthropic, openai, google)",
    )
    model_id: str = Field(
        default="claude-sonnet-4-6",
        description="The target model ID",
    )
    model_label: str = Field(
        default="Claude Sonnet 4.6",
        description="The target model display label",
    )
    is_reasoning_model: bool = Field(
        default=False,
        description="Whether the target model is a reasoning model (o-series, extended thinking)",
    )
    api_key: str = Field(
        ...,
        min_length=1,
        description="API key for the LLM provider",
    )


class EvaluationDatasetCase(BaseModel):
    """
    One task-level evaluation example provided by the API caller.

    This model is used by the optimization route when the caller requests
    empirical task scoring for each generated prompt variant.
    """

    input: str = Field(
        ...,
        min_length=1,
        description="Task input that will be sent to each generated variant.",
    )
    expected_output: Any = Field(
        ...,
        description=(
            "Canonical reference output used for scoring. "
            "Can be plain text or structured JSON-like data."
        ),
    )

    @field_validator("expected_output")
    @classmethod
    def validate_expected_output_is_present(cls, expected_output_value: Any) -> Any:
        """
        Ensure each dataset case provides an actual expected output.

        Association:
          This validator protects app.services.evaluation.task_level_evaluation,
          which assumes every case has a non-null expected output for scoring.
        """
        if expected_output_value is None:
            raise ValueError("expected_output cannot be null")
        return expected_output_value


class OptimizationRequest(BaseModel):
    """Request body for the optimization endpoint."""

    raw_prompt: str = Field(
        ...,
        min_length=1,
        description="The raw prompt to optimize",
    )
    input_variables: Optional[str] = Field(
        default=None,
        description="Declared input variables in the prompt",
    )
    task_type: str = Field(
        default="reasoning",
        description="The type of task",
    )
    framework: str = Field(
        default="auto",
        description="The optimization framework to apply",
    )
    quality_gate_mode: Literal["full", "critique_only", "off", "sample_one_variant"] = Field(
        default="full",
        description=(
            "Quality gate mode: full (critique+enhance all variants), "
            "critique_only (evaluate all, no enhancement), off (skip quality gate), "
            "sample_one_variant (full gate on variant 1 only)."
        ),
    )
    provider: str = Field(
        default="anthropic",
        description="The target LLM provider",
    )
    model_id: str = Field(
        default="claude-sonnet-4-6",
        description="The target model ID",
    )
    model_label: str = Field(
        default="Claude Sonnet 4.6",
        description="The target model display label",
    )
    is_reasoning_model: bool = Field(
        default=False,
        description="Whether the target model is a reasoning model",
    )
    gap_data: Optional[dict] = Field(
        default=None,
        description="Gap analysis data from previous step (TCRTE scores, complexity, techniques)",
    )
    answers: Optional[dict[str, str]] = Field(
        default=None,
        description="User answers to gap interview questions (question text -> answer)",
    )
    evaluation_dataset: Optional[list[EvaluationDatasetCase]] = Field(
        default=None,
        min_length=1,
        description=(
            "Optional dataset for task-level empirical scoring. "
            "When supplied, each generated variant is executed against each case."
        ),
    )
    api_key: str = Field(
        ...,
        min_length=1,
        description="API key for the LLM provider",
    )


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    message: str = Field(
        ...,
        min_length=1,
        description="The user's chat message",
    )
    history: list[dict] = Field(
        default_factory=list,
        description="Previous chat messages [{role: 'user'|'assistant', content: str}]",
    )
    context: Optional[dict] = Field(
        default=None,
        description="Full session context (raw_prompt, variants, gap_data, answers, etc.)",
    )
    provider: str = Field(
        default="anthropic",
        description="The LLM provider to use (anthropic, openai, google)",
    )
    model_id: str = Field(
        default="claude-sonnet-4-6",
        description="The model ID to use for chat",
    )
    api_key: str = Field(
        ...,
        min_length=1,
        description="API key for the LLM provider",
    )
