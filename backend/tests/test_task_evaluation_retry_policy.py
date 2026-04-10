"""Tests for rubric-judge retry behavior in task-level evaluation."""

import pytest

from app.config import get_settings
from app.services.evaluation.task_level.retry_policy import TaskEvaluationRetryPolicy
from app.services.evaluation.task_level.rubric_judge import RubricTaskJudge
from app.services.llm_client import LLMClientError


def _build_retry_friendly_settings():
    """Create settings copy with near-zero retry delays for fast tests."""
    settings = get_settings().model_copy(deep=True)
    settings.task_evaluation_judge_retry_attempts = 3
    settings.task_evaluation_judge_retry_base_delay_seconds = 0.0
    settings.task_evaluation_judge_retry_max_delay_seconds = 0.0
    settings.task_evaluation_judge_retry_jitter_seconds = 0.0
    return settings


@pytest.mark.asyncio
async def test_rubric_judge_retries_transient_429_then_succeeds():
    """Transient 429 failures should be retried before returning a score."""
    settings = _build_retry_friendly_settings()
    retry_policy = TaskEvaluationRetryPolicy(settings)
    rubric_judge = RubricTaskJudge(settings=settings, retry_policy=retry_policy)

    class FakeLLMClient:
        def __init__(self) -> None:
            self.call_count = 0

        async def call(self, **kwargs):
            self.call_count += 1
            if self.call_count < 3:
                raise LLMClientError("Rate limited", status_code=429)
            return '{"score": 84, "failure_reason": ""}'

    fake_llm_client = FakeLLMClient()
    case_score = await rubric_judge.score_case_with_rubric(
        llm_client=fake_llm_client,  # type: ignore[arg-type]
        provider="openai",
        model_id="gpt-4.1-mini",
        case_input_text="Input",
        expected_output_reference="Expected output",
        generated_output_text="Generated output",
    )

    assert fake_llm_client.call_count == 3
    assert case_score.score == 84
    assert case_score.failure_reason is None


@pytest.mark.asyncio
async def test_rubric_judge_does_not_retry_non_transient_failures():
    """Non-transient failures should fail fast without retries."""
    settings = _build_retry_friendly_settings()
    retry_policy = TaskEvaluationRetryPolicy(settings)
    rubric_judge = RubricTaskJudge(settings=settings, retry_policy=retry_policy)

    class FakeLLMClient:
        def __init__(self) -> None:
            self.call_count = 0

        async def call(self, **kwargs):
            self.call_count += 1
            raise LLMClientError("Bad request", status_code=400)

    fake_llm_client = FakeLLMClient()
    case_score = await rubric_judge.score_case_with_rubric(
        llm_client=fake_llm_client,  # type: ignore[arg-type]
        provider="openai",
        model_id="gpt-4.1-mini",
        case_input_text="Input",
        expected_output_reference="Expected output",
        generated_output_text="Generated output",
    )

    assert fake_llm_client.call_count == 1
    assert case_score.score == 0
    assert case_score.failure_reason == "rubric_judge_unavailable"

