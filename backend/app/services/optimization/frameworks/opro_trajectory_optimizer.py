"""
OPRO trajectory optimizer.

OPRO (Optimization by PROmpting) treats prompt optimization as black-box
search: keep a history of prompts with empirical scores, ask an LLM to propose
new prompts from that trajectory, evaluate the proposals, and repeat.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re
from typing import Any, Iterable, Optional

from app.models.requests import EvaluationDatasetCase, OptimizationRequest
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)
from app.services.evaluation.task_level_evaluation import TaskLevelEvaluationService
from app.services.json_extractor import JSONExtractionError, extract_json_from_llm_response
from app.services.llm_client import LLMClient
from app.services.optimization.base import BaseOptimizerStrategy
from app.services.optimization.optimizer_configuration import (
    MAX_TOKENS_OPRO_PROPOSAL,
    OPRO_CANDIDATES_PER_ITERATION,
    OPRO_DEFAULT_ITERATION_COUNT,
    OPRO_EXEMPLARS_IN_META_PROMPT,
    OPRO_MAX_TRAINING_CASES,
    OPRO_PROPOSAL_TEMPERATURE,
    OPRO_TRAJECTORY_KEEP_TOP,
    SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
)
from app.services.optimization.shared_prompt_techniques import (
    compute_coverage_delta_description,
    generate_claude_prefill_suggestion,
    inject_input_variables_block,
    integrate_gap_interview_answers_into_prompt,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OproTrajectoryEntry:
    """One prompt-score pair retained in the OPRO optimization history."""

    prompt_text: str
    score: int
    iteration: int
    source: str
    rationale: str


@dataclass(frozen=True)
class OproCandidate:
    """One candidate proposal returned by the optimizer LLM."""

    system_prompt: str
    rationale: str


_OPRO_PROPOSAL_PROMPT = """
You are running OPRO (Optimization by PROmpting) for system prompt optimization.
Your goal is to propose full replacement SYSTEM PROMPTS that achieve higher
empirical task success scores on the provided evaluation examples.

ORIGINAL RAW PROMPT:
{raw_prompt}

TASK TYPE: {task_type}
TARGET MODEL: {model_label}

EVALUATION EXAMPLES:
{evaluation_examples}

PROMPT-SCORE TRAJECTORY:
The following prior prompts are sorted in ascending score order. Higher score is
better. Learn from the best prompts while still exploring meaningfully different
wording and structure.
{trajectory}

Generate exactly {candidate_count} new candidate system prompts.
Rules:
- Each candidate must be a complete system prompt, not a short instruction.
- Candidates must differ from prior prompts in the trajectory.
- Preserve task intent from the raw prompt.
- Include output constraints and failure-mode guards when useful.
- Do not mention OPRO, scores, or the optimization process in the candidate.

