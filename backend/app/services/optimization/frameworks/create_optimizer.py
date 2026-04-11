"""CREATE optimizer strategy.

Deep CREATE implementation that rewrites prompt prose end-to-end using
CREATE anchors, instead of static section templating.
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
    MAX_TOKENS_CREATE_REWRITE,
    SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
)
from app.services.optimization.prompt_registry.create import (
    CREATE_BLUEPRINT_PARSE_PROMPT_TEMPLATE,
    CREATE_REWRITE_PROMPT_TEMPLATE,
)
from app.services.optimization.shared_prompt_techniques import (
    compute_coverage_delta_description,
    generate_claude_prefill_suggestion,
    inject_input_variables_block,
    integrate_gap_interview_answers_into_prompt,
)

logger = logging.getLogger(__name__)


_CREATE_BLUEPRINT_PARSE_PROMPT = CREATE_BLUEPRINT_PARSE_PROMPT_TEMPLATE
_CREATE_REWRITE_PROMPT = CREATE_REWRITE_PROMPT_TEMPLATE


class CreateOptimizer(BaseOptimizerStrategy):
    """Deep CREATE rewrite optimizer."""

    def _coerce_str_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _default_blueprint(self, prompt_text: str) -> dict[str, Any]:
        return {
            "character": "You are a precise and reliable assistant.",
            "request": prompt_text.strip() or "Execute the user's request using provided context.",
            "examples": ["No explicit examples were provided."],
            "adjustments": [
                "Follow the request exactly.",
                "Keep reasoning bounded to provided context.",
            ],
            "type_of_output": "Structured response that directly satisfies the request.",
            "extras": ["State uncertainty instead of inventing details."],
            "forbidden_behaviors": ["Do not hallucinate unsupported facts."],
            "verification_checks": ["Confirm the output matches the requested format."],
        }

    async def _parse_create_blueprint(
        self,
        *,
        prompt_text: str,
        request: OptimizationRequest,
    ) -> dict[str, Any]:
        parser_prompt = _CREATE_BLUEPRINT_PARSE_PROMPT.format(raw_prompt=prompt_text)

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
        blueprint = coerce_top_level_object(parsed, context_label="create blueprint parse")

        default_blueprint = self._default_blueprint(prompt_text)

        character = str(blueprint.get("character", "")).strip() or default_blueprint["character"]
        request_objective = str(blueprint.get("request", "")).strip() or default_blueprint["request"]
        examples = self._coerce_str_list(blueprint.get("examples")) or default_blueprint["examples"]
        adjustments = self._coerce_str_list(blueprint.get("adjustments")) or default_blueprint["adjustments"]
        type_of_output = str(blueprint.get("type_of_output", "")).strip() or default_blueprint["type_of_output"]
        extras = self._coerce_str_list(blueprint.get("extras")) or default_blueprint["extras"]
        forbidden_behaviors = (
            self._coerce_str_list(blueprint.get("forbidden_behaviors"))
            or default_blueprint["forbidden_behaviors"]
        )
        verification_checks = (
            self._coerce_str_list(blueprint.get("verification_checks"))
            or default_blueprint["verification_checks"]
        )

        return {
            "character": character,
            "request": request_objective,
            "examples": examples,
            "adjustments": adjustments,
            "type_of_output": type_of_output,
            "extras": extras,
            "forbidden_behaviors": forbidden_behaviors,
            "verification_checks": verification_checks,
        }

    async def _rewrite_with_create_objective(
        self,
        *,
        raw_prompt: str,
        blueprint: dict[str, Any],
        objective: str,
        request: OptimizationRequest,
    ) -> str:
        rewrite_prompt = _CREATE_REWRITE_PROMPT.format(
            objective=objective,
            blueprint_json=json.dumps(blueprint, ensure_ascii=False, indent=2),
            raw_prompt=raw_prompt,
        )

        async with LLMClient(api_key=request.api_key) as llm_client:
            rewritten = await llm_client.call(
                provider=request.provider,
                prompt=rewrite_prompt,
                max_tokens=MAX_TOKENS_CREATE_REWRITE,
                model=request.model_id,
                temperature=0.35,
            )

        rewritten_text = rewritten.strip()
        if not rewritten_text:
            raise ValueError("CREATE rewrite returned empty output.")
        return rewritten_text

    def _fallback_create_prompt(self, *, blueprint: dict[str, Any], tier: str) -> str:
        character = blueprint["character"]
        request_objective = blueprint["request"]
        examples = blueprint["examples"]
        adjustments = blueprint["adjustments"]
        type_of_output = blueprint["type_of_output"]
        extras = blueprint["extras"]
        forbidden_behaviors = blueprint["forbidden_behaviors"]
        verification_checks = blueprint["verification_checks"]

        example_lines = "\n".join(f"- {item}" for item in examples)
        must_lines = "\n".join(f"- MUST: {item}" for item in adjustments)
        must_not_lines = "\n".join(f"- MUST NOT: {item}" for item in forbidden_behaviors)
        extras_lines = "\n".join(f"- {item}" for item in extras)
        verify_lines = "\n".join(f"- {item}" for item in verification_checks)

        sections = [
            f"CHARACTER:\n{character}",
            f"REQUEST:\n{request_objective}",
            f"EXAMPLES:\n{example_lines}",
            f"ADJUSTMENTS:\n{must_lines}\n{must_not_lines}",
            f"TYPE OF OUTPUT:\n{type_of_output}",
            f"EXTRAS:\n{extras_lines}",
            f"VERIFICATION:\n{verify_lines}",
        ]

        if tier in {"structured", "advanced"}:
            sections.append(
                "EXECUTION ORDER:\n"
                "1. Parse request and constraints.\n"
                "2. Produce output using only allowed context.\n"
                "3. Run verification checks before final answer."
            )

        if tier == "advanced":
            sections.append(
                "Validation Guard:\n"
                "- If required evidence is missing, state what is missing.\n"
                "- Never fabricate details to satisfy format requirements.\n"
                "- Prefer abstention over unsupported claims."
            )

        return "\n\n".join(sections).strip()

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[list[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:
        """Generate CREATE variants via parse and deep rewrite passes."""
        logger.info("Executing deep CREATE rewrite optimization.")

        enriched_prompt = integrate_gap_interview_answers_into_prompt(
            raw_prompt=request.raw_prompt,
            gap_interview_answers=request.answers,
            gap_analysis_data=request.gap_data,
        )

        try:
            blueprint = await self._parse_create_blueprint(
                prompt_text=enriched_prompt,
                request=request,
            )
        except (JSONExtractionError, ValueError, Exception) as parse_error:
            logger.warning("CREATE blueprint parse failed, using default blueprint: %s", parse_error)
            blueprint = self._default_blueprint(enriched_prompt)

        objectives = {
            "conservative": (
                "Rewrite for clarity and bounded scope while preserving the six CREATE pillars."
            ),
            "structured": (
                "Strengthen explicit MUST and MUST NOT constraints plus ordered execution logic."
            ),
            "advanced": (
                "Maximize failure resistance with strict validation, edge-case handling, and anti-hallucination guards."
            ),
        }

        rewritten_by_tier: dict[str, str] = {}
        for tier, objective in objectives.items():
            try:
                rewritten_by_tier[tier] = await self._rewrite_with_create_objective(
                    raw_prompt=enriched_prompt,
                    blueprint=blueprint,
                    objective=objective,
                    request=request,
                )
            except (JSONExtractionError, ValueError, Exception) as rewrite_error:
                logger.warning("CREATE %s rewrite failed, using fallback: %s", tier, rewrite_error)
                rewritten_by_tier[tier] = self._fallback_create_prompt(blueprint=blueprint, tier=tier)

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
                strategy="Deep CREATE rewrite emphasizing bounded objective and clearer pillar mapping.",
                system_prompt=conservative_prompt,
                user_prompt="[Insert request payload here]",
                token_estimate=len(conservative_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=76, context=68, role=84, tone=62, execution=74),
                strengths=["Cleaner CREATE alignment", "Reduced ambiguity"],
                best_for="Low-to-medium complexity tasks needing reliable structure.",
                overshoot_guards=["Scope narrowed to one bounded objective."],
                undershoot_guards=["Six CREATE pillars preserved explicitly."],
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy="Deep CREATE rewrite with explicit MUST and MUST NOT boundaries and ordered execution.",
                system_prompt=structured_prompt,
                user_prompt="[Insert request payload here]",
                token_estimate=len(structured_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=86, context=82, role=92, tone=80, execution=86),
                strengths=["Deterministic constraints", "Clear execution choreography"],
                best_for="Production workflows requiring stable behavior.",
                overshoot_guards=["Explicit forbidden-behavior rules."],
                undershoot_guards=["Verification checks enforced pre-output."],
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy="Deep CREATE rewrite with strict validation and anti-hallucination guardrails.",
                system_prompt=advanced_prompt,
                user_prompt="[Insert request payload here]",
                prefill_suggestion=advanced_prefill,
                token_estimate=len(advanced_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=93, context=90, role=94, tone=90, execution=93),
                strengths=["Failure-resistant sequencing", "Strong reliability controls"],
                best_for="High-stakes tasks where precision and format fidelity matter.",
                overshoot_guards=["Validation guard before final output."],
                undershoot_guards=["Edge-case and abstention rules included."],
            ),
        ]

        model_notes = "CREATE deep rewrite pipeline completed (parse -> rewrite passes -> guarded fallback)."
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        response = OptimizationResponse(
            analysis=OptimizationAnalysis(
                detected_issues=[
                    "Prompt mixed role, constraints, and output contract without enforceable sequencing.",
                    "Safety and validation instructions were underspecified for reliable execution.",
                ],
                model_notes=model_notes,
                framework_applied="create",
                coverage_delta=compute_coverage_delta_description(request.gap_data, 85),
                auto_selected_framework="create" if auto_reason else None,
                auto_reason=auto_reason,
            ),
            techniques_applied=[
                "CREATE Blueprint Parse",
                "Pillar-Aware Deep Rewrite",
                "Constraint Normalization",
                "Validation Guarding",
            ],
            variants=variants,
        )

        response = await self._refine_variants_with_quality_critique(
            response=response,
            raw_prompt=request.raw_prompt,
            task_type=request.task_type,
            api_key=request.api_key,
            quality_gate_mode=request.quality_gate_mode,
            framework="create",
            target_model=request.model_id,
        )

        return response
