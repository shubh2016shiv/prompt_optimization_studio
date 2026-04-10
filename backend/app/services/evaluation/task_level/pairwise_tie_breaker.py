"""
Pairwise tie-break judge for near-equal variant scores.

Why this module exists:
  Pairwise comparison is helpful when top variants are close, but we want this
  logic isolated so it does not leak into baseline deterministic/rubric scoring.

Association with other modules:
  - Consumed by:
      task_level_evaluation.py
"""

from __future__ import annotations

import json
from typing import Any, Literal

import structlog

from app.config import Settings
from app.services.json_extractor import extract_json_from_llm_response
from app.services.llm_client import LLMClient

logger = structlog.get_logger(__name__)


class PairwiseTieBreakerJudge:
    """
    Compare two candidate outputs for a single case and pick winner A/B/TIE.
    """

    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings

    async def compare_outputs_for_case(
        self,
        *,
        llm_client: LLMClient,
        provider: str,
        model_id: str,
        case_input_text: str,
        expected_output_reference: Any,
        candidate_a_output_text: str,
        candidate_b_output_text: str,
    ) -> Literal["A", "B", "TIE"]:
        """
        Evaluate candidate A vs B for one dataset case.

        Returns:
          "A", "B", or "TIE".
        """
        pairwise_prompt = (
            "Compare candidate A and candidate B against the expected output.\n"
            "Return ONLY valid JSON: {\"winner\": \"A|B|TIE\"}.\n\n"
            f"<task_input>\n{case_input_text}\n</task_input>\n\n"
            f"<expected_output>\n{json.dumps(expected_output_reference, ensure_ascii=True)}\n</expected_output>\n\n"
            f"<candidate_a>\n{candidate_a_output_text}\n</candidate_a>\n\n"
            f"<candidate_b>\n{candidate_b_output_text}\n</candidate_b>\n"
        )
        pairwise_system_prompt = (
            "You are a strict evaluator. "
            "Prefer factual correctness and constraint adherence over writing style."
        )
        try:
            pairwise_response_text = await llm_client.call(
                provider=provider,
                prompt=pairwise_prompt,
                max_tokens=self._settings.max_tokens_task_evaluation_judging,
                model=model_id,
                system=pairwise_system_prompt,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            pairwise_payload = extract_json_from_llm_response(pairwise_response_text)
            winner_value = str(pairwise_payload.get("winner", "TIE")).upper()
            if winner_value in ("A", "B"):
                return winner_value
        except Exception as pairwise_error:
            logger.warning(
                "optimize.task_evaluation.pairwise_judge_failed",
                error=str(pairwise_error),
            )
        return "TIE"

