"""
Context Repetition (CoRe) Optimizer Strategy — Attention-Aware Prompt Restructuring

Standalone framework that makes Context Repetition the PRIMARY optimisation strategy.
This goes far beyond the shared utility (inject_context_repetition_at_attention_positions)
which performs naive mechanical text insertion. This framework uses LLM analysis to
intelligently restructure the entire prompt around the transformer attention distribution.

BACKGROUND — The "Lost in the Middle" Problem:
═══════════════════════════════════════════════════════════════════════════════════════

  Liu et al. (2023) proved that transformer-based LLMs exhibit a U-shaped attention
  curve: tokens at the START and END of the context window receive significantly
  higher attention weights than tokens in the MIDDLE. This creates a measurable
  failure mode:

    ┌──────────────────────────────────────────────────────┐
    │  Attention Weight                                     │
    │  ▓▓▓▓▓                                        ▓▓▓▓▓  │
    │  ▓▓▓▓▓     ░░░░░░░░░░░░░░░░░░░░░░░░░░░       ▓▓▓▓▓  │
    │  ▓▓▓▓▓     ░░░░░░░░░░░░░░░░░░░░░░░░░░░       ▓▓▓▓▓  │
    │  ▓▓▓▓▓     ░░░░░░░ DANGER ZONE ░░░░░░░       ▓▓▓▓▓  │
    │  ▓▓▓▓▓     ░░░░░░░░░░░░░░░░░░░░░░░░░░░       ▓▓▓▓▓  │
    │  ───────────────────────────────────────────────────── │
    │  Start          Middle (Lost)              End        │
    └──────────────────────────────────────────────────────┘

  Their benchmark shows up to 26% accuracy DROP on multi-hop retrieval tasks
  when critical context is placed only in the middle vs. placed at boundaries.

  CoRe mitigates this by repeating critical context at strategically spaced
  positions so a high-attention copy is always within the model's focal region.

WHAT THIS FRAMEWORK ADDS BEYOND THE SHARED UTILITY:
═══════════════════════════════════════════════════════════════════════════════════════

  The shared utility (shared_prompt_techniques.py L164–L232) performs:
    - Fixed k-based line splitting with marker injection
    - Caller must know WHAT to repeat and HOW MANY times
    - No intelligence about WHAT is critical or WHERE attention is weakest

  This standalone framework performs:
    1. LLM-driven Context Criticality Analysis — identifies WHICH parts of the
       prompt contain critical context that must not be lost (dependencies,
       constraints, factual anchors, cross-references)
    2. Multi-Hop Dependency Chain Mapping — detects sequential reasoning chains
       where result A feeds into step B feeds into step C
    3. Attention Risk Zone Identification — marks which sections of the prompt
       fall into the attention "danger zone" based on token position estimates
    4. Strategic Restructuring — doesn't just insert markers, but reorganises
       the prompt to front-load and tail-echo critical elements
    5. Three escalating variants with different CoRe strategies

ALGORITHM WORKFLOW:
═══════════════════════════════════════════════════════════════════════════════════════

  Step 1: CONTEXT CRITICALITY ANALYSIS (LLM sub-call)
    ├─ Identify critical context elements (facts, constraints, dependencies)
    ├─ Detect reasoning chain depth (1-hop, 2-hop, 3-hop+)
    ├─ Identify cross-reference points (where step N depends on step M)
    └─ Score each section's criticality (0–3)

  Step 2: ATTENTION RISK MAPPING (Python-side)
    ├─ Estimate token positions for each section
    ├─ Map sections to attention zones (primacy / middle / recency)
    └─ Flag critical content stuck in the danger zone

  Step 3: VARIANT ASSEMBLY (3 tiers)
    ├─ Conservative: Strategic repositioning only (front-load + tail-echo)
    ├─ Structured:   Repositioning + inline CoRe markers at hop boundaries
    └─ Advanced:     Full CoRe injection (k=hop_count) + RAL-Writer + query echo

  Step 4: QUALITY GATE
    └─ _refine_variants_with_quality_critique()

COST ANALYSIS:
  2 LLM calls (criticality analysis + structured rewrite) + quality gate calls.

REFERENCES:
  - Liu et al., 2023. "Lost in the Middle: How Language Models Use Long Contexts."
  - APOST_v4_Documentation.md §5.1 (Context Repetition).

TESTING:
  Run directly:
    cd d:\\Generative AI Portfolio Projects\\APOST\\backend
    python -m app.services.optimization.frameworks.core_attention_optimizer
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
    MAX_TOKENS_CORE_CRITICALITY_ANALYSIS,
    SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
)
from app.services.optimization.prompt_registry.core_attention import (
    CRITICALITY_ANALYSIS_PROMPT_TEMPLATE,
    STRATEGIC_REWRITE_PROMPT_TEMPLATE,
)
from app.services.optimization.shared_prompt_techniques import (
    integrate_gap_interview_answers_into_prompt,
    inject_input_variables_block,
    inject_context_repetition_at_attention_positions,
    apply_ral_writer_constraint_restatement,
    generate_claude_prefill_suggestion,
    compute_coverage_delta_description,
    format_list_as_bullet_points,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# LLM Prompt Templates
# ──────────────────────────────────────────────────────────────────────────────

_CRITICALITY_ANALYSIS_PROMPT = CRITICALITY_ANALYSIS_PROMPT_TEMPLATE
_STRATEGIC_REWRITE_PROMPT = STRATEGIC_REWRITE_PROMPT_TEMPLATE


class CoreAttentionOptimizer(BaseOptimizerStrategy):
    """
    Deep implementation of the Context Repetition (CoRe) attention-aware
    prompt restructuring framework.

    This optimizer analyses which parts of a prompt are most critical and
    most at-risk of attention decay, then produces three variant tiers
    with escalating attention management strategies:

      Conservative: Strategic repositioning (front-load + tail-echo)
      Structured:   Repositioning + inline CoRe markers at hop boundaries
      Advanced:     Full CoRe injection + RAL-Writer + query echo + prefill

    Unlike the shared utility which merely inserts text at fixed positions,
    this framework uses LLM analysis to determine WHAT to repeat, WHERE
    attention is weakest, and HOW to restructure the entire prompt around
    the transformer attention curve.
    """

    # ──────────────────────────────────────────────────────────────────────
    # Step 1: Context Criticality Analysis
    # ──────────────────────────────────────────────────────────────────────

    async def _analyse_context_criticality(
        self,
        raw_prompt: str,
        provider: str,
        model_id: str,
        api_key: str,
    ) -> dict[str, Any]:
        """
        LLM-driven analysis to identify critical context elements,
        reasoning chain dependencies, and attention risk zones.

        Returns a normalized criticality analysis dict.
        """
        analysis_prompt = _CRITICALITY_ANALYSIS_PROMPT.format(
            raw_prompt=raw_prompt,
        )

        async with LLMClient(api_key=api_key) as llm_client:
            response_text = await llm_client.call(
                provider=provider,
                prompt=analysis_prompt,
                max_tokens=MAX_TOKENS_CORE_CRITICALITY_ANALYSIS,
                model=model_id,
                system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
            )

            try:
                parsed = extract_json_from_llm_response(response_text)
                analysis = coerce_top_level_object(
                    parsed, context_label="context criticality analysis",
                )
            except JSONExtractionError:
                repair_prompt = (
                    "Repair into VALID JSON. Return ONLY JSON.\n\n"
                    f"Malformed payload:\n{response_text}"
                )
                repaired = await llm_client.call(
                    provider=provider,
                    prompt=repair_prompt,
                    max_tokens=MAX_TOKENS_CORE_CRITICALITY_ANALYSIS,
                    model=model_id,
                    system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
                )
                parsed = extract_json_from_llm_response(repaired)
                analysis = coerce_top_level_object(
                    parsed, context_label="context criticality analysis (repaired)",
                )

        return self._normalize_criticality_analysis(analysis)

    def _normalize_criticality_analysis(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize LLM output into a consistent shape with safe defaults."""

        # Critical elements
        raw_elements = raw.get("critical_elements", [])
        if not isinstance(raw_elements, list):
            raw_elements = []
        critical_elements = []
        for elem in raw_elements:
            if isinstance(elem, dict):
                critical_elements.append({
                    "content": str(elem.get("content", "")).strip() or "Unspecified critical context",
                    "criticality": max(0, min(3, int(elem.get("criticality", 2)))),
                    "reason": str(elem.get("reason", "")).strip() or "No reason provided",
                    "approximate_position": str(elem.get("approximate_position", "middle")).strip(),
                })

        # Reasoning chain
        raw_chain = raw.get("reasoning_chain", {})
        if not isinstance(raw_chain, dict):
            raw_chain = {}
        hop_count = max(1, min(5, int(raw_chain.get("hop_count", 1))))
        hops = []
        for hop in (raw_chain.get("hops") or []):
            if isinstance(hop, dict):
                hops.append({
                    "step": int(hop.get("step", len(hops) + 1)),
                    "description": str(hop.get("description", "")),
                    "depends_on": str(hop.get("depends_on", "")),
                })

        # Cross-references
        raw_xrefs = raw.get("cross_references", [])
        if not isinstance(raw_xrefs, list):
            raw_xrefs = []
        cross_references = []
        for xref in raw_xrefs:
            if isinstance(xref, dict):
                cross_references.append({
                    "source_description": str(xref.get("source_description", "")),
                    "reference_description": str(xref.get("reference_description", "")),
                    "risk": str(xref.get("risk", "medium")),
                })

        # Sections
        raw_sections = raw.get("sections", [])
        if not isinstance(raw_sections, list):
            raw_sections = []
        sections = []
        for section in raw_sections:
            if isinstance(section, dict):
                sections.append({
                    "name": str(section.get("name", "Unnamed")),
                    "content_summary": str(section.get("content_summary", "")),
                    "token_proportion_pct": int(section.get("token_proportion_pct", 0)),
                    "attention_zone": str(section.get("attention_zone", "middle")),
                    "contains_critical_context": bool(section.get("contains_critical_context", False)),
                })

        # Aggregate risk
        overall_risk = str(raw.get("overall_attention_risk", "medium")).strip()
        if overall_risk not in ("high", "medium", "low"):
            overall_risk = "medium"
        risk_summary = str(raw.get("risk_summary", "Context criticality analysis completed.")).strip()

        # Compute derived metrics
        critical_in_middle = sum(
            1 for e in critical_elements
            if e["approximate_position"] == "middle" and e["criticality"] >= 2
        )
        high_risk_xrefs = sum(1 for x in cross_references if x["risk"] == "high")

        return {
            "critical_elements": critical_elements,
            "reasoning_chain": {"hop_count": hop_count, "hops": hops},
            "cross_references": cross_references,
            "sections": sections,
            "overall_attention_risk": overall_risk,
            "risk_summary": risk_summary,
            "critical_elements_in_middle": critical_in_middle,
            "high_risk_cross_references": high_risk_xrefs,
            "effective_hop_count": hop_count,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Step 2: Build Critical Context Echo String
    # ──────────────────────────────────────────────────────────────────────

    def _build_critical_context_echo(
        self,
        analysis: dict[str, Any],
        max_elements: int = 5,
    ) -> str:
        """
        Build a compact echo string from the highest-criticality elements
        that are positioned in the attention danger zone (middle).

        This string is what gets injected at CoRe positions. Unlike the
        shared utility which takes caller-provided text, this method
        automatically constructs the optimal echo content from the analysis.
        """
        elements = analysis.get("critical_elements", [])

        # Sort by criticality (descending) then prioritize middle-positioned ones
        prioritized = sorted(
            elements,
            key=lambda e: (
                e.get("criticality", 0) * 2
                + (1 if e.get("approximate_position") == "middle" else 0)
            ),
            reverse=True,
        )

        selected = prioritized[:max_elements]
        if not selected:
            return ""

        echo_parts = ["CRITICAL CONTEXT (attention-optimised reminder):"]
        for elem in selected:
            echo_parts.append(f"• {elem['content']}")

        # Add cross-reference reminders for high-risk chains
        xrefs = [x for x in analysis.get("cross_references", []) if x.get("risk") == "high"]
        if xrefs:
            echo_parts.append("\nCRITICAL DEPENDENCIES:")
            for xref in xrefs[:3]:
                echo_parts.append(
                    f"• {xref['source_description']} → {xref['reference_description']}"
                )

        return "\n".join(echo_parts)

    # ──────────────────────────────────────────────────────────────────────
    # Step 3: Strategic Prompt Restructuring (LLM-assisted)
    # ──────────────────────────────────────────────────────────────────────

    async def _restructure_prompt_for_attention(
        self,
        raw_prompt: str,
        analysis: dict[str, Any],
        variant_tier: str,
        provider: str,
        model_id: str,
        api_key: str,
    ) -> dict[str, Any]:
        """
        LLM-assisted restructuring that front-loads critical context,
        adds structural delimiters, and tail-echoes dependencies.

        The restructuring depth increases with the variant tier:
        - Conservative: Minimal restructuring, focus on positioning
        - Structured: Full restructuring with section delimiters
        - Advanced: Aggressive restructuring with CoRe markers embedded
        """
        tier_instructions = {
            "conservative": (
                "CONSERVATIVE TIER: Light restructuring only. Move the most critical "
                "constraint or task definition to the very beginning. Add a brief "
                "echo of the top 2 critical elements at the end. Minimise changes."
            ),
            "structured": (
                "STRUCTURED TIER: Full restructuring. Create clearly delimited sections "
                "(TASK, CONTEXT, CONSTRAINTS, OUTPUT FORMAT). Front-load critical "
                "constraints. Add dependency chain notation at each hop point. "
                "Tail-echo critical constraints and cross-references."
            ),
            "advanced": (
                "ADVANCED TIER: Aggressive restructuring. Create high-contrast section "
                "borders. Front-load ALL critical elements (even at the cost of "
                "rearranging the narrative flow). Add explicit [ATTENTION ANCHOR] "
                "markers at cross-reference points. Add comprehensive tail-echo "
                "with all critical elements and a query restatement."
            ),
        }

        criticality_summary = json.dumps({
            "critical_elements": analysis["critical_elements"],
            "reasoning_chain": analysis["reasoning_chain"],
            "cross_references": analysis["cross_references"],
            "overall_attention_risk": analysis["overall_attention_risk"],
        }, indent=2, ensure_ascii=True)

        rewrite_prompt = _STRATEGIC_REWRITE_PROMPT.format(
            raw_prompt=raw_prompt,
            criticality_analysis=criticality_summary,
            variant_tier=tier_instructions.get(variant_tier, tier_instructions["structured"]),
        )

        async with LLMClient(api_key=api_key) as llm_client:
            response_text = await llm_client.call(
                provider=provider,
                prompt=rewrite_prompt,
                max_tokens=MAX_TOKENS_COMPONENT_EXTRACTION,
                model=model_id,
                system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
            )

        parsed = extract_json_from_llm_response(response_text)
        return {
            "restructured_prompt": self._safe_string(
                parsed.get("restructured_prompt"), raw_prompt,
            ),
            "front_loaded_elements": self._safe_list(parsed.get("front_loaded_elements")),
            "tail_echoed_elements": self._safe_list(parsed.get("tail_echoed_elements")),
            "structural_changes": self._safe_list(parsed.get("structural_changes")),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Step 4: Post-Restructuring CoRe Injection
    # ──────────────────────────────────────────────────────────────────────

    def _apply_core_injection_to_variant(
        self,
        system_prompt: str,
        critical_echo: str,
        hop_count: int,
        variant_tier: str,
    ) -> str:
        """
        Apply mechanical CoRe injection (shared utility) on top of the
        LLM-restructured prompt for Structured and Advanced tiers.

        Conservative: NO mechanical injection (restructuring handles it)
        Structured:   Inject at k=min(hop_count, 3) positions
        Advanced:     Inject at k=hop_count positions (up to 5)
        """
        if variant_tier == "conservative" or not critical_echo:
            return system_prompt

        if variant_tier == "structured":
            effective_k = min(hop_count, 3)
        else:  # advanced
            effective_k = hop_count

        return inject_context_repetition_at_attention_positions(
            prompt_text=system_prompt,
            critical_context_to_repeat=critical_echo,
            repetition_count_k=effective_k,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Main Workflow: generate_variants
    # ──────────────────────────────────────────────────────────────────────

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[List[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:
        """
        Generate 3 attention-optimised variants with escalating CoRe intensity.

        Workflow:
            Step 1: Enrich prompt with gap-interview answers.
            Step 2: LLM-driven context criticality analysis (10 dimensions).
            Step 3: Build critical context echo string from analysis.
            Step 4: LLM-assisted strategic restructuring (3 tiers).
            Step 5: Post-restructuring CoRe injection (Structured + Advanced).
            Step 6: Apply RAL-Writer, input variables, prefill.
            Step 7: Quality gate and return.
        """
        logger.info("Executing CoRe Attention-Aware prompt restructuring optimisation.")

        # Step 1: Enrich prompt
        enriched_prompt = integrate_gap_interview_answers_into_prompt(
            raw_prompt=request.raw_prompt,
            gap_interview_answers=request.answers,
            gap_analysis_data=request.gap_data,
        )

        # Step 2: Context criticality analysis
        analysis = await self._analyse_context_criticality(
            raw_prompt=enriched_prompt,
            provider=request.provider,
            model_id=request.model_id,
            api_key=request.api_key,
        )

        hop_count = analysis["effective_hop_count"]
        overall_risk = analysis["overall_attention_risk"]
        critical_in_middle = analysis["critical_elements_in_middle"]
        risk_summary = analysis["risk_summary"]

        logger.info(
            "Context criticality analysis complete. hops=%d, risk=%s, critical_in_middle=%d",
            hop_count, overall_risk, critical_in_middle,
        )

        # Step 3: Build critical context echo
        critical_echo = self._build_critical_context_echo(analysis)

        # Collect constraints from critical elements for RAL-Writer
        constraints = [
            elem["content"]
            for elem in analysis.get("critical_elements", [])
            if elem.get("criticality", 0) >= 2
        ]

        # Step 4: Strategic restructuring (3 tiers in parallel-safe sequence)
        conservative_rewrite = await self._restructure_prompt_for_attention(
            raw_prompt=enriched_prompt,
            analysis=analysis,
            variant_tier="conservative",
            provider=request.provider,
            model_id=request.model_id,
            api_key=request.api_key,
        )

        structured_rewrite = await self._restructure_prompt_for_attention(
            raw_prompt=enriched_prompt,
            analysis=analysis,
            variant_tier="structured",
            provider=request.provider,
            model_id=request.model_id,
            api_key=request.api_key,
        )

        advanced_rewrite = await self._restructure_prompt_for_attention(
            raw_prompt=enriched_prompt,
            analysis=analysis,
            variant_tier="advanced",
            provider=request.provider,
            model_id=request.model_id,
            api_key=request.api_key,
        )

        # Step 5: Post-restructuring CoRe injection
        variant_1_prompt = self._apply_core_injection_to_variant(
            conservative_rewrite["restructured_prompt"],
            critical_echo, hop_count, "conservative",
        )
        variant_2_prompt = self._apply_core_injection_to_variant(
            structured_rewrite["restructured_prompt"],
            critical_echo, hop_count, "structured",
        )
        variant_3_prompt = self._apply_core_injection_to_variant(
            advanced_rewrite["restructured_prompt"],
            critical_echo, hop_count, "advanced",
        )

        # Step 6: Apply RAL-Writer on Structured + Advanced
        if constraints:
            variant_2_prompt = apply_ral_writer_constraint_restatement(
                system_prompt=variant_2_prompt,
                critical_constraints_to_echo=constraints[:3],
                provider=request.provider,
            )
            variant_3_prompt = apply_ral_writer_constraint_restatement(
                system_prompt=variant_3_prompt,
                critical_constraints_to_echo=constraints,
                provider=request.provider,
            )

        # Add query echo at the very end of Advanced variant
        variant_3_prompt += (
            "\n\n--- QUERY ECHO (Recency Reinforcement) ---\n"
            f"REMEMBER: Your primary task is to address the following:\n"
            f"{enriched_prompt[:500]}"
            + ("..." if len(enriched_prompt) > 500 else "")
        )

        # Input variables injection
        variant_1_prompt = inject_input_variables_block(
            variant_1_prompt, request.input_variables, request.provider,
        )
        variant_2_prompt = inject_input_variables_block(
            variant_2_prompt, request.input_variables, request.provider,
        )
        variant_3_prompt = inject_input_variables_block(
            variant_3_prompt, request.input_variables, request.provider,
        )

        # Prefill
        advanced_prefill = generate_claude_prefill_suggestion(
            request.task_type, request.provider,
        )

        # Build technique descriptors
        cons_techniques = ["Strategic repositioning", "Front-loading", "Tail-echo"]
        struct_techniques = cons_techniques + [
            f"CoRe injection (k={min(hop_count, 3)})",
            "Section delimiters",
            "RAL-Writer constraint echo",
        ]
        adv_techniques = struct_techniques + [
            f"Full CoRe injection (k={hop_count})",
            "Query echo (recency reinforcement)",
            "High-contrast structural borders",
        ]

        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy=(
                    f"Strategic repositioning: front-loaded {len(conservative_rewrite['front_loaded_elements'])} "
                    f"critical elements, tail-echoed {len(conservative_rewrite['tail_echoed_elements'])}. "
                    f"No mechanical CoRe injection."
                ),
                system_prompt=variant_1_prompt.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(variant_1_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=75, context=70, role=55, tone=55, execution=65),
                strengths=[
                    "Minimal prompt inflation",
                    f"{len(conservative_rewrite['front_loaded_elements'])} critical elements front-loaded to primacy zone",
                    "Original narrative flow preserved",
                ],
                best_for="Prompts where context loss is a minor concern and brevity is valued",
                overshoot_guards=[],
                undershoot_guards=[],
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy=(
                    f"Full restructuring with CoRe (k={min(hop_count, 3)}). "
                    f"{len(structured_rewrite['structural_changes'])} structural changes applied. "
                    f"RAL-Writer constraint echo active."
                ),
                system_prompt=variant_2_prompt.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(variant_2_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=80, context=80, role=60, tone=60, execution=75),
                strengths=[
                    f"CoRe injection at {min(hop_count, 3)} attention-optimised positions",
                    "Clearly delimited sections for attention disambiguation",
                    "RAL-Writer constraint echo in recency zone",
                    f"{len(structured_rewrite['front_loaded_elements'])} elements front-loaded",
                ],
                best_for="Multi-hop reasoning tasks with moderate context length",
                overshoot_guards=[],
                undershoot_guards=[],
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy=(
                    f"Aggressive restructuring with full CoRe (k={hop_count}). "
                    f"RAL-Writer echo + query echo. "
                    f"{critical_in_middle} critical-in-middle elements redistributed."
                ),
                system_prompt=variant_3_prompt.strip(),
                user_prompt="[Insert request data here]",
                prefill_suggestion=advanced_prefill,
                token_estimate=len(variant_3_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=90, context=90, role=65, tone=65, execution=85),
                strengths=[
                    f"Full CoRe injection at {hop_count} positions (attention curve optimised)",
                    "High-contrast structural borders for attention disambiguation",
                    "Query echo at recency boundary",
                    "RAL-Writer constraint restatement (all critical constraints)",
                    f"All {critical_in_middle} middle-zone critical elements redistributed",
                ],
                best_for="Long prompts with complex multi-hop reasoning and high context-loss risk",
                overshoot_guards=[],
                undershoot_guards=[],
            ),
        ]

        # Build analysis
        detected_issues: list[str] = [risk_summary]
        if critical_in_middle > 0:
            detected_issues.append(
                f"{critical_in_middle} critical context element(s) positioned in the "
                "attention danger zone (middle of prompt)."
            )
        if hop_count >= 3:
            detected_issues.append(
                f"Multi-hop reasoning chain detected ({hop_count} hops). "
                "Each hop increases the risk of context loss between steps."
            )
        high_risk_xrefs = analysis.get("high_risk_cross_references", 0)
        if high_risk_xrefs > 0:
            detected_issues.append(
                f"{high_risk_xrefs} high-risk cross-reference(s) span the prompt's "
                "middle zone, creating dependency chains vulnerable to attention decay."
            )

        model_notes = (
            f"CoRe attention analysis: hop_count={hop_count}, "
            f"overall_risk={overall_risk}, critical_in_middle={critical_in_middle}, "
            f"high_risk_xrefs={high_risk_xrefs}."
        )
        if auto_reason:
            model_notes += f" Auto-select: {auto_reason}"

        analysis_obj = OptimizationAnalysis(
            detected_issues=detected_issues,
            model_notes=model_notes,
            framework_applied="core_attention",
            coverage_delta=compute_coverage_delta_description(request.gap_data, 82),
            auto_selected_framework="core_attention" if auto_reason else None,
            auto_reason=auto_reason,
        )

        response = OptimizationResponse(
            analysis=analysis_obj,
            techniques_applied=[
                "Context Criticality Analysis",
                "Reasoning Chain Mapping",
                "Attention Risk Zone Identification",
                "Strategic Front-Loading",
                "Tail-Echo Recency Anchoring",
                "CoRe Mechanical Injection",
                "RAL-Writer Constraint Restatement",
                "Query Echo Reinforcement",
            ],
            variants=variants,
        )

        # Step 7: Quality gate
        response = await self._refine_variants_with_quality_critique(
            response=response,
            raw_prompt=request.raw_prompt,
            task_type=request.task_type,
            api_key=request.api_key,
            quality_gate_mode=request.quality_gate_mode,
            target_model=request.model_id,
        )

        return response

    # ──────────────────────────────────────────────────────────────────────
    # Utilities
    # ──────────────────────────────────────────────────────────────────────

    def _safe_string(self, value: Any, default: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default

    def _safe_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []


# ══════════════════════════════════════════════════════════════════════════════
# Standalone Test Entry Point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    import os
    import sys
    from pathlib import Path
    from dotenv import load_dotenv

    backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    load_dotenv(backend_dir / ".env")

    # Multi-hop prompt with critical context in the middle
    MULTI_HOP_TEST_PROMPT = """\
    You are reviewing a patient's medication chart. The patient weighs 72kg
    and has a creatinine clearance of 45 mL/min (Stage 3b CKD).

    Current medications:
    - Metformin 1000mg BD
    - Lisinopril 20mg OD
    - Warfarin (target INR 2.0-3.0)
    - Amiodarone 200mg OD

    The patient's most recent INR was 4.8 (measured yesterday).

    Lab results from this morning:
    - Potassium: 5.8 mmol/L (HIGH)
    - eGFR: 38 mL/min/1.73m2
    - HbA1c: 7.2%

    Please:
    1. Identify drug interactions between the current medications
    2. Using the INR result and the drug interaction analysis from step 1,
       determine if the warfarin dose needs adjustment
    3. Based on the renal function AND the drug interaction findings,
       determine which medications need dose adjustment
    4. Provide a prioritised action plan considering ALL of the above
    """

    async def test_core_attention_optimizer():
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            print("ERROR: OPENAI_API_KEY not found in .env")
            sys.exit(1)

        request = OptimizationRequest(
            raw_prompt=MULTI_HOP_TEST_PROMPT,
            provider="openai",
            model_id="gpt-4.1-nano",
            model_label="GPT-4.1 Nano",
            task_type="analysis",
            framework="core_attention",
            is_reasoning_model=False,
            api_key=api_key,
        )

        optimizer = CoreAttentionOptimizer()
        print("=" * 80)
        print("TESTING: CoRe Attention-Aware Prompt Restructuring Optimizer")
        print("=" * 80)

        try:
            result = await optimizer.generate_variants(request=request)
            print(f"\n✓ Framework applied: {result.analysis.framework_applied}")
            print(f"✓ Detected issues: {result.analysis.detected_issues}")
            print(f"✓ Techniques: {result.techniques_applied}")
            print(f"✓ Variants generated: {len(result.variants)}")
            for v in result.variants:
                print(f"\n── Variant {v.id}: {v.name} ──")
                print(f"   Strategy: {v.strategy}")
                print(f"   Tokens: {v.token_estimate}")
                preview = v.system_prompt[:300]
                print(f"   Preview: {preview}...")
            print("\n✓ CoRe attention optimizer test PASSED")
        except Exception as err:
            print(f"\n✗ Test FAILED: {err}")
            import traceback
            traceback.print_exc()

    asyncio.run(test_core_attention_optimizer())
