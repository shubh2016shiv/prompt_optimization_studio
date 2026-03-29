"""
Prompt Quality Critic — Internal Critique-and-Enhance Driver

This service is the quality gate that sits inside every framework's
optimization loop. It ensures each generated prompt variant is objectively
good before it reaches the user.

RESPONSIBILITIES:
  1. critique_prompt()          — Evaluate a system prompt against 7 dimensions
                                   using G-Eval CoT binary checklist decomposition.
  2. enhance_prompt_from_critique() — Surgically improve a prompt by addressing
                                   specific weaknesses identified by the critique.

DESIGN DECISIONS:
  - Uses gpt-4.1-nano as a FIXED judge model (fast, cheap, cross-provider consistent).
  - The judge is always a DIFFERENT model from the user's target model, avoiding
    self-evaluation bias.
  - Binary checklist decomposition (not direct 1-100 rating) because research shows
    ~40% higher human-alignment with decomposed evaluation.
  - Graceful degradation: if any LLM call fails, returns a default CritiqueResult
    that passes the quality gate (never blocks the user).

USAGE (inside a framework optimizer):
    critic = PromptQualityCritic()
    critique = await critic.critique_prompt(system_prompt, raw_prompt, task_type, llm_client)
    if not critique.passed_quality_gate:
        enhanced_prompt = await critic.enhance_prompt_from_critique(
            system_prompt, critique, task_type, llm_client
        )
"""

import logging
from typing import Any

from app.services.evaluation.critique_result import CritiqueResult, DimensionScores
from app.services.evaluation.evaluation_rubric import (
    QUALITY_GATE_THRESHOLD,
    DIMENSION_WEIGHTS,
    LLM_JUDGE_PROVIDER,
    LLM_JUDGE_MODEL,
    MAX_TOKENS_CRITIQUE,
    MAX_TOKENS_ENHANCEMENT,
    CRITIQUE_SYSTEM_PROMPT,
    CRITIQUE_USER_PROMPT_TEMPLATE,
    ENHANCEMENT_SYSTEM_PROMPT,
    ENHANCEMENT_USER_PROMPT_TEMPLATE,
    score_to_grade,
)
from app.services.llm_client import LLMClient
from app.services.json_extractor import extract_json_from_llm_response

logger = logging.getLogger(__name__)


