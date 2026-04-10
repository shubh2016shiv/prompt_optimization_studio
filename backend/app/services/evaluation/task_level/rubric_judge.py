"""
Rubric-based judge for semantically ambiguous task-evaluation cases.

Why this module exists:
  Deterministic scoring cannot reliably grade open-ended outputs (summaries,
  explanations, nuanced reasoning). This judge provides a strict rubric pass
  using the caller-selected model while keeping retry and failure handling
  explicit.

Association with other modules:
  - Consumed by:
      task_level_evaluation.py
  - Uses retry policy from:
      retry_policy.py
  - Uses LLM transport from:
      app.services.llm_client.LLMClient
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.config import Settings
from app.services.evaluation.task_level.contracts import RubricCaseScore
from app.services.evaluation.task_level.retry_policy import TaskEvaluationRetryPolicy
from app.services.json_extractor import extract_json_from_llm_response
from app.services.llm_client import LLMClient

logger = structlog.get_logger(__name__)


class RubricTaskJudge:
    """
    LLM judge that scores one case with a strict JSON rubric output.

    Reliability guards:
      - bounded retry for transient provider failures (for example HTTP 429)
      - strict JSON extraction
      - explicit failure reason when judging is unavailable
    """

    def __init__(
        self,
        *,
        settings: Settings,
        retry_policy: TaskEvaluationRetryPolicy,
    ) -> None:
        self._settings = settings
        self._retry_policy = retry_policy

    async def score_case_with_rubric(
        self,
        *,
        llm_client: LLMClient,
        provider: str,
        model_id: str,
        case_input_text: str,
        expected_output_reference: Any,
        generated_output_text: str,
    ) -> RubricCaseScore:
        """
        Evaluate one case output via rubric judging.

        Returns:
          RubricCaseScore with normalized score and optional failure reason.
        """
        rubric_prompt = (
            "Evaluate the model output against the expected output for the task input.\n"
            "Score from 0 to 100.\n"
            "Return ONLY valid JSON with keys: score, failure_reason.\n\n"
            f"<task_input>\n{case_input_text}\n</task_input>\n\n"
            f"<expected_output>\n{json.dumps(expected_output_reference, ensure_ascii=True)}\n</expected_output>\n\n"
            f"<generated_output>\n{generated_output_text}\n</generated_output>\n"
        )
        rubric_system_prompt = (
            "You are a strict task evaluator. "
            "Do not reward style when correctness is weak. "
            "Use score 70+ only when the task is materially satisfied."
        )

        async def execute_judge_call() -> str:
            return await llm_client.call(
                provider=provider,
                prompt=rubric_prompt,
                max_tokens=self._settings.max_tokens_task_evaluation_judging,
                model=model_id,
                system=rubric_system_prompt,
                temperature=0.0,
                response_format={"type": "json_object"},
            )

        try:
            rubric_response_text = await self._retry_policy.execute_with_retry(
                operation_name="task_evaluation.rubric_judge",
                operation=execute_judge_call,
                log_context={
                    "provider": provider,
                    "model_id": model_id,
                },
            )
            rubric_payload = extract_json_from_llm_response(rubric_response_text)
            raw_score_value = rubric_payload.get("score", 0)
            normalized_score = int(max(0, min(100, int(raw_score_value))))
            failure_reason = rubric_payload.get("failure_reason")
            normalized_failure_reason = (
                failure_reason.strip()
                if isinstance(failure_reason, str) and failure_reason.strip()
                else None
            )
            return RubricCaseScore(
                score=normalized_score,
                failure_reason=normalized_failure_reason,
            )
        except Exception as rubric_error:
            logger.warning(
                "optimize.task_evaluation.rubric_judge_failed",
                error=str(rubric_error),
                provider=provider,
                model_id=model_id,
            )
            return RubricCaseScore(
                score=0,
                failure_reason="rubric_judge_unavailable",
            )

