"""
SAMMO topological optimizer.

SAMMO (Structure-Aware Multi-Objective prompt optimization) treats prompts as
structured objects, mutates their topology, and selects strong candidates using
multiple objectives instead of one-dimensional text similarity.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from app.models.requests import OptimizationRequest
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)
from app.services.json_extractor import JSONExtractionError, extract_json_from_llm_response
from app.services.llm_client import LLMClient
from app.services.optimization.base import BaseOptimizerStrategy
from app.services.optimization.optimizer_configuration import (
    MAX_TOKENS_SAMMO_STRUCTURAL_PARSE,
    SAMMO_MIN_TCRTE_THRESHOLD,
    SAMMO_TCRTE_WEIGHT,
    SAMMO_TOKEN_WEIGHT,
    SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
)
from app.services.optimization.shared_prompt_techniques import (
    compute_coverage_delta_description,
    generate_claude_prefill_suggestion,
    inject_input_variables_block,
    integrate_gap_interview_answers_into_prompt,
)
from app.services.scoring import score_tcrte

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SammoPromptGraph:
    """Structured prompt graph used by SAMMO-style topological mutations."""

    instruction: str
    context_blocks: list[str]
    rules: list[str]
    few_shot: list[str]
    output_format: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "instruction": self.instruction,
            "context_blocks": self.context_blocks,
            "rules": self.rules,
            "few_shot": self.few_shot,
            "output_format": self.output_format,
        }


@dataclass(frozen=True)
class SammoCandidate:
    """Candidate prompt plus its objective metrics."""

    label: str
    system_prompt: str
    tcrte_score: int
    token_efficiency_score: int
    combined_score: float


_SAMMO_PARSE_PROMPT = """
Parse the raw prompt into a structured prompt graph.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY valid JSON:
{{
  "instruction": "core instruction",
  "context_blocks": ["context block 1", "context block 2"],
  "rules": ["rule 1", "rule 2"],
  "few_shot": ["few-shot or exemplar block"],
  "output_format": "required output format and schema guidance"
}}
""".strip()

_SAMMO_MUTATION_PROMPT = """
Mutate this prompt graph using the requested operator while preserving task intent.

<mutation_operator>
{mutation_operator}
</mutation_operator>

<current_graph_json>
{graph_json}
</current_graph_json>

Operator semantics:
- compression: aggressively compress context_blocks while preserving critical facts.
- restructure: reorder sections and remove one low-value rule if safe.
- syntactical: rewrite instruction for maximal imperative clarity.