Return ONLY valid JSON:
{{
  "candidates": [
    {{"system_prompt": "complete prompt", "rationale": "why this should score better"}}
  ]
}}
""".strip()


class OproTrajectoryOptimizer(BaseOptimizerStrategy):
    """Empirical prompt optimizer based on prompt-score trajectories."""

    def _select_training_cases(
        self,
        evaluation_dataset: list[EvaluationDatasetCase],
        max_cases: int = OPRO_MAX_TRAINING_CASES,
    ) -> list[EvaluationDatasetCase]:
        """Return a deterministic evenly spaced subset for bounded OPRO scoring."""
        if len(evaluation_dataset) <= max_cases:
            return list(evaluation_dataset)
        if max_cases <= 1:
            return [evaluation_dataset[0]]

        last_index = len(evaluation_dataset) - 1
        indexes = {
            round(position * last_index / (max_cases - 1))
            for position in range(max_cases)
        }
        return [evaluation_dataset[index] for index in sorted(indexes)]

    def _normalize_prompt_for_deduplication(self, prompt_text: str) -> str:
        """Normalize prompt text so semantically identical copies are not re-scored."""
        return re.sub(r"\s+", " ", prompt_text.strip().lower())

    def _format_trajectory_for_meta_prompt(
        self,
        trajectory: list[OproTrajectoryEntry],
    ) -> str:
        """Format top trajectory entries in ascending score order, as in OPRO."""
        retained_entries = sorted(
            trajectory,
            key=lambda entry: (entry.score, entry.iteration, entry.source),
        )[-OPRO_TRAJECTORY_KEEP_TOP:]
        retained_entries = sorted(
            retained_entries,
            key=lambda entry: (entry.score, entry.iteration, entry.source),
        )

        blocks: list[str] = []
        for index, entry in enumerate(retained_entries, start=1):
            blocks.append(
                f"[{index}] score={entry.score}; iteration={entry.iteration}; "
                f"source={entry.source}; rationale={entry.rationale}\n"
                f"PROMPT:\n{entry.prompt_text}"
            )
        return "\n\n---\n\n".join(blocks) if blocks else "No prior prompts scored yet."

    def _format_evaluation_examples(
        self,
        training_cases: list[EvaluationDatasetCase],
    ) -> str:
        """Format a few training examples for the OPRO proposal meta-prompt."""
        examples = training_cases[:OPRO_EXEMPLARS_IN_META_PROMPT]
        formatted: list[str] = []
        for index, evaluation_case in enumerate(examples, start=1):
            expected_output = json.dumps(evaluation_case.expected_output, ensure_ascii=False)
            formatted.append(
                f"Example {index}\n"
                f"INPUT:\n{evaluation_case.input}\n"
                f"EXPECTED OUTPUT:\n{expected_output}"
            )
        return "\n\n".join(formatted) if formatted else "No examples provided."

    async def _propose_candidate_prompts(
        self,
        *,
        request: OptimizationRequest,
        enriched_prompt: str,
        training_cases: list[EvaluationDatasetCase],
        trajectory: list[OproTrajectoryEntry],
        candidate_count: int,
    ) -> list[OproCandidate]:
        """Ask the user's selected model to propose full prompt candidates."""
        proposal_prompt = _OPRO_PROPOSAL_PROMPT.format(
            raw_prompt=enriched_prompt,
            task_type=request.task_type,
            model_label=request.model_label,
            evaluation_examples=self._format_evaluation_examples(training_cases),
            trajectory=self._format_trajectory_for_meta_prompt(trajectory),
            candidate_count=candidate_count,
        )

        async with LLMClient(api_key=request.api_key) as llm_client:
            response_text = await llm_client.call(
                provider=request.provider,
                prompt=proposal_prompt,
                max_tokens=MAX_TOKENS_OPRO_PROPOSAL,
                model=request.model_id,
                system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
                temperature=OPRO_PROPOSAL_TEMPERATURE,
                response_format={"type": "json_object"},
            )

        parsed_response = extract_json_from_llm_response(response_text)
        if isinstance(parsed_response, list):
            raw_candidates = parsed_response
        elif isinstance(parsed_response, dict):
            raw_candidates = parsed_response.get("candidates", [])
        else:
            raw_candidates = []

        candidates: list[OproCandidate] = []
        for raw_candidate in raw_candidates:
            if not isinstance(raw_candidate, dict):
                continue
            system_prompt = str(raw_candidate.get("system_prompt", "")).strip()
            if not system_prompt:
                continue
            candidates.append(
                OproCandidate(
                    system_prompt=system_prompt,
                    rationale=str(raw_candidate.get("rationale", "OPRO candidate proposal.")).strip(),
                )
            )
        return candidates[:candidate_count]

    async def _score_candidate_prompt(
        self,
        *,
        request: OptimizationRequest,
        candidate_prompt: str,
        training_cases: list[EvaluationDatasetCase],
    ) -> int:
        """Score one prompt by reusing the existing task-level evaluator."""
        evaluation_request = request.model_copy(update={"evaluation_dataset": training_cases})
        candidate_response = OptimizationResponse(
            analysis=OptimizationAnalysis(
                detected_issues=[],
                model_notes="OPRO internal candidate scoring.",
                framework_applied="opro",
                coverage_delta="Internal OPRO candidate evaluation.",
            ),
            techniques_applied=["OPRO Internal Evaluation"],
            variants=[
                PromptVariant(
                    id=1,
                    name="Candidate",
                    strategy="OPRO candidate scoring",
                    system_prompt=candidate_prompt,
                    user_prompt="[Insert request data here]",
                    token_estimate=len(candidate_prompt) // 4,
                    tcrte_scores=VariantTCRTEScores(
                        task=60,
                        context=60,
                        role=60,
                        tone=60,
                        execution=60,
                    ),
                    strengths=[],
                    best_for="Internal OPRO scoring only.",
                    overshoot_guards=[],
                    undershoot_guards=[],
                )
            ],
        )

        evaluator = TaskLevelEvaluationService()
        await evaluator.evaluate_response_variants(
            optimization_request=evaluation_request,
            optimization_response=candidate_response,
        )
        task_evaluation = candidate_response.variants[0].task_evaluation
        return task_evaluation.task_success_score if task_evaluation is not None else 0

    def _fallback_candidates_from_best(
        self,
        best_prompt: str,
        needed_count: int,
    ) -> list[OproCandidate]:
        """Create deterministic fallbacks when the model returns too few unique candidates."""
        templates = [
            (
                "Add a compact verification step and explicit output contract.",
                "\n\nValidation guard: before final output, verify the response satisfies the requested format and does not add unsupported facts.",
            ),
            (
                "Add stricter scope boundaries and evidence discipline.",
                "\n\nScope guard: use only the provided input, state uncertainty when evidence is insufficient, and avoid broad generalizations.",
            ),
            (
                "Add concise execution controls for repeatable responses.",
                "\n\nExecution guard: keep the answer concise, ordered, and directly aligned to the expected output criteria.",
            ),
        ]
        candidates: list[OproCandidate] = []
        for rationale, suffix in templates[:needed_count]:
            candidates.append(OproCandidate(system_prompt=f"{best_prompt.rstrip()}{suffix}", rationale=rationale))
        return candidates

    def _build_variant_entries(
        self,
        trajectory: list[OproTrajectoryEntry],
    ) -> list[OproTrajectoryEntry]:
        """Map trajectory history into Conservative, Structured, Advanced entries."""
        unique_entries_by_prompt: dict[str, OproTrajectoryEntry] = {}
        for entry in sorted(trajectory, key=lambda item: item.score, reverse=True):
            key = self._normalize_prompt_for_deduplication(entry.prompt_text)
            unique_entries_by_prompt.setdefault(key, entry)

        unique_entries = list(unique_entries_by_prompt.values())
        if not unique_entries:
            raise ValueError("OPRO could not produce any candidate prompts.")

        best_entry = max(unique_entries, key=lambda entry: entry.score)
        selected: list[OproTrajectoryEntry] = []
        selected_keys: set[str] = {
            self._normalize_prompt_for_deduplication(best_entry.prompt_text)
        }

        def pick_best(candidates: Iterable[OproTrajectoryEntry]) -> Optional[OproTrajectoryEntry]:
            available = [
                candidate
                for candidate in candidates
                if self._normalize_prompt_for_deduplication(candidate.prompt_text) not in selected_keys
            ]
            if not available:
                return None
            return max(available, key=lambda entry: entry.score)

        early_entry = pick_best(entry for entry in unique_entries if entry.iteration <= 1) or best_entry
        selected.append(early_entry)
        selected_keys.add(self._normalize_prompt_for_deduplication(early_entry.prompt_text))

        middle_entry = pick_best(
            entry for entry in unique_entries if 1 < entry.iteration < OPRO_DEFAULT_ITERATION_COUNT
        ) or pick_best(unique_entries) or best_entry
        selected.append(middle_entry)
        selected_keys.add(self._normalize_prompt_for_deduplication(middle_entry.prompt_text))

        selected.append(best_entry)

        while len(selected) < 3:
            selected.append(best_entry)

        if len({self._normalize_prompt_for_deduplication(entry.prompt_text) for entry in selected}) < 3:
            best_prompt = best_entry.prompt_text
            for fallback_candidate in self._fallback_candidates_from_best(best_prompt, 3):
                fallback_entry = OproTrajectoryEntry(
                    prompt_text=fallback_candidate.system_prompt,
                    score=best_entry.score,
                    iteration=OPRO_DEFAULT_ITERATION_COUNT,
                    source="fallback",
                    rationale=fallback_candidate.rationale,
                )
                fallback_key = self._normalize_prompt_for_deduplication(fallback_entry.prompt_text)
                if fallback_key not in selected_keys:
                    selected.append(fallback_entry)
                    selected_keys.add(fallback_key)
                if len(selected_keys) >= 3:
                    break

        best_key = self._normalize_prompt_for_deduplication(best_entry.prompt_text)
        conservative_pool = [
            entry
            for entry in selected
            if self._normalize_prompt_for_deduplication(entry.prompt_text) != best_key
        ]
        advanced_pool = [best_entry]
        distinct_selected: list[OproTrajectoryEntry] = []
        seen_keys: set[str] = set()
        for entry in [*conservative_pool, *advanced_pool]:
            key = self._normalize_prompt_for_deduplication(entry.prompt_text)
            if key in seen_keys:
                continue
            distinct_selected.append(entry)
            seen_keys.add(key)
            if len(distinct_selected) == 3:
                break
        return distinct_selected

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[list[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:
        """Run OPRO and return the best three trajectory prompts as variants."""
        if not request.evaluation_dataset:
            raise ValueError(
                "OPRO requires evaluation_dataset because it learns from empirical prompt-score trajectories."
            )

        enriched_prompt = integrate_gap_interview_answers_into_prompt(
            raw_prompt=request.raw_prompt,
            gap_interview_answers=request.answers,
            gap_analysis_data=request.gap_data,
        )
        training_cases = self._select_training_cases(request.evaluation_dataset)
        trajectory: list[OproTrajectoryEntry] = []
        seen_prompts: set[str] = set()
        candidates_evaluated = 0
        iterations_run = 0

        seed_score = await self._score_candidate_prompt(
            request=request,
            candidate_prompt=enriched_prompt,
            training_cases=training_cases,
        )
        trajectory.append(
            OproTrajectoryEntry(
                prompt_text=enriched_prompt,
                score=seed_score,
                iteration=0,
                source="seed",
                rationale="Original enriched prompt baseline.",
            )
        )
        seen_prompts.add(self._normalize_prompt_for_deduplication(enriched_prompt))
        candidates_evaluated += 1

        for iteration_number in range(1, OPRO_DEFAULT_ITERATION_COUNT + 1):
            try:
                proposed_candidates = await self._propose_candidate_prompts(
                    request=request,
                    enriched_prompt=enriched_prompt,
                    training_cases=training_cases,
                    trajectory=trajectory,
                    candidate_count=OPRO_CANDIDATES_PER_ITERATION,
                )
            except JSONExtractionError as proposal_error:
                logger.warning("OPRO proposal JSON parsing failed: %s", proposal_error)
                proposed_candidates = []
            except Exception as proposal_error:
                logger.warning("OPRO proposal failed: %s", proposal_error)
                proposed_candidates = []

            if not proposed_candidates:
                best_prompt = max(trajectory, key=lambda entry: entry.score).prompt_text
                proposed_candidates = self._fallback_candidates_from_best(
                    best_prompt,
                    OPRO_CANDIDATES_PER_ITERATION,
                )

            for candidate in proposed_candidates:
                normalized_prompt = self._normalize_prompt_for_deduplication(candidate.system_prompt)
                if normalized_prompt in seen_prompts:
                    continue
                seen_prompts.add(normalized_prompt)
                score = await self._score_candidate_prompt(
                    request=request,
                    candidate_prompt=candidate.system_prompt,
                    training_cases=training_cases,
                )
                trajectory.append(
                    OproTrajectoryEntry(
                        prompt_text=candidate.system_prompt,
                        score=score,
                        iteration=iteration_number,
                        source="llm_proposal",
                        rationale=candidate.rationale,
                    )
                )
                candidates_evaluated += 1
            iterations_run = iteration_number

        variant_entries = self._build_variant_entries(trajectory)
        variant_names = ["Conservative", "Structured", "Advanced"]
        variant_strategies = [
            "Best early OPRO trajectory prompt from empirical candidate scoring.",
            "Best mid-trajectory prompt balancing structural change and empirical score.",
            "Highest-scoring prompt found across the full OPRO trajectory.",
        ]
        advanced_prefill = generate_claude_prefill_suggestion(request.task_type, request.provider)

        variants: list[PromptVariant] = []
        for index, entry in enumerate(variant_entries, start=1):
            system_prompt = inject_input_variables_block(
                entry.prompt_text,
                request.input_variables,
                request.provider,
            )
            score_floor = max(55, min(95, entry.score))
            variants.append(
                PromptVariant(
                    id=index,
                    name=variant_names[index - 1],
                    strategy=variant_strategies[index - 1],
                    system_prompt=system_prompt.strip(),
                    user_prompt="[Insert request data here]",
                    prefill_suggestion=advanced_prefill if index == 3 else None,
                    token_estimate=len(system_prompt) // 4,
                    tcrte_scores=VariantTCRTEScores(
                        task=min(100, score_floor + 5),
                        context=score_floor,
                        role=max(50, score_floor - 5),
                        tone=max(50, score_floor - 5),
                        execution=min(100, score_floor + 5),
                    ),
                    strengths=[
                        "Empirically scored on evaluation_dataset",
                        f"OPRO trajectory score: {entry.score}",
                    ],
                    best_for="Tasks where real example performance matters more than one-shot prompt style.",
                    overshoot_guards=["Candidate was selected by task-success score, not stylistic complexity."],
                    undershoot_guards=["Trajectory loop proposes and evaluates alternatives before selection."],
                )
            )

        best_score = max(entry.score for entry in trajectory)
        model_notes = (
            f"OPRO ran {iterations_run} iteration(s), evaluated {candidates_evaluated} "
            f"candidate prompt(s), and used {len(training_cases)} bounded training case(s)."
        )
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        response = OptimizationResponse(
            analysis=OptimizationAnalysis(
                detected_issues=[
                    "Prompt quality was optimized through empirical prompt-score trajectory search."
                ],
                model_notes=model_notes,
                framework_applied="opro",
                coverage_delta=compute_coverage_delta_description(request.gap_data, best_score),
                auto_selected_framework="opro" if auto_reason else None,
                auto_reason=auto_reason,
            ),
            techniques_applied=[
                "OPRO",
                "Trajectory-Based Meta-Optimization",
                "Empirical Candidate Scoring",
            ],
            variants=variants,
        )

        response = await self._refine_variants_with_quality_critique(
            response=response,
            raw_prompt=request.raw_prompt,
            task_type=request.task_type,
            api_key=request.api_key,
            quality_gate_mode=request.quality_gate_mode,
            framework="opro",
            target_model=request.model_id,
        )
        if response.run_metadata is not None:
            response.run_metadata.opro_iterations_run = iterations_run
            response.run_metadata.opro_candidates_evaluated = candidates_evaluated
            response.run_metadata.opro_training_cases_used = len(training_cases)
            response.run_metadata.opro_best_score = best_score

        return response
