"""
Overshoot/Undershoot Failure Mode Prevention Optimizer Strategy

Implements a dual failure‐mode detection and prevention engine that
analyses a prompt for BOTH classes of generation failure:

  Overshooting — the model generates output that is too long, too detailed,
                 hallucinating beyond scope, or including unnecessary caveats.
  Undershooting — the model generates output that skips required sections,
                  omits edge cases, gives superficial answers, or misses
                  hard constraints.

ALGORITHM WORKFLOW:
═══════════════════════════════════════════════════════════════════════════════

  ┌───────────────────────────────────┐
  │  Overshoot/Undershoot Engine      │
  └────────────────┬──────────────────┘
                   │
                   ▼
  ┌───────────────────────────────────┐  Step 1: FAILURE MODE RISK ANALYSIS
  │  Risk Analyser (LLM Sub-Call)     │  LLM evaluates the raw prompt across
  │                                   │  5 overshoot risk dimensions and 5
  │                                   │  undershoot risk dimensions. Returns
  │                                   │  per-dimension severity scores and
  └────────────────┬──────────────────┘  concrete evidence strings.
                   │
                   ▼
  ┌───────────────────────────────────┐  Step 2: GUARD LIBRARY SELECTION
  │  Guard Selector (Python Logic)    │  Deterministic Python logic selects
  │                                   │  from a curated library of 10 guard
  │                                   │  templates based on risk severity
  └────────────────┬──────────────────┘  scores from Step 1.
                   │
                   ▼
  ┌───────────────────────────────────┐  Step 3: PROMPT REWRITE + INJECTION
  │  Variant Assembly (3 Tiers)       │  LLM sub-call rewrites the raw prompt
  │                                   │  with structural improvements, then
  │                                   │  Python injects the selected guards
  │                                   │  at escalating intensity:
  │                                   │    Conservative: overshoot guards only
  │                                   │    Structured:   balanced dual guards
  └────────────────┬──────────────────┘    Advanced:     aggressive dual + echo
                   │
                   ▼
  ┌───────────────────────────────────┐  Step 4: QUALITY GATE
  │  PromptQualityCritic              │  Standard shared quality evaluation
  └───────────────────────────────────┘  and optional enhancement pass.

COST ANALYSIS:
  2 LLM calls (risk analysis + structured rewrite) + quality gate calls.
  ~2000 tokens per call × 2 = ~4000 total tokens before quality gate.

REFERENCES:
  - "Overshoot and Undershoot in LLM Generation" — empirical observations
    from Meta-Prompting Research (Suzgun & Kalai, 2024).
  - APOST_v4_Documentation.md §5.4 (Failure mode guardrails).

TESTING:
  Run this file directly to test with a healthcare example:
    cd d:\\Generative AI Portfolio Projects\\APOST\\backend
    python -m app.services.optimization.frameworks.overshoot_undershoot_optimizer
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
    MAX_TOKENS_FAILURE_MODE_ANALYSIS,
    MAX_TOKENS_COMPONENT_EXTRACTION,
    SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
)
from app.services.optimization.prompt_registry.overshoot_undershoot import (
    FAILURE_MODE_ANALYSIS_PROMPT_TEMPLATE,
    STRUCTURAL_REWRITE_PROMPT_TEMPLATE,
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

_FAILURE_MODE_ANALYSIS_PROMPT = FAILURE_MODE_ANALYSIS_PROMPT_TEMPLATE

_FAILURE_MODE_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "overshoot_risks": {
            "type": "object",
            "properties": {
                "verbosity_risk": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "integer"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["severity", "evidence"],
                    "additionalProperties": False,
                },
                "hallucination_risk": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "integer"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["severity", "evidence"],
                    "additionalProperties": False,
                },
                "caveat_risk": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "integer"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["severity", "evidence"],
                    "additionalProperties": False,
                },
                "tangent_risk": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "integer"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["severity", "evidence"],
                    "additionalProperties": False,
                },
                "enumeration_risk": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "integer"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["severity", "evidence"],
                    "additionalProperties": False,
                },
            },
            "required": [
                "verbosity_risk",
                "hallucination_risk",
                "caveat_risk",
                "tangent_risk",
                "enumeration_risk",
            ],
            "additionalProperties": False,
        },
        "undershoot_risks": {
            "type": "object",
            "properties": {
                "completeness_risk": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "integer"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["severity", "evidence"],
                    "additionalProperties": False,
                },
                "depth_risk": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "integer"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["severity", "evidence"],
                    "additionalProperties": False,
                },
                "schema_risk": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "integer"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["severity", "evidence"],
                    "additionalProperties": False,
                },
                "edge_case_risk": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "integer"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["severity", "evidence"],
                    "additionalProperties": False,
                },
                "reasoning_risk": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "integer"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["severity", "evidence"],
                    "additionalProperties": False,
                },
            },
            "required": [
                "completeness_risk",
                "depth_risk",
                "schema_risk",
                "edge_case_risk",
                "reasoning_risk",
            ],
            "additionalProperties": False,
        },
        "overall_overshoot_score": {"type": "integer"},
        "overall_undershoot_score": {"type": "integer"},
        "dominant_failure_mode": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": [
        "overshoot_risks",
        "undershoot_risks",
        "overall_overshoot_score",
        "overall_undershoot_score",
        "dominant_failure_mode",
        "summary",
    ],
    "additionalProperties": False,
}


_STRUCTURAL_REWRITE_PROMPT = STRUCTURAL_REWRITE_PROMPT_TEMPLATE


# ──────────────────────────────────────────────────────────────────────────────
# Guard Template Library
#
# Each guard is a tuple of (guard_id, display_label, injection_text).
# Guards are selected based on risk severity scores from Step 1.
# ──────────────────────────────────────────────────────────────────────────────

_OVERSHOOT_GUARD_TEMPLATES: dict[str, tuple[str, str]] = {
    "scope_lock": (
        "Scope Lockdown",
        (
            "SCOPE CONSTRAINT: Restrict your response EXCLUSIVELY to the specific "
            "task described above. Do not discuss tangential topics, provide unsolicited "
            "background information, or speculate beyond the provided context."
        ),
    ),
    "length_calibration": (
        "Length Calibration",
        (
            "LENGTH CONSTRAINT: Your response should be focused and proportional to "
            "the complexity of the task. Prioritise precision over volume. Avoid "
            "restating the question, providing unnecessary preambles, or padding "
            "with filler content."
        ),
    ),
    "anti_hallucination": (
        "Anti-Hallucination",
        (
            "GROUNDING CONSTRAINT: Only reference information explicitly present in "
            "the provided input or context. If information is missing or insufficient, "
            "state that explicitly rather than fabricating plausible-sounding content. "
            "Do NOT invent data, statistics, citations, or facts."
        ),
    ),
    "anti_caveat": (
        "Anti-Caveat/Hedging",
        (
            "DIRECTNESS CONSTRAINT: Provide direct, actionable answers. Do NOT include "
            "generic disclaimers ('I'm an AI...'), unnecessary hedging ('It depends...'), "
            "or meta-commentary about the task itself. If you are uncertain about "
            "something specific, state the uncertainty precisely rather than adding "
            "blanket caveats."
        ),
    ),
    "enumeration_cap": (
        "Enumeration Cap",
        (
            "LIST CONSTRAINT: When generating lists, rankings, or enumerations, limit "
            "output to the most relevant items. Prioritise quality and relevance over "
            "exhaustive quantity. Each item must add distinct value — do not pad lists "
            "with marginal entries."
        ),
    ),
}

_UNDERSHOOT_GUARD_TEMPLATES: dict[str, tuple[str, str]] = {
    "exhaustiveness": (
        "Exhaustiveness Requirement",
        (
            "COMPLETENESS CONSTRAINT: You MUST address ALL sub-tasks, questions, or "
            "requirements stated in the prompt. Before finalising your response, verify "
            "that every explicitly requested element has been covered. An incomplete "
            "response is a failed response."
        ),
    ),
    "depth_floor": (
        "Depth Floor",
        (
            "DEPTH CONSTRAINT: For each point, finding, or recommendation, provide "
            "substantive detail — not just a label or one-liner. Include: (1) the "
            "specific observation, (2) the reasoning or evidence behind it, and "
            "(3) the practical implication or next step."
        ),
    ),
    "schema_completeness": (
        "Schema Completeness",
        (
            "SCHEMA CONSTRAINT: If an output format or schema is specified, every "
            "field MUST be populated with meaningful content. Do not use placeholder "
            "values, empty strings, or 'N/A' unless the task explicitly permits it. "
            "Missing fields constitute a failed response."
        ),
    ),
    "edge_case_coverage": (
        "Edge Case Coverage",
        (
            "EDGE CASE CONSTRAINT: Explicitly consider and address boundary conditions, "
            "special cases, exceptions, and failure modes relevant to the task. Do not "
            "assume the happy path is the only path. If edge cases exist, they must be "
            "acknowledged and handled."
        ),
    ),
    "reasoning_depth": (
        "Reasoning Depth",
        (
            "REASONING CONSTRAINT: Show your reasoning process for non-trivial "
            "conclusions. Do not jump to answers without explaining the logic, evidence, "
            "or analysis that led to them. Each conclusion must be traceable to a "
            "supporting observation or fact."
        ),
    ),
}

# Severity threshold: guard is selected when risk severity >= this value.
_GUARD_ACTIVATION_THRESHOLD_CONSERVATIVE = 3  # Only critical risks
_GUARD_ACTIVATION_THRESHOLD_STRUCTURED = 2    # Moderate + critical
_GUARD_ACTIVATION_THRESHOLD_ADVANCED = 1       # Low + moderate + critical


class OvershootUndershootOptimizer(BaseOptimizerStrategy):
    """
    Deep implementation of the Overshoot/Undershoot Failure Mode Prevention
    optimization framework.

    This optimizer analyses a prompt for both classes of generation failure —
    cases where the model produces too much (overshooting) and cases where it
    produces too little (undershooting) — and injects calibrated guardrails
    at three intensity tiers.

    Architecture:
        1. LLM sub-call to analyse 10 risk dimensions (5 overshoot + 5 undershoot)
        2. Python-side guard selection from a curated library of 10 guard templates
        3. LLM sub-call to structurally rewrite the prompt with clear task/scope/format
        4. Python-side guard injection at 3 escalating intensity levels
        5. Standard quality gate via _refine_variants_with_quality_critique()
    """

    # ──────────────────────────────────────────────────────────────────────
    # Step 1: Failure Mode Risk Analysis
    # ──────────────────────────────────────────────────────────────────────

    async def _analyse_failure_mode_risks(
        self,
        raw_prompt: str,
        provider: str,
        model_id: str,
        api_key: str,
    ) -> dict[str, Any]:
        """
        Analyse the prompt for overshoot and undershoot risk factors.

        Uses provider-aware structured response format where available,
        with a single repair retry for malformed payloads.

        Args:
            raw_prompt: The enriched raw prompt to analyse.
            provider: LLM provider string.
            model_id: Target model ID.
            api_key: API key for the LLM provider.

        Returns:
            Parsed risk analysis dict conforming to _FAILURE_MODE_ANALYSIS_SCHEMA.
        """
        analysis_prompt = _FAILURE_MODE_ANALYSIS_PROMPT.format(
            raw_prompt=raw_prompt,
        )
        response_format = self._structured_response_format_for_provider(
            provider, schema=_FAILURE_MODE_ANALYSIS_SCHEMA, name="failure_mode_analysis"
        )

        async with LLMClient(api_key=api_key) as llm_client:
            response_text = await llm_client.call(
                provider=provider,
                prompt=analysis_prompt,
                max_tokens=MAX_TOKENS_FAILURE_MODE_ANALYSIS,
                model=model_id,
                system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
                response_format=response_format,
            )

            try:
                parsed_payload = extract_json_from_llm_response(response_text)
                analysis = coerce_top_level_object(
                    parsed_payload,
                    context_label="failure mode risk analysis",
                )
            except JSONExtractionError:
                repair_prompt = (
                    "Repair the payload into VALID JSON matching this schema exactly.\n"
                    "Return ONLY JSON.\n\n"
                    f"Schema:\n{json.dumps(_FAILURE_MODE_ANALYSIS_SCHEMA, ensure_ascii=True)}\n\n"
                    f"Malformed payload:\n{response_text}"
                )
                repaired_response = await llm_client.call(
                    provider=provider,
                    prompt=repair_prompt,
                    max_tokens=MAX_TOKENS_FAILURE_MODE_ANALYSIS,
                    model=model_id,
                    system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
                    response_format=response_format,
                )
                repaired_payload = extract_json_from_llm_response(repaired_response)
                analysis = coerce_top_level_object(
                    repaired_payload,
                    context_label="failure mode risk analysis (repaired)",
                )

        return self._normalize_risk_analysis(analysis)

    def _normalize_risk_analysis(self, raw_analysis: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize the LLM-returned risk analysis into a consistent shape.

        Ensures all severity values are clamped to [0, 3] and all evidence
        strings are non-empty. Provides safe defaults for missing keys.
        """
        def normalize_risk_group(group_data: Any, expected_keys: list[str]) -> dict[str, dict]:
            if not isinstance(group_data, dict):
                return {k: {"severity": 2, "evidence": "No analysis available."} for k in expected_keys}
            normalized = {}
            for key in expected_keys:
                entry = group_data.get(key, {})
                if isinstance(entry, dict):
                    severity = max(0, min(3, int(entry.get("severity", 2))))
                    evidence = str(entry.get("evidence", "No evidence provided.")).strip()
                    normalized[key] = {"severity": severity, "evidence": evidence or "No evidence provided."}
                else:
                    normalized[key] = {"severity": 2, "evidence": "No analysis available."}
            return normalized

        overshoot_keys = [
            "verbosity_risk", "hallucination_risk", "caveat_risk",
            "tangent_risk", "enumeration_risk",
        ]
        undershoot_keys = [
            "completeness_risk", "depth_risk", "schema_risk",
            "edge_case_risk", "reasoning_risk",
        ]

        overshoot_risks = normalize_risk_group(
            raw_analysis.get("overshoot_risks"), overshoot_keys,
        )
        undershoot_risks = normalize_risk_group(
            raw_analysis.get("undershoot_risks"), undershoot_keys,
        )

        # Compute aggregate scores (sum of severities, scaled to 0–15)
        overshoot_total = sum(r["severity"] for r in overshoot_risks.values())
        undershoot_total = sum(r["severity"] for r in undershoot_risks.values())

        dominant = raw_analysis.get("dominant_failure_mode", "balanced")
        if dominant not in ("overshoot", "undershoot", "balanced"):
            if overshoot_total > undershoot_total + 3:
                dominant = "overshoot"
            elif undershoot_total > overshoot_total + 3:
                dominant = "undershoot"
            else:
                dominant = "balanced"

        summary = str(raw_analysis.get("summary", "Failure mode analysis completed.")).strip()
        if not summary:
            summary = "Failure mode analysis completed."

        return {
            "overshoot_risks": overshoot_risks,
            "undershoot_risks": undershoot_risks,
            "overall_overshoot_score": overshoot_total,
            "overall_undershoot_score": undershoot_total,
            "dominant_failure_mode": dominant,
            "summary": summary,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Step 2: Guard Selection from Library
    # ──────────────────────────────────────────────────────────────────────

    def _select_guards_for_tier(
        self,
        risk_analysis: dict[str, Any],
        activation_threshold: int,
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """
        Select guards from the template library based on risk severity scores.

        For each risk dimension whose severity >= activation_threshold,
        the corresponding guard template is activated.

        Args:
            risk_analysis: Normalized risk analysis from Step 1.
            activation_threshold: Minimum severity to activate a guard.

        Returns:
            Tuple of:
              - overshoot_guard_texts: List of injection text strings for overshoot guards
              - undershoot_guard_texts: List of injection text strings for undershoot guards
              - overshoot_guard_labels: Display labels for the variant metadata
              - undershoot_guard_labels: Display labels for the variant metadata
        """
        overshoot_risk_to_guard = {
            "verbosity_risk": "length_calibration",
            "hallucination_risk": "anti_hallucination",
            "caveat_risk": "anti_caveat",
            "tangent_risk": "scope_lock",
            "enumeration_risk": "enumeration_cap",
        }
        undershoot_risk_to_guard = {
            "completeness_risk": "exhaustiveness",
            "depth_risk": "depth_floor",
            "schema_risk": "schema_completeness",
            "edge_case_risk": "edge_case_coverage",
            "reasoning_risk": "reasoning_depth",
        }

        overshoot_guard_texts: list[str] = []
        overshoot_guard_labels: list[str] = []
        undershoot_guard_texts: list[str] = []
        undershoot_guard_labels: list[str] = []

        # Select overshoot guards
        overshoot_risks = risk_analysis.get("overshoot_risks", {})
        for risk_key, guard_key in overshoot_risk_to_guard.items():
            risk_data = overshoot_risks.get(risk_key, {})
            severity = risk_data.get("severity", 0)
            if severity >= activation_threshold:
                label, text = _OVERSHOOT_GUARD_TEMPLATES[guard_key]
                overshoot_guard_texts.append(text)
                overshoot_guard_labels.append(label)

        # Select undershoot guards
        undershoot_risks = risk_analysis.get("undershoot_risks", {})
        for risk_key, guard_key in undershoot_risk_to_guard.items():
            risk_data = undershoot_risks.get(risk_key, {})
            severity = risk_data.get("severity", 0)
            if severity >= activation_threshold:
                label, text = _UNDERSHOOT_GUARD_TEMPLATES[guard_key]
                undershoot_guard_texts.append(text)
                undershoot_guard_labels.append(label)

        return overshoot_guard_texts, undershoot_guard_texts, overshoot_guard_labels, undershoot_guard_labels

    # ──────────────────────────────────────────────────────────────────────
    # Step 3: Structural Rewrite of the Raw Prompt
    # ──────────────────────────────────────────────────────────────────────

    async def _rewrite_prompt_with_structure(
        self,
        raw_prompt: str,
        risk_analysis: dict[str, Any],
        provider: str,
        model_id: str,
        api_key: str,
    ) -> dict[str, Any]:
        """
        Structurally rewrite the raw prompt to add clear task/scope/format
        sections that inherently reduce both overshoot and undershoot risk.

        Args:
            raw_prompt: The enriched raw prompt.
            risk_analysis: The failure mode analysis from Step 1.
            provider: LLM provider string.
            model_id: Target model ID.
            api_key: API key.

        Returns:
            Dict with task_statement, scope_boundaries, original_context,
            output_format, and constraints.
        """
        rewrite_prompt = _STRUCTURAL_REWRITE_PROMPT.format(
            raw_prompt=raw_prompt,
            failure_analysis=json.dumps(
                {
                    "dominant_failure_mode": risk_analysis["dominant_failure_mode"],
                    "overall_overshoot_score": risk_analysis["overall_overshoot_score"],
                    "overall_undershoot_score": risk_analysis["overall_undershoot_score"],
                    "summary": risk_analysis["summary"],
                },
                indent=2,
            ),
        )

        async with LLMClient(api_key=api_key) as llm_client:
            response_text = await llm_client.call(
                provider=provider,
                prompt=rewrite_prompt,
                max_tokens=MAX_TOKENS_COMPONENT_EXTRACTION,
                model=model_id,
                system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
            )

        extracted = extract_json_from_llm_response(response_text)

        return {
            "task_statement": self._safe_string(
                extracted.get("task_statement"), "Complete the requested task."
            ),
            "scope_boundaries": self._safe_string(
                extracted.get("scope_boundaries"), "Respond within the scope of the provided context."
            ),
            "original_context": self._safe_string(
                extracted.get("original_context"), raw_prompt
            ),
            "output_format": self._safe_string(
                extracted.get("output_format"), "Respond in clear, structured prose."
            ),
            "constraints": self._safe_constraints(extracted.get("constraints")),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Step 4: Variant Assembly
    # ──────────────────────────────────────────────────────────────────────

    def _assemble_variant_prompt(
        self,
        rewrite: dict[str, Any],
        overshoot_guards: list[str],
        undershoot_guards: list[str],
        variant_tier: str,
    ) -> str:
        """
        Assemble a complete system prompt from the structural rewrite
        and the selected guard templates.

        Args:
            rewrite: The structural rewrite output from Step 3.
            overshoot_guards: Selected overshoot guard injection texts.
            undershoot_guards: Selected undershoot guard injection texts.
            variant_tier: "conservative", "structured", or "advanced".
        """
        task_statement = rewrite["task_statement"]
        scope_boundaries = rewrite["scope_boundaries"]
        original_context = rewrite["original_context"]
        output_format = rewrite["output_format"]
        constraints = rewrite["constraints"]

        if variant_tier == "conservative":
            # Light structure + overshoot guards only
            parts = [
                f"TASK:\n{task_statement}",
                f"\nCONTEXT:\n{original_context}",
                f"\nSCOPE:\n{scope_boundaries}",
                f"\nOUTPUT FORMAT:\n{output_format}",
            ]
            if constraints:
                parts.append(f"\nCONSTRAINTS:\n{format_list_as_bullet_points(constraints)}")
            if overshoot_guards:
                parts.append("\n--- GENERATION GUARDRAILS ---")
                for guard in overshoot_guards:
                    parts.append(f"\n{guard}")
            return "\n".join(parts)

        elif variant_tier == "structured":
            # Full structure + balanced dual guards
            parts = [
                f"### TASK\n{task_statement}",
                f"\n### CONTEXT\n{original_context}",
                f"\n### SCOPE BOUNDARIES\n{scope_boundaries}",
                f"\n### OUTPUT FORMAT\n{output_format}",
                f"\n### CONSTRAINTS\n{format_list_as_bullet_points(constraints)}",
            ]
            if overshoot_guards or undershoot_guards:
                parts.append("\n### GENERATION GUARDRAILS")
                if overshoot_guards:
                    parts.append("\n**Overshoot Prevention (do not generate excess):**")
                    for guard in overshoot_guards:
                        parts.append(f"\n{guard}")
                if undershoot_guards:
                    parts.append("\n**Undershoot Prevention (do not omit required content):**")
                    for guard in undershoot_guards:
                        parts.append(f"\n{guard}")
            return "\n".join(parts)

        else:  # advanced
            # High-contrast borders + aggressive dual guards + echo
            parts = [
                "=" * 40,
                "TASK MANDATE",
                "=" * 40,
                task_statement,
                "",
                "=" * 40,
                "CONTEXT GROUNDING",
                "=" * 40,
                original_context,
                "",
                "=" * 40,
                "SCOPE BOUNDARIES (HARD LIMITS)",
                "=" * 40,
                scope_boundaries,
                "",
                "=" * 40,
                "OUTPUT FORMAT SPECIFICATION",
                "=" * 40,
                output_format,
                "",
                "=" * 40,
                "HARD CONSTRAINTS",
                "=" * 40,
                format_list_as_bullet_points(constraints),
                "- Do NOT hallucinate facts outside the provided context.",
                "- Do NOT append conversational preamble or postamble.",
                "- Validate all output against the schema before responding.",
            ]

            if overshoot_guards:
                parts.extend([
                    "",
                    "=" * 40,
                    "⚠ OVERSHOOT PREVENTION (CRITICAL)",
                    "=" * 40,
                ])
                for guard in overshoot_guards:
                    parts.append(guard)

            if undershoot_guards:
                parts.extend([
                    "",
                    "=" * 40,
                    "⚠ UNDERSHOOT PREVENTION (CRITICAL)",
                    "=" * 40,
                ])
                for guard in undershoot_guards:
                    parts.append(guard)

            return "\n".join(parts)

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
        Generate 3 failure-mode-calibrated variants with escalating guard intensity.

        Workflow:
            Step 1: Enrich prompt with gap-interview answers.
            Step 2: LLM sub-call to analyse 10 failure mode risk dimensions.
            Step 3: LLM sub-call to structurally rewrite the prompt.
            Step 4: Python-side guard selection at 3 intensity tiers.
            Step 5: Assemble 3 variants and apply enhancements.
            Step 6: Quality gate and return.
        """
        logger.info("Executing Overshoot/Undershoot failure mode prevention optimization.")

        # Step 1: Enrich prompt
        enriched_prompt = integrate_gap_interview_answers_into_prompt(
            raw_prompt=request.raw_prompt,
            gap_interview_answers=request.answers,
            gap_analysis_data=request.gap_data,
        )

        # Step 2: Failure mode risk analysis
        risk_analysis = await self._analyse_failure_mode_risks(
            raw_prompt=enriched_prompt,
            provider=request.provider,
            model_id=request.model_id,
            api_key=request.api_key,
        )

        overshoot_score = risk_analysis["overall_overshoot_score"]
        undershoot_score = risk_analysis["overall_undershoot_score"]
        dominant_mode = risk_analysis["dominant_failure_mode"]
        analysis_summary = risk_analysis["summary"]

        logger.info(
            "Failure mode analysis complete. overshoot=%d, undershoot=%d, dominant=%s",
            overshoot_score,
            undershoot_score,
            dominant_mode,
        )

        # Step 3: Structural rewrite
        rewrite = await self._rewrite_prompt_with_structure(
            raw_prompt=enriched_prompt,
            risk_analysis=risk_analysis,
            provider=request.provider,
            model_id=request.model_id,
            api_key=request.api_key,
        )

        # Step 4: Guard selection at 3 tiers
        cons_os_guards, cons_us_guards, cons_os_labels, cons_us_labels = (
            self._select_guards_for_tier(risk_analysis, _GUARD_ACTIVATION_THRESHOLD_CONSERVATIVE)
        )
        struct_os_guards, struct_us_guards, struct_os_labels, struct_us_labels = (
            self._select_guards_for_tier(risk_analysis, _GUARD_ACTIVATION_THRESHOLD_STRUCTURED)
        )
        adv_os_guards, adv_us_guards, adv_os_labels, adv_us_labels = (
            self._select_guards_for_tier(risk_analysis, _GUARD_ACTIVATION_THRESHOLD_ADVANCED)
        )

        # Step 5: Assemble 3 variants
        variant_1_system_prompt = self._assemble_variant_prompt(
            rewrite, cons_os_guards, cons_us_guards, "conservative",
        )
        variant_2_system_prompt = self._assemble_variant_prompt(
            rewrite, struct_os_guards, struct_us_guards, "structured",
        )
        variant_3_system_prompt = self._assemble_variant_prompt(
            rewrite, adv_os_guards, adv_us_guards, "advanced",
        )

        # Apply RAL-Writer on Structured and Advanced variants to echo critical guards
        if rewrite["constraints"]:
            variant_2_system_prompt = apply_ral_writer_constraint_restatement(
                system_prompt=variant_2_system_prompt,
                critical_constraints_to_echo=rewrite["constraints"][:3],
                provider=request.provider,
            )
            variant_3_system_prompt = apply_ral_writer_constraint_restatement(
                system_prompt=variant_3_system_prompt,
                critical_constraints_to_echo=rewrite["constraints"],
                provider=request.provider,
            )

        # Input variables injection
        variant_1_system_prompt = inject_input_variables_block(
            variant_1_system_prompt, request.input_variables, request.provider,
        )
        variant_2_system_prompt = inject_input_variables_block(
            variant_2_system_prompt, request.input_variables, request.provider,
        )
        variant_3_system_prompt = inject_input_variables_block(
            variant_3_system_prompt, request.input_variables, request.provider,
        )

        # Prefill suggestion for Anthropic Advanced variant
        advanced_prefill = generate_claude_prefill_suggestion(
            request.task_type, request.provider,
        )

        # Build total guard counts for metadata
        cons_total_guards = len(cons_os_labels) + len(cons_us_labels)
        struct_total_guards = len(struct_os_labels) + len(struct_us_labels)
        adv_total_guards = len(adv_os_labels) + len(adv_us_labels)

        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy=(
                    f"Overshoot-only guard injection ({len(cons_os_labels)} guards). "
                    f"Dominant mode: {dominant_mode}."
                ),
                system_prompt=variant_1_system_prompt.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(variant_1_system_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=70, context=65, role=50, tone=55, execution=70),
                strengths=[
                    "Minimal prompt inflation",
                    "Targets most critical overshoot risks",
                ],
                best_for="Prompts where verbosity is the main concern",
                overshoot_guards=cons_os_labels,
                undershoot_guards=cons_us_labels,
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy=(
                    f"Balanced dual-mode guards ({len(struct_os_labels)} overshoot + "
                    f"{len(struct_us_labels)} undershoot). Dominant mode: {dominant_mode}."
                ),
                system_prompt=variant_2_system_prompt.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(variant_2_system_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=80, context=75, role=60, tone=65, execution=80),
                strengths=[
                    "Balanced protection against both failure modes",
                    "Moderate + critical guards activated",
                    "RAL-Writer constraint echo",
                ],
                best_for="Production prompts needing calibrated scope and depth control",
                overshoot_guards=struct_os_labels,
                undershoot_guards=struct_us_labels,
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy=(
                    f"Aggressive dual-mode protection ({len(adv_os_labels)} overshoot + "
                    f"{len(adv_us_labels)} undershoot). Full guard library activation."
                ),
                system_prompt=variant_3_system_prompt.strip(),
                user_prompt="[Insert request data here]",
                prefill_suggestion=advanced_prefill,
                token_estimate=len(variant_3_system_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=90, context=85, role=70, tone=75, execution=90),
                strengths=[
                    "Maximum dual-mode failure prevention",
                    "All applicable guards activated",
                    "High-contrast structural borders",
                    "RAL-Writer constraint restatement",
                ],
                best_for="High-stakes prompts where both over- and under-generation are dangerous",
                overshoot_guards=adv_os_labels,
                undershoot_guards=adv_us_labels,
            ),
        ]

        # Build analysis
        detected_issues: list[str] = [analysis_summary]
        if overshoot_score > 8:
            detected_issues.append(
                f"High overshoot risk detected (score {overshoot_score}/15). "
                "Prompt lacks scope boundaries and length calibration."
            )
        if undershoot_score > 8:
            detected_issues.append(
                f"High undershoot risk detected (score {undershoot_score}/15). "
                "Prompt lacks exhaustiveness requirements and depth anchors."
            )

        model_notes = (
            f"Failure mode analysis: overshoot={overshoot_score}/15, "
            f"undershoot={undershoot_score}/15, dominant={dominant_mode}. "
            f"Guards activated: {cons_total_guards} (conservative), "
            f"{struct_total_guards} (structured), {adv_total_guards} (advanced)."
        )
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        analysis = OptimizationAnalysis(
            detected_issues=detected_issues,
            model_notes=model_notes,
            framework_applied="overshoot_undershoot",
            coverage_delta=compute_coverage_delta_description(request.gap_data, 80),
            auto_selected_framework="overshoot_undershoot" if auto_reason else None,
            auto_reason=auto_reason,
        )

        response = OptimizationResponse(
            analysis=analysis,
            techniques_applied=[
                "Failure Mode Risk Analysis",
                "Guard Library Selection",
                "Overshoot Prevention",
                "Undershoot Prevention",
                "Structural Rewrite",
            ],
            variants=variants,
        )

        # Step 6: Quality gate
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
        """Extract a string from a potentially non-string value."""
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (dict, list)):
            dumped = json.dumps(value, indent=2, ensure_ascii=True)
            return dumped if dumped.strip() else default
        return default

    def _safe_constraints(self, value: Any) -> list[str]:
        """Normalize constraints into a non-empty list of string rules."""
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [
                line.strip().lstrip("-").strip()
                for line in value.splitlines()
                if line.strip().lstrip("-").strip()
            ]
        return []

    def _structured_response_format_for_provider(
        self,
        provider: str,
        *,
        schema: dict[str, Any],
        name: str,
    ) -> Optional[dict[str, Any]]:
        """Return provider-compatible structured response hints when available."""
        if provider == "openai":
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": name,
                    "strict": True,
                    "schema": schema,
                },
            }
        if provider == "google":
            return {
                "type": "json_schema",
                "json_schema": {"schema": schema},
            }
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Standalone Test Entry Point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    import os
    import sys
    from pathlib import Path
    from dotenv import load_dotenv

    backend_directory = Path(__file__).resolve().parent.parent.parent.parent.parent
    env_file_path = backend_directory / ".env"
    load_dotenv(env_file_path)

    # A healthcare prompt with both overshoot and undershoot risks
    MIXED_RISK_TEST_PROMPT = """\
    Look at the patient's chart and tell me what you think. They have some
    heart problems and are on several medications. Give me your assessment
    and any recommendations you might have.
    """

    async def test_overshoot_undershoot_optimizer():
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            print("ERROR: OPENAI_API_KEY not found in .env")
            sys.exit(1)

        request = OptimizationRequest(
            raw_prompt=MIXED_RISK_TEST_PROMPT,
            provider="openai",
            model_id="gpt-4.1-nano",
            model_label="GPT-4.1 Nano",
            task_type="analysis",
            framework="overshoot_undershoot",
            is_reasoning_model=False,
            api_key=api_key,
        )

        optimizer = OvershootUndershootOptimizer()
        print("=" * 80)
        print("TESTING: Overshoot/Undershoot Failure Mode Prevention Optimizer")
        print("=" * 80)

        try:
            result = await optimizer.generate_variants(request=request)
            print(f"\n✓ Framework applied: {result.analysis.framework_applied}")
            print(f"✓ Detected issues: {result.analysis.detected_issues}")
            print(f"✓ Techniques: {result.techniques_applied}")
            print(f"✓ Variants generated: {len(result.variants)}")
            for variant in result.variants:
                print(f"\n── Variant {variant.id}: {variant.name} ──")
                print(f"   Strategy: {variant.strategy}")
                print(f"   Token estimate: {variant.token_estimate}")
                print(f"   Overshoot guards: {variant.overshoot_guards}")
                print(f"   Undershoot guards: {variant.undershoot_guards}")
                preview_length = min(300, len(variant.system_prompt))
                print(f"   System prompt preview: {variant.system_prompt[:preview_length]}...")
            print("\n✓ Overshoot/Undershoot test PASSED")
        except Exception as error:
            print(f"\n✗ Overshoot/Undershoot test FAILED: {error}")
            import traceback
            traceback.print_exc()

    asyncio.run(test_overshoot_undershoot_optimizer())
