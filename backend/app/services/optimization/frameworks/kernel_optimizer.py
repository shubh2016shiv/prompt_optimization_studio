"""
KERNEL prompt optimizer strategy.

KERNEL = Keep simple, Explicit constraints, Narrow scope, Known success criteria,
Logical order. This implementation performs real rewriting passes rather than
simple heading-based string templating.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.models.requests import OptimizationRequest
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)
from app.services.json_extractor import (
    JSONExtractionError,
    coerce_top_level_object,
    extract_json_from_llm_response,
)
from app.services.llm_client import LLMClient
from app.services.optimization.base import BaseOptimizerStrategy
from app.services.optimization.optimizer_configuration import (
    MAX_TOKENS_COMPONENT_EXTRACTION,
    MAX_TOKENS_KERNEL_REWRITE,
    SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
)
from app.services.optimization.shared_prompt_techniques import (
    compute_coverage_delta_description,
    generate_claude_prefill_suggestion,
    inject_input_variables_block,
    integrate_gap_interview_answers_into_prompt,
)

logger = logging.getLogger(__name__)


_KERNEL_COMPONENT_PARSE_PROMPT = """
You are a KERNEL decomposition specialist.
Extract stable optimization anchors from the prompt.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY valid JSON:
{{
  "task": "single bounded objective",
  "context": "required grounding context",
  "positive_constraints": ["must-do constraints"],
  "negative_constraints": ["must-not constraints"],
  "success_criteria": ["verifiable completion checks"],
  "output_format": "required output format/schema"
}}
""".strip()


_KERNEL_REWRITE_PROMPT = """
You are performing a KERNEL rewrite.
Rewrite the prompt end-to-end, not as labels-only rearrangement.

KERNEL objective for this pass:
{objective}

KERNEL blueprint (must preserve intent):
{blueprint_json}

Original prompt:
<raw_prompt>
{raw_prompt}
</raw_prompt>

