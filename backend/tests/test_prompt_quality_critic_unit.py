import json

import pytest

from app.services.evaluation.prompt_quality_critic import PromptQualityCritic


class CaptureLLMClient:
    def __init__(self) -> None:
        self.last_call_kwargs = {}

    async def call(self, **kwargs):
        self.last_call_kwargs = kwargs
        return json.dumps(
            {
                "reasoning": "Looks solid.",
                "dimensions": {
                    "role_clarity": 80,
                    "task_specificity": 80,
                    "constraint_completeness": 80,
                    "output_format": 80,
                    "hallucination_resistance": 80,
                    "edge_case_handling": 80,
                    "improvement_over_raw": 80,
                },
                "strengths": ["clear role"],
                "weaknesses": [],
                "enhancement_suggestions": [],
            }
        )


class FailingLLMClient:
    async def call(self, **kwargs):
        raise RuntimeError("judge unavailable")


class ZeroScoreLLMClient:
    async def call(self, **kwargs):
        return json.dumps(
            {
                "reasoning": "Malformed dimensions.",
                "dimensions": {
                    "role_clarity": 0,
                    "task_specificity": 0,
                    "constraint_completeness": 0,
                    "output_format": 0,
                    "hallucination_resistance": 0,
                    "edge_case_handling": 0,
                    "improvement_over_raw": 0,
                },
                "strengths": [],
                "weaknesses": [],
                "enhancement_suggestions": [],
            }
        )


@pytest.mark.asyncio
async def test_critique_prompt_uses_temperature_zero_and_includes_task_type():
    critic = PromptQualityCritic()
    client = CaptureLLMClient()

    result = await critic.critique_prompt(
        system_prompt="You are a helpful assistant.",
        raw_prompt="Summarize the report.",
        task_type="summarization",
        llm_client=client,
    )

    assert client.last_call_kwargs["temperature"] == 0.0
    assert "=== TASK TYPE ===\nsummarization" in client.last_call_kwargs["prompt"]
    assert result.was_fallback is False


@pytest.mark.asyncio
async def test_critique_prompt_returns_explicit_fallback_on_failure():
    critic = PromptQualityCritic()
    client = FailingLLMClient()

    result = await critic.critique_prompt(
        system_prompt="You are a helpful assistant.",
        raw_prompt="Summarize the report.",
        task_type="summarization",
        llm_client=client,
    )

    assert result.was_fallback is True
    assert result.passed_quality_gate is False
    assert result.overall_score == 0
    assert "Critique unavailable" in result.reasoning


@pytest.mark.asyncio
async def test_critique_prompt_marks_all_zero_dimensions_as_fallback():
    critic = PromptQualityCritic()
    client = ZeroScoreLLMClient()

    result = await critic.critique_prompt(
        system_prompt="You are a helpful assistant.",
        raw_prompt="Summarize the report.",
        task_type="summarization",
        llm_client=client,
    )

    assert result.was_fallback is True
    assert result.passed_quality_gate is False
    assert "all-zero dimensions" in result.reasoning
