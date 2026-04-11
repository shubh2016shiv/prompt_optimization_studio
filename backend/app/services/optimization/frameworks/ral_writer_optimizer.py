"""
RAL-Writer (Retrieve-and-Restate) Optimizer Strategy — Constraint Restatement

Standalone framework that makes Constraint Restatement the PRIMARY optimisation strategy.
This goes beyond the shared utility (apply_ral_writer_constraint_restatement) which
performs naive text appending. This framework uses LLM analysis to identify implicit
vs explicit constraints, detect constraint conflicts, map constraint scope, and structure
the prompt to ensure complex guardrails are preserved across long-context interactions.

BACKGROUND — The Constraint Dilution Problem:
═══════════════════════════════════════════════════════════════════════════════════════

  When a prompt contains complex constraints (e.g., "Use British English", "Format as JSON",
  "Do not use the word 'therefore'"), LLMs frequently "forget" these constraints if the
  prompt context is long, or if the model's attention is consumed by a difficult reasoning
  task. This is known as Constraint Dilution.

  RAL-Writer (Retrieve-and-Restate) mitigates this by:
  1. Extracting complex, interwoven constraints from the raw narrative.
  2. Isolating them into a dedicated, high-attention structurally separate block.
  3. "Restating" the most critical constraints at the Recency boundary (very end)
     so they are fresh in the model's immediate context window right before generation.

WHAT THIS FRAMEWORK ADDS BEYOND THE SHARED UTILITY:
═══════════════════════════════════════════════════════════════════════════════════════

  The shared utility (shared_prompt_techniques.py L240–L287) performs:
    - Fixed appendage of caller-provided strings to the end of a prompt.
    - No intelligence about WHICH constraints are actually critical.

  This standalone framework performs:
    1. Constraint Extraction & Disentanglement — separates task instructions from
       hard constraints, soft preferences, and implicit rules.
    2. Conflict Detection — identifies if the user's constraints contradict each other.
    3. Structural Isolation — builds an explicit [CONSTRAINTS] primacy block.
    4. Strategic Restatement — intelligently selects only the most critical, often-violated
       constraints for the recency restatement echo.

ALGORITHM WORKFLOW:
═══════════════════════════════════════════════════════════════════════════════════════

  Step 1: CONSTRAINT EXTRACTION (LLM sub-call)
    ├─ Extract explicit hard constraints (must/must not)
    ├─ Extract soft preferences (should/prefer)
    ├─ Identify implicit constraints implied by the task
    └─ Detect constraint conflicts or ambiguities

  Step 2: RESTRUCTURING (LLM sub-call)
    ├─ Rewrite the core prompt narrative with constraints removed (disentanglement)
    └─ Format the core task and context clearly

  Step 3: VARIANT ASSEMBLY (3 tiers)
    ├─ Conservative: Core prompt + primacy constraint block
    ├─ Structured:   Core + primacy block + structural delimiters + recency echo (RAL)
    └─ Advanced:     Core + high-contrast borders + full RAL-Writer echo + prefill

  Step 4: QUALITY GATE
    └─ _refine_variants_with_quality_critique()

COST ANALYSIS:
  2 LLM calls (extraction + rewrite) + quality gate calls.

REFERENCES:
  - APOST_v4_Documentation.md §5.2 (RAL-Writer Restate Technique).

TESTING:
  Run directly:
    cd d:\\Generative AI Portfolio Projects\\APOST\\backend
    python -m app.services.optimization.frameworks.ral_writer_optimizer
"""

import json
import logging
from typing import Any, List, Optional