Rules:
- Rewrite prose for clarity and directness.
- Use explicit MUST and MUST NOT constraints.
- Keep scope narrow to one bounded objective.
- Include verifiable success criteria.
- Keep the structure logically ordered.
- Return only the final rewritten system prompt text.
""".strip()


class KernelOptimizer(BaseOptimizerStrategy):
    """Deep KERNEL rewrite optimizer."""

    async def _parse_kernel_components(
        self,
        *,
        prompt_text: str,
        request: OptimizationRequest,
    ) -> dict[str, Any]:
        """Extract KERNEL components used as rewrite anchors."""
        parser_prompt = _KERNEL_COMPONENT_PARSE_PROMPT.format(raw_prompt=prompt_text)

        async with LLMClient(api_key=request.api_key) as llm_client:
            response_text = await llm_client.call(
                provider=request.provider,
                prompt=parser_prompt,
                max_tokens=MAX_TOKENS_COMPONENT_EXTRACTION,
                model=request.model_id,
                system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
                response_format={"type": "json_object"},
            )

        parsed = extract_json_from_llm_response(response_text)
        components = coerce_top_level_object(parsed, context_label="kernel component parse")

        task = str(components.get("task", "")).strip() or prompt_text.strip()
        context = str(components.get("context", "")).strip()
        positive_constraints = self._coerce_str_list(components.get("positive_constraints"))
        negative_constraints = self._coerce_str_list(components.get("negative_constraints"))
        success_criteria = self._coerce_str_list(components.get("success_criteria"))
        output_format = str(components.get("output_format", "")).strip()
        if not output_format:
            output_format = "Provide structured output that directly satisfies the task."

        return {
            "task": task,
            "context": context,
            "positive_constraints": positive_constraints,
            "negative_constraints": negative_constraints,
            "success_criteria": success_criteria,
            "output_format": output_format,
        }

    def _coerce_str_list(self, value: Any) -> list[str]:
        """Normalize unknown list-like values to clean string lists."""
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    async def _rewrite_with_kernel_objective(
        self,
        *,
        raw_prompt: str,
        components: dict[str, Any],
        objective: str,
        request: OptimizationRequest,
    ) -> str:
        """Run one objective-specific deep rewrite pass."""
        rewrite_prompt = _KERNEL_REWRITE_PROMPT.format(
            objective=objective,
            blueprint_json=json.dumps(components, ensure_ascii=False, indent=2),
            raw_prompt=raw_prompt,
        )

        async with LLMClient(api_key=request.api_key) as llm_client:
            rewritten = await llm_client.call(
                provider=request.provider,
                prompt=rewrite_prompt,
                max_tokens=MAX_TOKENS_KERNEL_REWRITE,
                model=request.model_id,
                temperature=0.35,
            )
        rewritten_text = rewritten.strip()
        if not rewritten_text:
            raise ValueError("KERNEL rewrite returned empty output.")
        return rewritten_text

    def _fallback_rewrite(
        self,
        *,
        components: dict[str, Any],
        tier: str,
    ) -> str:
        """Deterministic fallback when rewrite pass fails."""
        task = components["task"]
        context = components["context"]
        positive = components["positive_constraints"]
        negative = components["negative_constraints"]
        success = components["success_criteria"]
        output_format = components["output_format"]

        positive_text = "\n".join(f"- MUST: {item}" for item in positive) or "- MUST: Follow the task exactly."
        negative_text = "\n".join(f"- MUST NOT: {item}" for item in negative) or "- MUST NOT: Add unsupported facts."
        success_text = "\n".join(f"- {item}" for item in success) or "- The output is complete and matches the requested format."

        sections = [f"Task: {task}"]
        if context:
            sections.append(f"Context:\n{context}")
        sections.append(f"Constraints:\n{positive_text}\n{negative_text}")
        sections.append(f"Success Criteria:\n{success_text}")
        sections.append(f"Output Format:\n{output_format}")

        if tier == "advanced":
            sections.append(
                "Validation Guard:\n- Before finalizing, verify every required field and state uncertainty instead of guessing."
            )
        return "\n\n".join(sections).strip()

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[list[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:
        """Generate three KERNEL variants via deep rewrite passes."""
        logger.info("Executing deep KERNEL rewrite optimization.")

        enriched_prompt = integrate_gap_interview_answers_into_prompt(
            raw_prompt=request.raw_prompt,
            gap_interview_answers=request.answers,
            gap_analysis_data=request.gap_data,
        )

        components = await self._parse_kernel_components(
            prompt_text=enriched_prompt,
            request=request,
        )

        objectives = {
            "conservative": (
                "Keep it simple: shorten language, remove ambiguity, and keep one bounded objective."
            ),
            "structured": (
                "Make constraints explicit with clear MUST and MUST NOT boundaries and strict logical order."
            ),
            "advanced": (
                "Maximize failure resistance: add validation checks, anti-hallucination guards, and strict scope limits."
            ),
        }

        rewritten_by_tier: dict[str, str] = {}
        for tier, objective in objectives.items():
            try:
                rewritten_by_tier[tier] = await self._rewrite_with_kernel_objective(
                    raw_prompt=enriched_prompt,
                    components=components,
                    objective=objective,
                    request=request,
                )
            except (JSONExtractionError, ValueError, Exception) as rewrite_error:
                logger.warning("KERNEL %s rewrite failed, using fallback: %s", tier, rewrite_error)
                rewritten_by_tier[tier] = self._fallback_rewrite(components=components, tier=tier)

        conservative_prompt = inject_input_variables_block(
            rewritten_by_tier["conservative"],
            request.input_variables,
            request.provider,
        )
        structured_prompt = inject_input_variables_block(
            rewritten_by_tier["structured"],
            request.input_variables,
            request.provider,
        )
        advanced_prompt = inject_input_variables_block(
            rewritten_by_tier["advanced"],
            request.input_variables,
            request.provider,
        )
        advanced_prefill = generate_claude_prefill_suggestion(request.task_type, request.provider)

        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy="Deep KERNEL rewrite emphasizing simplicity and bounded objective scope.",
                system_prompt=conservative_prompt,
                user_prompt="[Insert request data here]",
                token_estimate=len(conservative_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=72, context=64, role=55, tone=55, execution=72),
                strengths=["Clearer imperative prose", "Reduced ambiguity"],
                best_for="Low-to-medium complexity tasks needing reliable clarity.",
                overshoot_guards=["Scope narrowed to one primary objective."],
                undershoot_guards=["Task and format requirements made explicit."],
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy="Deep KERNEL rewrite with explicit MUST/MUST NOT constraints and known success checks.",
                system_prompt=structured_prompt,
                user_prompt="[Insert request data here]",
                token_estimate=len(structured_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=84, context=78, role=60, tone=60, execution=84),
                strengths=["Explicit constraint boundaries", "Verifiable success criteria"],
                best_for="Production workflows requiring deterministic compliance.",
                overshoot_guards=["Hard negative constraints reduce scope creep."],
                undershoot_guards=["Logical order protects against missed steps."],
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy="Deep KERNEL rewrite with validation and anti-hallucination guardrails.",
                system_prompt=advanced_prompt,
                user_prompt="[Insert request data here]",
                prefill_suggestion=advanced_prefill,
                token_estimate=len(advanced_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=92, context=86, role=66, tone=66, execution=92),
                strengths=["Guarded failure-resistant instructions", "Strong format control"],
                best_for="High-stakes tasks where correctness and safety are critical.",
                overshoot_guards=["Validation checks before final output."],
                undershoot_guards=["All key constraints echoed as executable rules."],
            ),
        ]

        model_notes = "KERNEL deep rewrite pipeline completed (parse -> rewrite passes -> guarded fallback)."
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        response = OptimizationResponse(
            analysis=OptimizationAnalysis(
                detected_issues=[
                    "Prompt required simplification and stricter scope boundaries.",
                    "Constraint handling required explicit MUST/MUST NOT normalization.",
                ],
                model_notes=model_notes,
                framework_applied="kernel",
                coverage_delta=compute_coverage_delta_description(request.gap_data, 82),
                auto_selected_framework="kernel" if auto_reason else None,
                auto_reason=auto_reason,
            ),
            techniques_applied=[
                "KERNEL Deep Rewrite",
                "Constraint Normalization",
                "Scope Narrowing",
                "Known-Success Criteria",
            ],
            variants=variants,
        )

        response = await self._refine_variants_with_quality_critique(
            response=response,
            raw_prompt=request.raw_prompt,
            task_type=request.task_type,
            api_key=request.api_key,
            quality_gate_mode=request.quality_gate_mode,
            framework="kernel",
            target_model=request.model_id,
        )
        return response