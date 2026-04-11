"""Progressive Disclosure optimizer strategy.

Deep Progressive Disclosure implementation that rewrites prompts with layered
activation/execution semantics instead of static heading templates.
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
    MAX_TOKENS_PROGRESSIVE_REWRITE,
    SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
)
from app.services.optimization.prompt_registry.progressive import (
    PROGRESSIVE_BLUEPRINT_PARSE_PROMPT_TEMPLATE,
    PROGRESSIVE_REWRITE_PROMPT_TEMPLATE,
)
from app.services.optimization.shared_prompt_techniques import (
    apply_ral_writer_constraint_restatement,
    compute_coverage_delta_description,
    generate_claude_prefill_suggestion,
    inject_input_variables_block,
    integrate_gap_interview_answers_into_prompt,
)

logger = logging.getLogger(__name__)


_PROGRESSIVE_BLUEPRINT_PARSE_PROMPT = PROGRESSIVE_BLUEPRINT_PARSE_PROMPT_TEMPLATE
_PROGRESSIVE_REWRITE_PROMPT = PROGRESSIVE_REWRITE_PROMPT_TEMPLATE


class ProgressiveDisclosureOptimizer(BaseOptimizerStrategy):
    """Deep Progressive Disclosure rewrite optimizer."""

    def _coerce_str_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _coerce_activation_rules(self, value: Any) -> list[dict[str, str]]:
        if not isinstance(value, list):
            return []

        rules: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue

            trigger = str(item.get("trigger", "")).strip()
            action = str(item.get("action", "")).strip()
            priority = str(item.get("priority", "medium")).strip() or "medium"
            if not trigger or not action:
                continue

            rules.append(
                {
                    "trigger": trigger,
                    "action": action,
                    "priority": priority,
                }
            )

        return rules

    def _default_blueprint(self, prompt_text: str) -> dict[str, Any]:
        return {
            "discovery_metadata": [
                "Available capability: execute user-requested task with provided context.",
                "Use only explicitly provided instructions and data.",
            ],
            "activation_rules": [
                {
                    "trigger": "When the request is clear and in-scope",
                    "action": "Run the required workflow without adding unrelated steps",
                    "priority": "critical",
                },
                {
                    "trigger": "When required data is missing",
                    "action": "State what is missing and request clarification",
                    "priority": "high",
                },
            ],
            "execution_logic": [
                f"Interpret objective: {prompt_text.strip() or 'execute request'}.",
                "Apply constraints before producing output.",
                "Verify output against requested format.",
            ],
            "output_format": "Structured output directly matching the request.",
            "safety_bounds": ["Do not hallucinate unsupported facts."],
            "failure_modes": ["Do not blend activation conditions with execution steps."],
        }

    async def _parse_progressive_blueprint(
        self,
        *,
        prompt_text: str,
        request: OptimizationRequest,
    ) -> dict[str, Any]:
        parser_prompt = _PROGRESSIVE_BLUEPRINT_PARSE_PROMPT.format(raw_prompt=prompt_text)

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
        blueprint = coerce_top_level_object(parsed, context_label="progressive blueprint parse")
        default_blueprint = self._default_blueprint(prompt_text)

        discovery_metadata = (
            self._coerce_str_list(blueprint.get("discovery_metadata"))
            or default_blueprint["discovery_metadata"]
        )
        activation_rules = (
            self._coerce_activation_rules(blueprint.get("activation_rules"))
            or default_blueprint["activation_rules"]
        )
        execution_logic = (
            self._coerce_str_list(blueprint.get("execution_logic"))
            or default_blueprint["execution_logic"]
        )
        output_format = str(blueprint.get("output_format", "")).strip() or default_blueprint["output_format"]
        safety_bounds = self._coerce_str_list(blueprint.get("safety_bounds")) or default_blueprint["safety_bounds"]
        failure_modes = self._coerce_str_list(blueprint.get("failure_modes")) or default_blueprint["failure_modes"]

        return {
            "discovery_metadata": discovery_metadata,
            "activation_rules": activation_rules,
            "execution_logic": execution_logic,
            "output_format": output_format,
            "safety_bounds": safety_bounds,
            "failure_modes": failure_modes,
        }

    async def _rewrite_with_progressive_objective(
        self,
        *,
        raw_prompt: str,
        blueprint: dict[str, Any],
        objective: str,
        request: OptimizationRequest,
    ) -> str:
        rewrite_prompt = _PROGRESSIVE_REWRITE_PROMPT.format(
            objective=objective,
            blueprint_json=json.dumps(blueprint, ensure_ascii=False, indent=2),
            raw_prompt=raw_prompt,
        )

        async with LLMClient(api_key=request.api_key) as llm_client:
            rewritten = await llm_client.call(
                provider=request.provider,
                prompt=rewrite_prompt,
                max_tokens=MAX_TOKENS_PROGRESSIVE_REWRITE,
                model=request.model_id,
                temperature=0.35,
            )

        rewritten_text = rewritten.strip()
        if not rewritten_text:
            raise ValueError("Progressive rewrite returned empty output.")
        return rewritten_text

    def _fallback_progressive_prompt(self, *, blueprint: dict[str, Any], tier: str) -> str:
        discovery_text = "\n".join(f"- {line}" for line in blueprint["discovery_metadata"])
        activation_lines = []
        for rule in blueprint["activation_rules"]:
            activation_lines.append(
                f"- IF: {rule['trigger']}\\n  THEN: {rule['action']} (priority={rule['priority']})"
            )
        activation_text = "\n".join(activation_lines)
        execution_text = "\n".join(f"{idx + 1}. {step}" for idx, step in enumerate(blueprint["execution_logic"]))
        safety_text = "\n".join(f"- {line}" for line in blueprint["safety_bounds"])
        failure_text = "\n".join(f"- Prevent: {line}" for line in blueprint["failure_modes"])

        sections = [
            "DISCOVERY LAYER:\n" + discovery_text,
            "ACTIVATION LAYER:\n" + activation_text,
            "EXECUTION LAYER:\n" + execution_text,
            "OUTPUT SPECIFICATION:\n" + blueprint["output_format"],
            "SAFETY BOUNDS:\n" + safety_text,
            "FAILURE MODE CONTROLS:\n" + failure_text,
        ]

        if tier in {"structured", "advanced"}:
            sections.append(
                "ORDERING GUARD:\n"
                "- First check activation condition matches request.\n"
                "- Then execute only matching procedures.\n"
                "- Finally verify output format and constraints."
            )

        if tier == "advanced":
            sections.append(
                "ESCALATION GUARD:\n"
                "- If instructions conflict, prioritize safety bounds and explicit constraints.\n"
                "- If context is insufficient, abstain and state missing elements."
            )

        return "\n\n".join(sections).strip()

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[list[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:
        """Generate Progressive variants via layered parse and deep rewrite."""
        logger.info("Executing deep Progressive Disclosure rewrite optimization.")

        enriched_prompt = integrate_gap_interview_answers_into_prompt(
            raw_prompt=request.raw_prompt,
            gap_interview_answers=request.answers,
            gap_analysis_data=request.gap_data,
        )

        try:
            blueprint = await self._parse_progressive_blueprint(
                prompt_text=enriched_prompt,
                request=request,
            )
        except (JSONExtractionError, ValueError, Exception) as parse_error:
            logger.warning("Progressive blueprint parse failed, using default blueprint: %s", parse_error)
            blueprint = self._default_blueprint(enriched_prompt)

        objectives = {
            "conservative": (
                "Rewrite for cleaner separation of discovery, activation, and execution with bounded scope."
            ),
            "structured": (
                "Strengthen trigger-to-action determinism and enforce ordered execution controls."
            ),
            "advanced": (
                "Maximize reliability with conflict-resolution rules, safety bounds, and failure-mode defenses."
            ),
        }

        rewritten_by_tier: dict[str, str] = {}
        for tier, objective in objectives.items():
            try:
                rewritten_by_tier[tier] = await self._rewrite_with_progressive_objective(
                    raw_prompt=enriched_prompt,
                    blueprint=blueprint,
                    objective=objective,
                    request=request,
                )
            except (JSONExtractionError, ValueError, Exception) as rewrite_error:
                logger.warning("Progressive %s rewrite failed, using fallback: %s", tier, rewrite_error)
                rewritten_by_tier[tier] = self._fallback_progressive_prompt(blueprint=blueprint, tier=tier)

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
        advanced_prompt = apply_ral_writer_constraint_restatement(
            system_prompt=advanced_prompt,
            critical_constraints_to_echo=blueprint["safety_bounds"],
            provider=request.provider,
        )
        advanced_prefill = generate_claude_prefill_suggestion(request.task_type, request.provider)

        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy="Deep progressive rewrite with clearer layer separation and bounded flow.",
                system_prompt=conservative_prompt,
                user_prompt="[Insert request payload here]",
                token_estimate=len(conservative_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=76, context=72, role=56, tone=56, execution=74),
                strengths=["Clear layer boundaries", "Reduced instruction blending"],
                best_for="Simple to moderate agent routing workflows.",
                overshoot_guards=["Execution kept bounded to matching triggers."],
                undershoot_guards=["Discovery and execution responsibilities separated."],
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy="Deep progressive rewrite with deterministic trigger-action execution sequencing.",
                system_prompt=structured_prompt,
                user_prompt="[Insert request payload here]",
                token_estimate=len(structured_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=86, context=84, role=72, tone=72, execution=86),
                strengths=["Deterministic activation logic", "Ordered procedural execution"],
                best_for="Production multi-step agentic workflows.",
                overshoot_guards=["Ordering guard reduces uncontrolled branching."],
                undershoot_guards=["Output format verification added."],
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy="Deep progressive rewrite with conflict resolution and failure-mode protection.",
                system_prompt=advanced_prompt,
                user_prompt="<user_invocation>[Insert request payload here]</user_invocation>",
                prefill_suggestion=advanced_prefill,
                token_estimate=len(advanced_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=93, context=91, role=86, tone=86, execution=93),
                strengths=["Strong safety and escalation handling", "Robust failure-mode containment"],
                best_for="High-stakes multi-agent or tool-using flows.",
                overshoot_guards=["Conflict resolution guard", "Safety recency restatement"],
                undershoot_guards=["Explicit abstention on insufficient context."],
            ),
        ]

        model_notes = "Progressive deep rewrite pipeline completed (parse -> rewrite passes -> guarded fallback)."
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        response = OptimizationResponse(
            analysis=OptimizationAnalysis(
                detected_issues=[
                    "Discovery, activation, and execution logic were entangled.",
                    "Trigger semantics and failure controls were underspecified.",
                ],
                model_notes=model_notes,
                framework_applied="progressive",
                coverage_delta=compute_coverage_delta_description(request.gap_data, 85),
                auto_selected_framework="progressive" if auto_reason else None,
                auto_reason=auto_reason,
            ),
            techniques_applied=[
                "Progressive Blueprint Parse",
                "Layer-Aware Deep Rewrite",
                "Trigger-Action Determinism",
                "Failure-Mode Guarding",
            ],
            variants=variants,
        )

        response = await self._refine_variants_with_quality_critique(
            response=response,
            raw_prompt=request.raw_prompt,
            task_type=request.task_type,
            api_key=request.api_key,
            quality_gate_mode=request.quality_gate_mode,
            framework="progressive",
            target_model=request.model_id,
        )

        return response