class PromptQualityCritic:
    """
    Evaluates and enhances prompt variants using G-Eval CoT decomposition.

    This is a stateless service — instantiate it, call its methods, discard it.
    All state is in the CritiqueResult it returns.
    """

    # ──────────────────────────────────────────────────────────────────────
    # Public Method 1: Critique a prompt
    # ──────────────────────────────────────────────────────────────────────

    async def critique_prompt(
        self,
        system_prompt: str,
        raw_prompt: str,
        task_type: str,
        llm_client: LLMClient,
    ) -> CritiqueResult:
        """
        Evaluate a system prompt against the 7-dimension quality rubric.

        The judge model (gpt-4.1-nano) is forced to reason through binary
        checklist questions for each dimension before assigning scores.
        This G-Eval decomposition produces scores with ~40% higher
        human-alignment than direct numerical rating.

        Args:
            system_prompt: The optimised system prompt variant to evaluate.
            raw_prompt: The user's original, unoptimised prompt (for comparison).
            task_type: The task type (reasoning, extraction, etc.) for context.
            llm_client: An active LLMClient instance for making the judge call.

        Returns:
            CritiqueResult with scores, weaknesses, and enhancement suggestions.
            On failure, returns a default result that passes the quality gate.
        """
        critique_user_prompt = CRITIQUE_USER_PROMPT_TEMPLATE.format(
            raw_prompt=raw_prompt.strip(),
            system_prompt=system_prompt.strip(),
        )

        try:
            judge_response_text = await llm_client.call(
                provider=LLM_JUDGE_PROVIDER,
                prompt=critique_user_prompt,
                max_tokens=MAX_TOKENS_CRITIQUE,
                model=LLM_JUDGE_MODEL,
                system=CRITIQUE_SYSTEM_PROMPT,
            )

            parsed_response = extract_json_from_llm_response(judge_response_text)
            return self._parse_critique_response(parsed_response)

        except Exception as critique_error:
            logger.warning(
                "PromptQualityCritic.critique_prompt() failed (%s). "
                "Returning default passing result to avoid blocking the user.",
                critique_error,
            )
            return self._create_default_passing_result()

    # ──────────────────────────────────────────────────────────────────────
    # Public Method 2: Enhance a prompt based on critique
    # ──────────────────────────────────────────────────────────────────────

    async def enhance_prompt_from_critique(
        self,
        system_prompt: str,
        critique: CritiqueResult,
        task_type: str,
        llm_client: LLMClient,
    ) -> str:
        """
        Surgically improve a system prompt by addressing specific weaknesses.

        This is NOT a generic "make it better" rewrite — it takes the exact
        weaknesses identified by critique_prompt() and produces targeted
        additions that fix those specific gaps while preserving all existing
        content.

        Args:
            system_prompt: The current system prompt to improve.
            critique: The CritiqueResult from critique_prompt().
            task_type: The task type for context.
            llm_client: An active LLMClient instance.

        Returns:
            The enhanced system prompt string. On failure, returns the
            original system_prompt unchanged.
        """
        if not critique.weaknesses and not critique.enhancement_suggestions:
            logger.debug("No weaknesses or suggestions — skipping enhancement.")
            return system_prompt

        weaknesses_text = "\n".join(f"- {w}" for w in critique.weaknesses)
        suggestions_text = "\n".join(f"- {s}" for s in critique.enhancement_suggestions)

        enhancement_user_prompt = ENHANCEMENT_USER_PROMPT_TEMPLATE.format(
            system_prompt=system_prompt.strip(),
            weaknesses=weaknesses_text,
            suggestions=suggestions_text,
            task_type=task_type,
        )

        try:
            enhanced_text = await llm_client.call(
                provider=LLM_JUDGE_PROVIDER,
                prompt=enhancement_user_prompt,
                max_tokens=MAX_TOKENS_ENHANCEMENT,
                model=LLM_JUDGE_MODEL,
                system=ENHANCEMENT_SYSTEM_PROMPT,
            )

            # Validate that the enhancement didn't return empty or truncated
            if not enhanced_text or len(enhanced_text.strip()) < len(system_prompt) * 0.5:
                logger.warning(
                    "Enhancement returned suspiciously short text (%d chars vs original %d). "
                    "Keeping original.",
                    len(enhanced_text) if enhanced_text else 0,
                    len(system_prompt),
                )
                return system_prompt

            logger.info(
                "Prompt enhanced: %d → %d chars (delta: +%d)",
                len(system_prompt),
                len(enhanced_text.strip()),
                len(enhanced_text.strip()) - len(system_prompt),
            )
            return enhanced_text.strip()

        except Exception as enhance_error:
            logger.warning(
                "PromptQualityCritic.enhance_prompt_from_critique() failed (%s). "
                "Keeping original prompt.",
                enhance_error,
            )
            return system_prompt

    # ──────────────────────────────────────────────────────────────────────
    # Internal: Parse the judge's JSON response into CritiqueResult
    # ──────────────────────────────────────────────────────────────────────

    def _parse_critique_response(self, parsed_json: dict[str, Any]) -> CritiqueResult:
        """
        Convert the raw JSON from the judge model into a typed CritiqueResult.

        Applies dimension weights to compute the overall score, clamps all
        values to 0–100, and determines whether the quality gate is passed.
        """
        raw_dimensions = parsed_json.get("dimensions", {})

        dimensions = DimensionScores(
            role_clarity=self._clamp_score(raw_dimensions.get("role_clarity", 0)),
            task_specificity=self._clamp_score(raw_dimensions.get("task_specificity", 0)),
            constraint_completeness=self._clamp_score(raw_dimensions.get("constraint_completeness", 0)),
            output_format=self._clamp_score(raw_dimensions.get("output_format", 0)),
            hallucination_resistance=self._clamp_score(raw_dimensions.get("hallucination_resistance", 0)),
            edge_case_handling=self._clamp_score(raw_dimensions.get("edge_case_handling", 0)),
            improvement_over_raw=self._clamp_score(raw_dimensions.get("improvement_over_raw", 0)),
        )

        # Sanity check: if ALL dimensions parsed to 0, the judge response was
        # likely malformed (empty dimensions dict, wrong key names, etc.).
        # Return the default passing result rather than a bogus all-zero critique.
        all_zero = all(
            score == 0
            for score in [
                dimensions.role_clarity,
                dimensions.task_specificity,
                dimensions.constraint_completeness,
                dimensions.output_format,
                dimensions.hallucination_resistance,
                dimensions.edge_case_handling,
                dimensions.improvement_over_raw,
            ]
        )
        if all_zero:
            logger.warning(
                "All dimension scores parsed to 0 — likely malformed judge response. "
                "Falling back to default passing result."
            )
            return self._create_default_passing_result()

        overall_score = self._compute_weighted_overall_score(dimensions)

        return CritiqueResult(
            overall_score=overall_score,
            dimensions=dimensions,
            weaknesses=parsed_json.get("weaknesses", []),
            enhancement_suggestions=parsed_json.get("enhancement_suggestions", []),
            strengths=parsed_json.get("strengths", []),
            reasoning=parsed_json.get("reasoning", ""),
            passed_quality_gate=overall_score >= QUALITY_GATE_THRESHOLD,
        )

    def _compute_weighted_overall_score(self, dimensions: DimensionScores) -> int:
        """
        Compute the weighted average across all 7 dimensions.

        Task Specificity and Constraint Completeness get 1.5× weight because
        they have the highest correlation with downstream execution quality.
        """
        weighted_sum = 0.0
        total_weight = 0.0

        dimension_values = {
            "role_clarity": dimensions.role_clarity,
            "task_specificity": dimensions.task_specificity,
            "constraint_completeness": dimensions.constraint_completeness,
            "output_format": dimensions.output_format,
            "hallucination_resistance": dimensions.hallucination_resistance,
            "edge_case_handling": dimensions.edge_case_handling,
            "improvement_over_raw": dimensions.improvement_over_raw,
        }

        for dimension_name, score in dimension_values.items():
            weight = DIMENSION_WEIGHTS.get(dimension_name, 1.0)
            weighted_sum += score * weight
            total_weight += weight

        if total_weight == 0:
            return 0

        return int(round(weighted_sum / total_weight))

    # ──────────────────────────────────────────────────────────────────────
    # Internal: Default result when critique fails
    # ──────────────────────────────────────────────────────────────────────

    def _create_default_passing_result(self) -> CritiqueResult:
        """
        Return a default CritiqueResult that passes the quality gate.

        Used when the judge LLM call fails — ensures the optimization
        pipeline never blocks on a critique failure.
        """
        return CritiqueResult(
            overall_score=QUALITY_GATE_THRESHOLD,
            dimensions=DimensionScores(
                role_clarity=QUALITY_GATE_THRESHOLD,
                task_specificity=QUALITY_GATE_THRESHOLD,
                constraint_completeness=QUALITY_GATE_THRESHOLD,
                output_format=QUALITY_GATE_THRESHOLD,
                hallucination_resistance=QUALITY_GATE_THRESHOLD,
                edge_case_handling=QUALITY_GATE_THRESHOLD,
                improvement_over_raw=QUALITY_GATE_THRESHOLD,
            ),
            weaknesses=[],
            enhancement_suggestions=[],
            strengths=[],
            reasoning="Critique unavailable — default scores assigned.",
            passed_quality_gate=True,
        )

    @staticmethod
    def _clamp_score(value: Any) -> int:
        """Clamp a value to the 0–100 range, handling non-numeric input."""
        try:
            return max(0, min(100, int(value)))
        except (ValueError, TypeError):
            return 0