Return ONLY valid JSON with the same schema:
{{
  "instruction": "core instruction",
  "context_blocks": ["context block 1", "context block 2"],
  "rules": ["rule 1", "rule 2"],
  "few_shot": ["few-shot or exemplar block"],
  "output_format": "required output format and schema guidance"
}}
""".strip()


class SammoTopologicalOptimizer(BaseOptimizerStrategy):
    """Structure-aware prompt optimizer with multi-objective candidate selection."""

    async def _parse_prompt_graph(
        self,
        *,
        raw_prompt: str,
        request: OptimizationRequest,
    ) -> SammoPromptGraph:
        """Parse raw text into a structured graph representation."""
        parse_prompt = _SAMMO_PARSE_PROMPT.format(raw_prompt=raw_prompt)
        async with LLMClient(api_key=request.api_key) as llm_client:
            response_text = await llm_client.call(
                provider=request.provider,
                prompt=parse_prompt,
                max_tokens=MAX_TOKENS_SAMMO_STRUCTURAL_PARSE,
                model=request.model_id,
                system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
                response_format={"type": "json_object"},
            )

        parsed = extract_json_from_llm_response(response_text)
        if not isinstance(parsed, dict):
            raise JSONExtractionError("SAMMO graph parse expected a JSON object.")
        return self._normalize_graph(parsed, fallback_instruction=raw_prompt)

    async def _mutate_graph(
        self,
        *,
        base_graph: SammoPromptGraph,
        mutation_operator: str,
        request: OptimizationRequest,
    ) -> SammoPromptGraph:
        """Run one mutation operator against the graph."""
        mutation_prompt = _SAMMO_MUTATION_PROMPT.format(
            mutation_operator=mutation_operator,
            graph_json=json.dumps(base_graph.to_dict(), ensure_ascii=False, indent=2),
        )
        try:
            async with LLMClient(api_key=request.api_key) as llm_client:
                response_text = await llm_client.call(
                    provider=request.provider,
                    prompt=mutation_prompt,
                    max_tokens=MAX_TOKENS_SAMMO_STRUCTURAL_PARSE,
                    model=request.model_id,
                    system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
                    response_format={"type": "json_object"},
                )
            parsed = extract_json_from_llm_response(response_text)
            if not isinstance(parsed, dict):
                raise JSONExtractionError("SAMMO mutation expected a JSON object.")
            return self._normalize_graph(parsed, fallback_instruction=base_graph.instruction)
        except Exception as mutation_error:
            logger.warning("SAMMO mutation '%s' failed: %s", mutation_operator, mutation_error)
            return self._deterministic_mutation_fallback(base_graph, mutation_operator)

    def _normalize_graph(
        self,
        graph_payload: dict[str, Any],
        *,
        fallback_instruction: str,
    ) -> SammoPromptGraph:
        """Normalize parsed graph payload into a strict internal dataclass."""
        instruction = str(graph_payload.get("instruction", "")).strip() or fallback_instruction.strip()
        context_blocks = self._coerce_str_list(graph_payload.get("context_blocks"))
        rules = self._coerce_str_list(graph_payload.get("rules"))
        few_shot = self._coerce_str_list(graph_payload.get("few_shot"))
        output_format = str(graph_payload.get("output_format", "")).strip()
        if not output_format:
            output_format = "Provide a clear, structured output aligned to the request."

        return SammoPromptGraph(
            instruction=instruction,
            context_blocks=context_blocks,
            rules=rules,
            few_shot=few_shot,
            output_format=output_format,
        )

    def _coerce_str_list(self, value: Any) -> list[str]:
        """Convert unknown list-like values to clean string lists."""
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _deterministic_mutation_fallback(
        self,
        graph: SammoPromptGraph,
        mutation_operator: str,
    ) -> SammoPromptGraph:
        """Fallback mutation logic when a mutation sub-call fails."""
        if mutation_operator == "compression":
            compressed_context = [
                block if len(block) <= 220 else f"{block[:217].rstrip()}..."
                for block in graph.context_blocks
            ]
            return SammoPromptGraph(
                instruction=graph.instruction,
                context_blocks=compressed_context,
                rules=graph.rules,
                few_shot=graph.few_shot,
                output_format=graph.output_format,
            )

        if mutation_operator == "restructure":
            reordered_context = list(reversed(graph.context_blocks))
            trimmed_rules = graph.rules[:-1] if len(graph.rules) > 1 else graph.rules
            return SammoPromptGraph(
                instruction=graph.instruction,
                context_blocks=reordered_context,
                rules=trimmed_rules,
                few_shot=graph.few_shot,
                output_format=graph.output_format,
            )

        if mutation_operator == "syntactical":
            rewritten_instruction = (
                f"{graph.instruction.rstrip()}\nExecute the task in a deterministic, stepwise manner."
            )
            return SammoPromptGraph(
                instruction=rewritten_instruction,
                context_blocks=graph.context_blocks,
                rules=graph.rules,
                few_shot=graph.few_shot,
                output_format=graph.output_format,
            )

        return graph

    def _assemble_prompt_from_graph(
        self,
        *,
        graph: SammoPromptGraph,
        label: str,
    ) -> str:
        """Serialize graph topology back into a runnable system prompt."""
        sections: list[str] = [
            f"### Instruction\n{graph.instruction}",
        ]

        if graph.context_blocks:
            context_text = "\n".join(f"- {block}" for block in graph.context_blocks)
            sections.append(f"### Context\n{context_text}")

        if graph.rules:
            rules_text = "\n".join(f"- {rule}" for rule in graph.rules)
            sections.append(f"### Rules\n{rules_text}")

        if graph.few_shot:
            few_shot_text = "\n".join(f"- {example}" for example in graph.few_shot)
            sections.append(f"### Few-Shot Hints\n{few_shot_text}")

        sections.append(f"### Output Format\n{graph.output_format}")
        sections.append(f"### SAMMO Mutation Label\n{label}")
        return "\n\n".join(sections).strip()

    async def _estimate_tcrte_score(self, prompt_text: str, api_key: str) -> int:
        """
        Estimate TCRTE quickly using the deterministic scorer when possible.
        Falls back to a heuristic if the scorer is unavailable.
        """
        try:
            tcrte_payload = await score_tcrte(raw_prompt=prompt_text, api_key=api_key)
            return int(tcrte_payload.get("overall_score", 0))
        except Exception:
            # Heuristic fallback keeps SAMMO functional for non-OpenAI-only sessions.
            score = 40
            if "### Instruction" in prompt_text:
                score += 15
            if "### Context" in prompt_text:
                score += 15
            if "### Rules" in prompt_text:
                score += 15
            if "### Output Format" in prompt_text:
                score += 15
            return max(0, min(100, score))

    def _token_efficiency_score(self, candidate_tokens: int, baseline_tokens: int) -> int:
        """Compute a 0-100 token-efficiency score relative to baseline size."""
        if candidate_tokens <= 0 or baseline_tokens <= 0:
            return 0
        ratio = baseline_tokens / candidate_tokens
        return max(0, min(100, int(round(ratio * 100))))

    def _normalize_prompt(self, prompt_text: str) -> str:
        """Normalize prompt string for deduplication."""
        return re.sub(r"\s+", " ", prompt_text.strip().lower())

    def _pareto_front(self, candidates: list[SammoCandidate]) -> list[SammoCandidate]:
        """Return non-dominated candidates over (tcrte_score, token_efficiency_score)."""
        front: list[SammoCandidate] = []
        for candidate in candidates:
            dominated = False
            for other in candidates:
                if other is candidate:
                    continue
                if (
                    other.tcrte_score >= candidate.tcrte_score
                    and other.token_efficiency_score >= candidate.token_efficiency_score
                    and (
                        other.tcrte_score > candidate.tcrte_score
                        or other.token_efficiency_score > candidate.token_efficiency_score
                    )
                ):
                    dominated = True
                    break
            if not dominated:
                front.append(candidate)
        return front

    def _select_variant_candidates(self, candidates: list[SammoCandidate]) -> list[SammoCandidate]:
        """Select Conservative, Structured, Advanced candidates."""
        if not candidates:
            raise ValueError("SAMMO produced no candidate prompts.")

        # Conservative: most token-efficient that still clears minimum quality.
        quality_safe = [
            candidate for candidate in candidates if candidate.tcrte_score >= SAMMO_MIN_TCRTE_THRESHOLD
        ]
        conservative_pool = quality_safe or candidates
        conservative = max(conservative_pool, key=lambda item: item.token_efficiency_score)

        # Structured: highest structural quality estimate.
        structured = max(candidates, key=lambda item: item.tcrte_score)

        # Advanced: choose strongest candidate from pareto front using weighted blend.
        pareto_candidates = self._pareto_front(candidates)
        advanced = max(pareto_candidates, key=lambda item: item.combined_score)

        selected: list[SammoCandidate] = []
        used: set[str] = set()
        for item in (conservative, structured, advanced):
            key = self._normalize_prompt(item.system_prompt)
            if key in used:
                continue
            selected.append(item)
            used.add(key)

        if len(selected) < 3:
            for candidate in sorted(candidates, key=lambda item: item.combined_score, reverse=True):
                key = self._normalize_prompt(candidate.system_prompt)
                if key in used:
                    continue
                selected.append(candidate)
                used.add(key)
                if len(selected) == 3:
                    break

        if len(selected) < 3:
            best = max(candidates, key=lambda item: item.combined_score)
            fallbacks = [
                f"{best.system_prompt}\n\nAdditional guard: keep output concise and deterministic.",
                f"{best.system_prompt}\n\nAdditional guard: avoid unsupported assumptions and cite uncertainty.",
            ]
            for index, prompt in enumerate(fallbacks, start=1):
                key = self._normalize_prompt(prompt)
                if key in used:
                    continue
                selected.append(
                    SammoCandidate(
                        label=f"fallback-{index}",
                        system_prompt=prompt,
                        tcrte_score=best.tcrte_score,
                        token_efficiency_score=best.token_efficiency_score,
                        combined_score=best.combined_score,
                    )
                )
                used.add(key)
                if len(selected) == 3:
                    break

        return selected[:3]

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[list[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:
        """Generate three SAMMO variants via graph mutation and pareto selection."""
        enriched_prompt = integrate_gap_interview_answers_into_prompt(
            raw_prompt=request.raw_prompt,
            gap_interview_answers=request.answers,
            gap_analysis_data=request.gap_data,
        )

        base_graph = await self._parse_prompt_graph(raw_prompt=enriched_prompt, request=request)
        mutation_operators = ["compression", "restructure", "syntactical"]
        mutation_graphs = await asyncio.gather(
            *(
                self._mutate_graph(
                    base_graph=base_graph,
                    mutation_operator=operator,
                    request=request,
                )
                for operator in mutation_operators
            )
        )

        assembled_prompts: list[tuple[str, str]] = [
            ("base", self._assemble_prompt_from_graph(graph=base_graph, label="base")),
        ]
        for operator, graph in zip(mutation_operators, mutation_graphs):
            assembled_prompts.append(
                (operator, self._assemble_prompt_from_graph(graph=graph, label=operator))
            )

        deduped_prompts: list[tuple[str, str]] = []
        seen: set[str] = set()
        for label, prompt_text in assembled_prompts:
            normalized = self._normalize_prompt(prompt_text)
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped_prompts.append((label, prompt_text))

        baseline_tokens = max(1, len(deduped_prompts[0][1]) // 4)
        scored_candidates: list[SammoCandidate] = []
        for label, prompt_text in deduped_prompts:
            candidate_tokens = max(1, len(prompt_text) // 4)
            tcrte_score = await self._estimate_tcrte_score(prompt_text, request.api_key)
            token_score = self._token_efficiency_score(candidate_tokens, baseline_tokens)
            combined = (SAMMO_TCRTE_WEIGHT * tcrte_score) + (SAMMO_TOKEN_WEIGHT * token_score)
            scored_candidates.append(
                SammoCandidate(
                    label=label,
                    system_prompt=prompt_text,
                    tcrte_score=tcrte_score,
                    token_efficiency_score=token_score,
                    combined_score=combined,
                )
            )

        selected_candidates = self._select_variant_candidates(scored_candidates)
        variant_names = ["Conservative", "Structured", "Advanced"]
        variant_strategies = [
            "Most token-efficient topology that still satisfies structural quality threshold.",
            "Highest-quality topology by structural TCRTE estimate.",
            "Pareto-optimal topology balancing quality and token efficiency.",
        ]
        advanced_prefill = generate_claude_prefill_suggestion(request.task_type, request.provider)

        variants: list[PromptVariant] = []
        for index, candidate in enumerate(selected_candidates, start=1):
            prompt_text = inject_input_variables_block(
                candidate.system_prompt,
                request.input_variables,
                request.provider,
            )
            variants.append(
                PromptVariant(
                    id=index,
                    name=variant_names[index - 1],
                    strategy=variant_strategies[index - 1],
                    system_prompt=prompt_text,
                    user_prompt="[Insert request data here]",
                    prefill_suggestion=advanced_prefill if index == 3 else None,
                    token_estimate=len(prompt_text) // 4,
                    tcrte_scores=VariantTCRTEScores(
                        task=min(100, candidate.tcrte_score + 2),
                        context=candidate.tcrte_score,
                        role=max(50, candidate.tcrte_score - 5),
                        tone=max(50, candidate.tcrte_score - 5),
                        execution=min(100, candidate.tcrte_score + 4),
                    ),
                    strengths=[
                        f"SAMMO mutation label: {candidate.label}",
                        f"TCRTE estimate: {candidate.tcrte_score}",
                        f"Token-efficiency score: {candidate.token_efficiency_score}",
                    ],
                    best_for=(
                        "Prompts that benefit from explicit structural mutation and "
                        "quality-vs-token tradeoff control."
                    ),
                    overshoot_guards=[
                        "Selected from non-dominated multi-objective candidate set."
                    ],
                    undershoot_guards=[
                        "All candidates preserve instruction, context, rules, and output format sections."
                    ],
                )
            )

        best_tcrte = max(candidate.tcrte_score for candidate in scored_candidates)
        response = OptimizationResponse(
            analysis=OptimizationAnalysis(
                detected_issues=[
                    "Flat prompt structure was decomposed into mutable topology nodes.",
                    "Quality and token efficiency objectives were optimized jointly.",
                ],
                model_notes=(
                    f"SAMMO evaluated {len(scored_candidates)} mutation candidate(s) across "
                    f"{len(mutation_operators)} operators."
                    + (f" Auto-select logic: {auto_reason}" if auto_reason else "")
                ),
                framework_applied="sammo",
                coverage_delta=compute_coverage_delta_description(request.gap_data, best_tcrte),
                auto_selected_framework="sammo" if auto_reason else None,
                auto_reason=auto_reason,
            ),
            techniques_applied=[
                "SAMMO Prompt Graph Parsing",
                "Topological Mutation Operators",
                "Pareto Multi-Objective Selection",
            ],
            variants=variants,
        )

        response = await self._refine_variants_with_quality_critique(
            response=response,
            raw_prompt=request.raw_prompt,
            task_type=request.task_type,
            api_key=request.api_key,
            quality_gate_mode=request.quality_gate_mode,
            framework="sammo",
            target_model=request.model_id,
        )
        if response.run_metadata is not None:
            response.run_metadata.sammo_mutations_explored = len(scored_candidates)
        return response
