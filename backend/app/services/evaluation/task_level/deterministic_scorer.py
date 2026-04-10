"""
Deterministic case scorer for task-level evaluation.

Why this module exists:
  Deterministic scoring should remain fast, explainable, and independent from
  LLM judge variability. Splitting it into its own module keeps deterministic
  logic easy to test and evolve.

Association with other modules:
  - Consumed by:
      task_level_evaluation.py
  - Uses shared contracts from:
      contracts.py
  - Uses JSON extraction helper from:
      app.services.json_extractor
"""

from __future__ import annotations

import json
import re
from statistics import mean
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from app.config import Settings
from app.services.evaluation.task_level.contracts import DeterministicCaseScore
from app.services.json_extractor import JSONExtractionError, extract_json_from_llm_response


class DeterministicTaskScorer:
    """
    Deterministic evaluator for objective, verifiable case-level checks.

    The scorer intentionally prefers deterministic evidence first. Rubric
    judging is requested only when deterministic similarity is ambiguous.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def score_generated_output(
        self,
        *,
        generated_output_text: str,
        expected_output_reference: Any,
        expected_output_json_schema: dict[str, Any] | None = None,
    ) -> DeterministicCaseScore:
        """
        Score one generated output against the expected output reference.

        Args:
          generated_output_text:
            Output produced by one variant for one evaluation case.
          expected_output_reference:
            Canonical expected output from evaluation_dataset.
          expected_output_json_schema:
            Optional JSON Schema to enforce structural validity deterministically.
        """
        if isinstance(expected_output_reference, (dict, list)):
            return self._score_structured_output(
                generated_output_text=generated_output_text,
                expected_output_reference=expected_output_reference,
                expected_output_json_schema=expected_output_json_schema,
            )

        return self._score_text_output(
            generated_output_text=generated_output_text,
            expected_output_reference=expected_output_reference,
        )

    def _score_text_output(
        self,
        *,
        generated_output_text: str,
        expected_output_reference: Any,
    ) -> DeterministicCaseScore:
        """
        Deterministic text scoring with escalating strictness.

        This method handles exact/normalized/token-overlap logic for plain-text
        tasks. Ambiguous matches are escalated to rubric judging.
        """
        expected_text = str(expected_output_reference).strip()
        actual_text = generated_output_text.strip()
        if actual_text == expected_text:
            return DeterministicCaseScore(score=100, should_use_rubric=False, failure_reason=None)

        normalized_expected_text = self._normalize_text(expected_text)
        normalized_actual_text = self._normalize_text(actual_text)
        if normalized_actual_text == normalized_expected_text:
            return DeterministicCaseScore(score=95, should_use_rubric=False, failure_reason=None)

        token_overlap_ratio = self._calculate_token_overlap_ratio(
            normalized_expected_text=normalized_expected_text,
            normalized_actual_text=normalized_actual_text,
        )
        deterministic_score = int(round(token_overlap_ratio * 100))
        if token_overlap_ratio >= 0.9:
            return DeterministicCaseScore(
                score=max(85, deterministic_score),
                should_use_rubric=False,
                failure_reason=None,
            )
        if token_overlap_ratio >= 0.45:
            return DeterministicCaseScore(
                score=max(40, deterministic_score),
                should_use_rubric=True,
                failure_reason=None,
            )
        return DeterministicCaseScore(
            score=max(5, deterministic_score),
            should_use_rubric=False,
            failure_reason="semantic_mismatch",
        )

    def _score_structured_output(
        self,
        *,
        generated_output_text: str,
        expected_output_reference: dict[str, Any] | list[Any],
        expected_output_json_schema: dict[str, Any] | None,
    ) -> DeterministicCaseScore:
        """
        Deterministic structured scoring for JSON-like tasks.

        If a JSON Schema is supplied, schema validity is enforced before
        structural similarity scoring so objective contract violations fail fast.
        """
        parsed_output_value = self._extract_structured_value(generated_output_text)
        if parsed_output_value is None:
            return DeterministicCaseScore(
                score=0,
                should_use_rubric=False,
                failure_reason="invalid_structured_output",
            )

        if expected_output_json_schema is not None:
            if not self._is_schema_valid_for_output(
                expected_output_json_schema=expected_output_json_schema,
                parsed_output_value=parsed_output_value,
            ):
                return DeterministicCaseScore(
                    score=0,
                    should_use_rubric=False,
                    failure_reason="json_schema_validation_failed",
                )

        structural_similarity = self._calculate_structural_similarity(
            expected_value=expected_output_reference,
            actual_value=parsed_output_value,
        )
        structured_score = int(round(structural_similarity * 100))
        if structural_similarity >= 0.99:
            return DeterministicCaseScore(
                score=100,
                should_use_rubric=False,
                failure_reason=None,
            )

        failure_reason = None
        if structured_score < self._settings.task_evaluation_case_pass_threshold:
            failure_reason = "structured_value_mismatch"
        return DeterministicCaseScore(
            score=structured_score,
            should_use_rubric=False,
            failure_reason=failure_reason,
        )

    def _extract_structured_value(self, generated_output_text: str) -> Any | None:
        """
        Parse JSON content from model output.

        The extraction strategy intentionally tolerates markdown fences and
        wrapper text so deterministic checks stay robust in real LLM outputs.
        """
        trimmed_output = generated_output_text.strip()
        try:
            return json.loads(trimmed_output)
        except json.JSONDecodeError:
            pass

        try:
            return extract_json_from_llm_response(trimmed_output)
        except JSONExtractionError:
            pass

        json_array_match = re.search(r"\[[\s\S]*\]", trimmed_output)
        if json_array_match:
            try:
                return json.loads(json_array_match.group())
            except json.JSONDecodeError:
                return None
        return None

    def _is_schema_valid_for_output(
        self,
        *,
        expected_output_json_schema: dict[str, Any],
        parsed_output_value: Any,
    ) -> bool:
        """
        Validate parsed output against caller-supplied JSON Schema.

        Validation is deterministic and binary by design:
          - valid -> continue with similarity scoring
          - invalid -> fail case deterministically
        """
        validator = Draft202012Validator(expected_output_json_schema)
        try:
            validator.validate(parsed_output_value)
            return True
        except ValidationError:
            return False

    def _calculate_structural_similarity(self, expected_value: Any, actual_value: Any) -> float:
        """Recursively compute structural similarity in the range [0.0, 1.0]."""
        if isinstance(expected_value, dict):
            if not isinstance(actual_value, dict):
                return 0.0
            expected_keys = list(expected_value.keys())
            if not expected_keys:
                return 1.0
            per_key_scores = [
                self._calculate_structural_similarity(
                    expected_value=expected_value[key],
                    actual_value=actual_value.get(key),
                )
                if key in actual_value
                else 0.0
                for key in expected_keys
            ]
            return float(mean(per_key_scores))

        if isinstance(expected_value, list):
            if not isinstance(actual_value, list):
                return 0.0
            if not expected_value:
                return 1.0
            compared_items_count = min(len(expected_value), len(actual_value))
            if compared_items_count == 0:
                return 0.0
            paired_scores = [
                self._calculate_structural_similarity(
                    expected_value=expected_value[index],
                    actual_value=actual_value[index],
                )
                for index in range(compared_items_count)
            ]
            coverage_penalty = compared_items_count / len(expected_value)
            return float(mean(paired_scores) * coverage_penalty)

        if expected_value is None and actual_value is None:
            return 1.0
        return 1.0 if str(expected_value).strip() == str(actual_value).strip() else 0.0

    def _normalize_text(self, text_value: str) -> str:
        """Normalize text before deterministic text comparisons."""
        lowercase_text = text_value.lower()
        collapsed_whitespace_text = re.sub(r"\s+", " ", lowercase_text).strip()
        return re.sub(r"[^\w\s]", "", collapsed_whitespace_text)

    def _calculate_token_overlap_ratio(
        self,
        *,
        normalized_expected_text: str,
        normalized_actual_text: str,
    ) -> float:
        """Compute expected-token coverage ratio in the actual output."""
        expected_tokens = set(normalized_expected_text.split())
        actual_tokens = set(normalized_actual_text.split())
        if not expected_tokens:
            return 0.0
        matched_tokens = expected_tokens.intersection(actual_tokens)
        return len(matched_tokens) / len(expected_tokens)