from app.models.requests import OptimizationRequest
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)
from app.services.llm_client import LLMClient
from app.services.json_extractor import (
    JSONExtractionError,
    coerce_top_level_object,
    extract_json_from_llm_response,
)
from app.services.optimization.base import BaseOptimizerStrategy
from app.services.optimization.optimizer_configuration import (
    MAX_TOKENS_COMPONENT_EXTRACTION,
    SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
)
from app.services.optimization.prompt_registry.ral_writer import (
    CONSTRAINT_EXTRACTION_PROMPT_TEMPLATE,
    NARRATIVE_DISENTANGLEMENT_PROMPT_TEMPLATE,
)
from app.services.optimization.shared_prompt_techniques import (
    integrate_gap_interview_answers_into_prompt,
    inject_input_variables_block,
    apply_ral_writer_constraint_restatement,
    generate_claude_prefill_suggestion,
    compute_coverage_delta_description,
    format_list_as_bullet_points,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# LLM Prompt Templates
# ──────────────────────────────────────────────────────────────────────────────

_CONSTRAINT_EXTRACTION_PROMPT = CONSTRAINT_EXTRACTION_PROMPT_TEMPLATE
_NARRATIVE_DISENTANGLEMENT_PROMPT = NARRATIVE_DISENTANGLEMENT_PROMPT_TEMPLATE


class RalWriterOptimizer(BaseOptimizerStrategy):
    """
    Deep implementation of the RAL-Writer (Retrieve-and-Restate) constraint
    optimization framework.

    This optimizer analyses a prompt to extract, categorise, and deduplicate
    constraints. It then disentangles those constraints from the core task
    narrative to create a clean, structurally separated prompt where constraints
    are isolated in a high-attention primacy block, and the most critical
    constraints are echoed in a recency block (the RAL-Writer technique).
    """

    # ──────────────────────────────────────────────────────────────────────
    # Step 1: Constraint Extraction
    # ──────────────────────────────────────────────────────────────────────

    async def _extract_constraints(
        self,
        raw_prompt: str,
        provider: str,
        model_id: str,
        api_key: str,
    ) -> dict[str, Any]:
        """LLM-driven analysis to identify all explicit/implicit constraints."""
        analysis_prompt = _CONSTRAINT_EXTRACTION_PROMPT.format(raw_prompt=raw_prompt)

        async with LLMClient(api_key=api_key) as llm_client:
            response_text = await llm_client.call(
                provider=provider,
                prompt=analysis_prompt,
                max_tokens=MAX_TOKENS_COMPONENT_EXTRACTION,
                model=model_id,
                system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
            )

            try:
                parsed = extract_json_from_llm_response(response_text)
                analysis = coerce_top_level_object(parsed, context_label="constraint extraction")
            except JSONExtractionError:
                repaired = await llm_client.call(
                    provider=provider,
                    prompt=f"Repair into VALID JSON. Return ONLY JSON.\n\n{response_text}",
                    max_tokens=MAX_TOKENS_COMPONENT_EXTRACTION,
                    model=model_id,
                    system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
                )
                parsed = extract_json_from_llm_response(repaired)
                analysis = coerce_top_level_object(parsed, context_label="constraint extraction (repaired)")

        return self._normalize_extraction(analysis)

    def _normalize_extraction(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize constraint extraction data."""
        hard_constraints = []
        for hc in raw.get("hard_constraints", []):
            if isinstance(hc, dict):
                hard_constraints.append({
                    "rule": str(hc.get("rule", "")).strip(),
                    "criticality": str(hc.get("criticality", "medium")),
                    "category": str(hc.get("category", "content")),
                })

        soft_preferences = [str(x).strip() for x in raw.get("soft_preferences", []) if x]
        missing_implicit = [str(x).strip() for x in raw.get("missing_implicit_constraints", []) if x]
        conflicts = [str(x).strip() for x in raw.get("conflicts", []) if x]

        return {
            "hard_constraints": [hc for hc in hard_constraints if hc["rule"]],
            "soft_preferences": soft_preferences,
            "missing_implicit_constraints": missing_implicit,
            "conflicts": conflicts,
            "constraint_density": str(raw.get("constraint_density", "medium")),
            "summary": str(raw.get("summary", "Constraints extracted.")),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Step 2: Narrative Disentanglement
    # ──────────────────────────────────────────────────────────────────────

    async def _disentangle_narrative(
        self,
        raw_prompt: str,
        provider: str,
        model_id: str,
        api_key: str,
    ) -> dict[str, Any]:
        """Rewrite raw prompt to remove constraints from the core text."""
        disentangle_prompt = _NARRATIVE_DISENTANGLEMENT_PROMPT.format(raw_prompt=raw_prompt)

        async with LLMClient(api_key=api_key) as llm_client:
            response_text = await llm_client.call(
                provider=provider,
                prompt=disentangle_prompt,
                max_tokens=MAX_TOKENS_COMPONENT_EXTRACTION,
                model=model_id,
                system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
            )

        parsed = extract_json_from_llm_response(response_text)
        return {
            "task_narrative": str(parsed.get("task_narrative", raw_prompt)).strip(),
            "context_narrative": str(parsed.get("context_narrative", "")).strip(),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Step 3: Variant Assembly
    # ──────────────────────────────────────────────────────────────────────

    def _assemble_variant(
        self,
        disentangled: dict[str, str],
        constraints: dict[str, Any],
        variant_tier: str,
        provider: str,
    ) -> str:
        """Assemble the variant with escalating RAL-Writer structural intensity."""
        task = disentangled["task_narrative"]
        context = disentangled["context_narrative"]

        # Build combined constraint list
        hard_rules = [hc["rule"] for hc in constraints["hard_constraints"]]
        soft_rules = constraints["soft_preferences"]
        implicit_rules = constraints["missing_implicit_constraints"]

        all_rules = hard_rules + soft_rules
        if variant_tier in ["structured", "advanced"]:
            all_rules += implicit_rules

        # Identify critical rules for RAL echo
        critical_rules = [
            hc["rule"] for hc in constraints["hard_constraints"]
            if hc["criticality"] == "high"
        ]
        if not critical_rules and hard_rules:
            critical_rules = hard_rules[:3]

        if variant_tier == "conservative":
            parts = [f"TASK:\n{task}"]
            if context:
                parts.append(f"\nCONTEXT:\n{context}")
            if all_rules:
                parts.append(f"\nCONSTRAINTS:\n{format_list_as_bullet_points(all_rules)}")
            return "\n".join(parts)

        elif variant_tier == "structured":
            parts = [
                f"### TASK\n{task}",
            ]
            if context:
                parts.append(f"\n### CONTEXT\n{context}")
            if all_rules:
                parts.append(f"\n### SYSTEM CONSTRAINTS (MANDATORY)\n{format_list_as_bullet_points(all_rules)}")

            sys_prompt = "\n".join(parts)
            # Apply RAL echo
            if critical_rules:
                sys_prompt = apply_ral_writer_constraint_restatement(
                    system_prompt=sys_prompt,
                    critical_constraints_to_echo=critical_rules,
                    provider=provider,
                )
            return sys_prompt

        else: # advanced
            parts = [
                "=" * 40,
                "CORE TASK DIRECTIVE",
                "=" * 40,
                task,
            ]
            if context:
                parts.extend(["", "=" * 40, "BACKGROUND CONTEXT", "=" * 40, context])

            parts.extend([
                "",
                "=" * 40,
                "ISOLATED CONSTRAINT BLOCK (MUST OEY)",
                "=" * 40,
            ])

            if hard_rules:
                parts.append("\nHARD CONSTRAINTS:")
                parts.append(format_list_as_bullet_points(hard_rules))
            if implicit_rules:
                parts.append("\nIMPLICIT/STRUCTURAL BOUNDARIES:")
                parts.append(format_list_as_bullet_points(implicit_rules))
            if soft_rules:
                parts.append("\nSTYLE PREFERENCES:")
                parts.append(format_list_as_bullet_points(soft_rules))

            sys_prompt = "\n".join(parts)
            # Apply intense RAL echo
            if critical_rules:
                sys_prompt = apply_ral_writer_constraint_restatement(
                    system_prompt=sys_prompt,
                    critical_constraints_to_echo=critical_rules,
                    provider=provider,
                )
            return sys_prompt

    # ──────────────────────────────────────────────────────────────────────
    # Main Workflow
    # ──────────────────────────────────────────────────────────────────────

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[List[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:
        logger.info("Executing RAL-Writer constraint restatement optimisation.")

        enriched_prompt = integrate_gap_interview_answers_into_prompt(
            raw_prompt=request.raw_prompt,
            gap_interview_answers=request.answers,
            gap_analysis_data=request.gap_data,
        )

        constraints = await self._extract_constraints(
            enriched_prompt, request.provider, request.model_id, request.api_key,
        )
        disentangled = await self._disentangle_narrative(
            enriched_prompt, request.provider, request.model_id, request.api_key,
        )

        variant_1 = self._assemble_variant(disentangled, constraints, "conservative", request.provider)
        variant_2 = self._assemble_variant(disentangled, constraints, "structured", request.provider)
        variant_3 = self._assemble_variant(disentangled, constraints, "advanced", request.provider)

        variant_1 = inject_input_variables_block(variant_1, request.input_variables, request.provider)
        variant_2 = inject_input_variables_block(variant_2, request.input_variables, request.provider)
        variant_3 = inject_input_variables_block(variant_3, request.input_variables, request.provider)

        adv_prefill = generate_claude_prefill_suggestion(request.task_type, request.provider)

        hard_count = len(constraints["hard_constraints"])
        impl_count = len(constraints["missing_implicit_constraints"])

        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy="Constraints extracted from narrative into a dedicated primacy block.",
                system_prompt=variant_1.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(variant_1) // 4,
                tcrte_scores=VariantTCRTEScores(task=75, context=70, role=50, tone=75, execution=80),
                strengths=[
                    "Clean separation of task and constraints",
                    "Preserves original instructions",
                ],
                best_for="Simple tasks with few constraints",
                overshoot_guards=[], undershoot_guards=[],
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy="Isolated primacy constraint block + RAL-Writer recency echo.",
                system_prompt=variant_2.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(variant_2) // 4,
                tcrte_scores=VariantTCRTEScores(task=80, context=75, role=60, tone=80, execution=85),
                strengths=[
                    "Critical constraints echoed in recency zone",
                    f"{impl_count} implicit boundaries made explicit",
                ],
                best_for="Tasks with constraint dilution risks",
                overshoot_guards=[], undershoot_guards=[],
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy="High-contrast structural isolation + full RAL-Writer echo.",
                system_prompt=variant_3.strip(),
                user_prompt="[Insert request data here]",
                prefill_suggestion=adv_prefill,
                token_estimate=len(variant_3) // 4,
                tcrte_scores=VariantTCRTEScores(task=90, context=85, role=70, tone=85, execution=95),
                strengths=[
                    "Maximum constraint enforcement",
                    "High-contrast structural borders",
                ],
                best_for="Complex tasks with high constraint density",
                overshoot_guards=[], undershoot_guards=[],
            ),
        ]

        issues = [constraints["summary"]]
        if constraints["conflicts"]:
            issues.extend(constraints["conflicts"])
        if impl_count > 0:
            issues.append(f"Prompt relies on {impl_count} implicit boundaries that models often violate.")

        analysis = OptimizationAnalysis(
            detected_issues=issues,
            model_notes=f"Extracted {hard_count} hard constraints. Density: {constraints['constraint_density']}.",
            framework_applied="ral_writer",
            coverage_delta=compute_coverage_delta_description(request.gap_data, 85),
            auto_selected_framework="ral_writer" if auto_reason else None,
            auto_reason=auto_reason,
        )

        response = OptimizationResponse(
            analysis=analysis,
            techniques_applied=[
                "Constraint Disentanglement",
                "Implicit Rule Surfacing",
                "Structural Isolation",
                "RAL-Writer Recency Echo",
            ],
            variants=variants,
        )

        return await self._refine_variants_with_quality_critique(
            response=response,
            raw_prompt=request.raw_prompt,
            task_type=request.task_type,
            api_key=request.api_key,
            quality_gate_mode=request.quality_gate_mode,
            target_model=request.model_id,
        )

if __name__ == "__main__":
    import asyncio, os, sys
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent.parent.parent / ".env")

    TEST_PROMPT = "Write a summary of the uploaded document. It should be professional, under 200 words, don't use bullet points, and highlight the main financial risks. Make sure it's formatting in JSON with keys 'summary' and 'risks'."

    async def test():
        key = os.getenv("OPENAI_API_KEY")
        if not key: sys.exit(1)
        req = OptimizationRequest(raw_prompt=TEST_PROMPT, provider="openai", model_id="gpt-4.1-nano", api_key=key)
        res = await RalWriterOptimizer().generate_variants(request=req)
        print(f"✓ Framework: {res.analysis.framework_applied}")
        print(f"✓ Issues: {res.analysis.detected_issues}")
    asyncio.run(test())
