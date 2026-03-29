"""
TCRTE Coverage-First Optimizer Strategy

Implements the TCRTE gap-filling optimization from APOST_v4_Documentation.md §3
and §4.8 Priority 5. This optimizer is specifically designed for prompts that
score below 50% on the TCRTE coverage audit — meaning the prompt is so
underspecified that structural gaps must be filled BEFORE any stylistic framework
can be effective.

ALGORITHM WORKFLOW:
═══════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────────────┐
  │   TCRTE Gap Resolver         │
  └──────────────┬───────────────┘
                 │
                 ▼
  ┌──────────────────────────────┐  Step 1: DIMENSION TRIAGE
  │  Dimension Triage Engine     │  Read gap_data.tcrte scores. Classify each
  │                              │  dimension into:
  │                              │    MISSING (score < 35) → must be filled
  │                              │    WEAK    (score < 70) → should be enhanced
  │                              │    GOOD    (score ≥ 70) → preserve as-is
  └──────────────┬───────────────┘
                 │
                 ▼
  ┌──────────────────────────────┐  Step 2: ANSWER INTEGRATION
  │  Gap Answer Merger           │  For each MISSING/WEAK dimension, check if
  │                              │  the user provided answers in the gap interview.
  │                              │  If yes → use verbatim. If no → use LLM to
  └──────────────┬───────────────┘  generate a reasonable default.
                 │
                 ▼
  ┌──────────────────────────────┐  Step 3: DIMENSION FILLING via LLM
  │  TCRTE Section Constructor   │  Use LLM sub-call to rewrite the raw prompt
  │                              │  with explicit [TASK] [CONTEXT] [ROLE] [TONE]
  └──────────────┬───────────────┘  [EXECUTION] sections, each addressing its
                 │                  dimension score.
                 ▼
  ┌──────────────────────────────┐  Step 4: VARIANT ASSEMBLY (3 Variants)
  │  Variant Assembly            │  Conservative: Original + targeted insertions
  │                              │                for MISSING dimensions only
  │                              │  Structured:   Full 5-section TCRTE architecture
  └──────────────┬───────────────┘  Advanced:     Full TCRTE + guards + CoRe +
                 │                                RAL-Writer echo + prefill
                 ▼
  ┌──────────────────────────────┐  Step 5: ENHANCEMENT APPLICATION
  │  Enhancement Injection       │  Apply CoRe, RAL-Writer, input variables,
  └──────────────────────────────┘  Claude prefill via shared utilities.

TESTING:
  Run this file directly to test with a healthcare example:
    cd d:\\Generative AI Portfolio Projects\\APOST\\backend
    python -m app.services.optimization.frameworks.tcrte_coverage_optimizer

REFERENCES:
  - APOST_v4_Documentation.md §3 (TCRTE Framework)
  - APOST_v4_Documentation.md §4.8 Priority 5 (Auto-select → TCRTE when score < 50)
"""

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
from app.services.json_extractor import extract_json_from_llm_response
from app.services.optimization.base import BaseOptimizerStrategy
from app.services.optimization.optimizer_configuration import (
    MAX_TOKENS_TCRTE_DIMENSION_FILL,
    SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
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
# TCRTE Dimension Labels and Thresholds
# ──────────────────────────────────────────────────────────────────────────────

TCRTE_DIMENSION_NAMES = ["task", "context", "role", "tone", "execution"]

TCRTE_SCORE_THRESHOLD_MISSING = 35   # Below this → MISSING (must fill)
TCRTE_SCORE_THRESHOLD_WEAK = 70      # Below this → WEAK (should enhance)

# Human-readable labels for the 5 TCRTE dimensions
TCRTE_DIMENSION_DESCRIPTIONS = {
    "task": "Task clarity — what exactly the model should produce and how success is measured",
    "context": "Context grounding — domain, data sources, temporal scope",
    "role": "Role definition — expert persona, seniority, behavioural calibration",
    "tone": "Tone specification — formality register, audience, hedging rules",
    "execution": "Execution constraints — output format, length limits, prohibited content",
}


# ──────────────────────────────────────────────────────────────────────────────
# LLM Prompt Template for TCRTE Dimension Filling
# ──────────────────────────────────────────────────────────────────────────────

_TCRTE_DIMENSION_FILL_PROMPT = """
You are an expert prompt architect. The user's raw prompt is UNDERSPECIFIED
and needs structural repair across the 5 TCRTE dimensions.

Here is the raw prompt:
<raw_prompt>
{raw_prompt}
</raw_prompt>

{dimension_repair_instructions}

Rewrite the prompt with explicit sections for ALL 5 TCRTE dimensions.
For dimensions marked as MISSING or WEAK, you MUST generate substantial content.
For dimensions marked as GOOD, preserve the original content.

{user_provided_answers_block}

Return ONLY valid JSON matching this schema:
{{
  "task_section": "Explicit task definition with measurable outputs and success criteria",
  "context_section": "Domain, data sources, temporal scope, grounding information",
  "role_section": "Expert persona with seniority and behavioural calibration",
  "tone_section": "Formality register, audience type, hedging rules",
  "execution_section": "Output format, length constraints, prohibited content",
  "constraints": ["list of identified constraints"],
  "critical_context_for_core": "The single most important context element"
}}
"""


class TcrteCoverageOptimizer(BaseOptimizerStrategy):
    """
    Deep implementation of the TCRTE Coverage-First optimization framework.

    This optimizer is designed for  prompts with overall_score < 50 where
    structural gaps across the 5 TCRTE dimensions must be filled BEFORE
    any stylistic framework can be effective. It reads gap_data as its
    primary input and uses gap-interview answers to enrich the prompt.
    """

    # ──────────────────────────────────────────────────────────────────────
    # Step 1: Dimension Triage
    # ──────────────────────────────────────────────────────────────────────

    def _classify_dimensions_by_score(
        self,
        gap_analysis_data: Optional[dict],
    ) -> dict[str, str]:
        """
        Classify each TCRTE dimension as MISSING, WEAK, or GOOD based on scores.

        Args:
            gap_analysis_data: The gap analysis response dict containing tcrte scores.

        Returns:
            Dict mapping dimension name → status ("missing", "weak", "good").
        """
        classifications: dict[str, str] = {}

        for dimension_name in TCRTE_DIMENSION_NAMES:
            score = 0  # Default to 0 (MISSING) if no data available

            if gap_analysis_data and "tcrte" in gap_analysis_data:
                tcrte_data = gap_analysis_data["tcrte"]
                if isinstance(tcrte_data, dict) and dimension_name in tcrte_data:
                    dimension_data = tcrte_data[dimension_name]
                    if isinstance(dimension_data, dict):
                        score = int(dimension_data.get("score", 0))
                    elif isinstance(dimension_data, (int, float)):
                        score = int(dimension_data)

            if score < TCRTE_SCORE_THRESHOLD_MISSING:
                classifications[dimension_name] = "missing"
            elif score < TCRTE_SCORE_THRESHOLD_WEAK:
                classifications[dimension_name] = "weak"
            else:
                classifications[dimension_name] = "good"

        logger.info(
            "TCRTE dimension triage: %s",
            {name: status.upper() for name, status in classifications.items()},
        )
        return classifications

    # ──────────────────────────────────────────────────────────────────────
    # Step 2: Build Repair Instructions from Classifications
    # ──────────────────────────────────────────────────────────────────────

    def _build_dimension_repair_instructions(
        self,
        dimension_classifications: dict[str, str],
    ) -> str:
        """
        Build the dimension-specific repair instructions for the LLM prompt.

        Each dimension gets a line indicating its status and what action is needed.

        Args:
            dimension_classifications: Output from _classify_dimensions_by_score.

        Returns:
            Multi-line instruction string for each dimension.
        """
        instruction_lines: list[str] = ["DIMENSION STATUS AND REQUIRED ACTIONS:"]

        for dimension_name in TCRTE_DIMENSION_NAMES:
            status = dimension_classifications.get(dimension_name, "missing")
            description = TCRTE_DIMENSION_DESCRIPTIONS[dimension_name]

            if status == "missing":
                instruction_lines.append(
                    f"  [{dimension_name.upper()}] → MISSING (score < 35). "
                    f"You MUST generate substantial content for: {description}"
                )
            elif status == "weak":
                instruction_lines.append(
                    f"  [{dimension_name.upper()}] → WEAK (score 35-69). "
                    f"Enhance and strengthen: {description}"
                )
            else:
                instruction_lines.append(
                    f"  [{dimension_name.upper()}] → GOOD (score ≥ 70). "
                    f"Preserve existing content for: {description}"
                )

        return "\n".join(instruction_lines)

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
        Generate 3 TCRTE coverage-repair variants.

        Workflow:
            Step 1: Classify dimensions by score (MISSING/WEAK/GOOD).
            Step 2: Build repair instructions and integrate gap answers.
            Step 3: Use LLM to fill/enhance all 5 TCRTE sections.
            Step 4: Assemble 3 variants with escalating completeness.
            Step 5: Apply enhancements (CoRe, RAL-Writer, Prefill, variables).
            Step 6: Return structured OptimizationResponse.
        """
        logger.info("Executing TCRTE Coverage-First optimization (gap-filling mode).")

        # Step 1: Dimension triage
        dimension_classifications = self._classify_dimensions_by_score(request.gap_data)

        # Step 2: Enrich prompt with gap-interview answers
        enriched_prompt = integrate_gap_interview_answers_into_prompt(
            raw_prompt=request.raw_prompt,
            gap_interview_answers=request.answers,
            gap_analysis_data=request.gap_data,
        )

        # Build repair instructions
        repair_instructions = self._build_dimension_repair_instructions(dimension_classifications)

        # Build user answers block for the LLM
        user_answers_block = ""
        if request.answers:
            answer_lines = ["\nUSER-PROVIDED ANSWERS (use these to fill gaps):"]
            for question_text, answer_value in request.answers.items():
                if answer_value and answer_value.strip():
                    answer_lines.append(f"  Q: {question_text}")
                    answer_lines.append(f"  A: {answer_value}")
            user_answers_block = "\n".join(answer_lines)

        # Step 3: LLM sub-call to generate the 5 TCRTE sections
        fill_prompt = _TCRTE_DIMENSION_FILL_PROMPT.format(
            raw_prompt=enriched_prompt,
            dimension_repair_instructions=repair_instructions,
            user_provided_answers_block=user_answers_block,
        )

        async with LLMClient(api_key=request.api_key) as llm_client:
            fill_response_text = await llm_client.call(
                provider=request.provider,
                prompt=fill_prompt,
                max_tokens=MAX_TOKENS_TCRTE_DIMENSION_FILL,
                model=request.model_id,
                system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
            )

        filled_sections = extract_json_from_llm_response(fill_response_text)
        task_section = filled_sections.get("task_section", "Complete the requested task.")
        context_section = filled_sections.get("context_section", "General domain.")
        role_section = filled_sections.get("role_section", "You are an AI assistant.")
        tone_section = filled_sections.get("tone_section", "Professional and clear.")
        execution_section = filled_sections.get("execution_section", "Respond in clear prose.")
        constraints = filled_sections.get("constraints", [])
        critical_context = filled_sections.get("critical_context_for_core", "")

        # Count how many dimensions were repaired
        missing_count = sum(1 for status in dimension_classifications.values() if status == "missing")
        weak_count = sum(1 for status in dimension_classifications.values() if status == "weak")

        # Step 4: Assemble 3 variants

        # ── Variant 1: Conservative — targeted insertions for MISSING dims only ──
        variant_1_parts: list[str] = [enriched_prompt]
        if dimension_classifications.get("task") == "missing":
            variant_1_parts.append(f"\n[TASK — Added] {task_section}")
        if dimension_classifications.get("context") == "missing":
            variant_1_parts.append(f"\n[CONTEXT — Added] {context_section}")
        if dimension_classifications.get("role") == "missing":
            variant_1_parts.append(f"\n[ROLE — Added] {role_section}")
        if dimension_classifications.get("execution") == "missing":
            variant_1_parts.append(f"\n[OUTPUT FORMAT — Added] {execution_section}")
        variant_1_system_prompt = "\n".join(variant_1_parts)

        # ── Variant 2: Structured — full 5-section TCRTE architecture ──
        variant_2_system_prompt = f"""### ROLE
{role_section}

### TASK
{task_section}

### CONTEXT
{context_section}

### TONE
{tone_section}

### EXECUTION
{execution_section}

### CONSTRAINTS
{format_list_as_bullet_points(constraints)}"""

        # ── Variant 3: Advanced — full TCRTE + all guards ──
        variant_3_system_prompt = f"""=================
[R] ROLE DEFINITION
=================
{role_section}
You must strictly maintain this persona for the duration of the request.

=================
[T] TASK MANDATE
=================
{task_section}

=================
[C] CONTEXT GROUNDING
=================
{context_section}

=================
[T] TONE SPECIFICATION
=================
{tone_section}

=================
[E] EXECUTION CONSTRAINTS
=================
{execution_section}

=================
HARD CONSTRAINTS
=================
{format_list_as_bullet_points(constraints)}
- Do NOT hallucinate facts outside the provided context.
- Do NOT append conversational preamble or postamble.
- Validate all output against the execution schema before responding."""

        # Step 5: Apply enhancements

        # CoRe injection on Advanced variant
        if core_k > 2 and critical_context:
            variant_3_system_prompt = inject_context_repetition_at_attention_positions(
                prompt_text=variant_3_system_prompt,
                critical_context_to_repeat=critical_context,
                repetition_count_k=core_k,
            )

        # RAL-Writer on Structured and Advanced
        if constraints:
            variant_2_system_prompt = apply_ral_writer_constraint_restatement(
                system_prompt=variant_2_system_prompt,
                critical_constraints_to_echo=constraints[:3],
                provider=request.provider,
            )
            variant_3_system_prompt = apply_ral_writer_constraint_restatement(
                system_prompt=variant_3_system_prompt,
                critical_constraints_to_echo=constraints,
                provider=request.provider,
            )

        # Input variables injection
        variant_1_system_prompt = inject_input_variables_block(variant_1_system_prompt, request.input_variables, request.provider)
        variant_2_system_prompt = inject_input_variables_block(variant_2_system_prompt, request.input_variables, request.provider)
        variant_3_system_prompt = inject_input_variables_block(variant_3_system_prompt, request.input_variables, request.provider)

        # Prefill
        advanced_prefill = generate_claude_prefill_suggestion(request.task_type, request.provider)

        # Step 6: Build response
        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy=f"Targeted insertion of {missing_count} MISSING TCRTE dimensions into original prompt.",
                system_prompt=variant_1_system_prompt.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(variant_1_system_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=60, context=55, role=50, tone=45, execution=60),
                strengths=["Minimal disruption", "Preserves original structure"],
                best_for="Quick repairs for slightly underspecified prompts",
                overshoot_guards=[],
                undershoot_guards=[],
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy=f"Full 5-section TCRTE architecture filling {missing_count} MISSING + {weak_count} WEAK dimensions.",
                system_prompt=variant_2_system_prompt.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(variant_2_system_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=80, context=75, role=80, tone=70, execution=80),
                strengths=["Complete TCRTE coverage", "Structured sections", "RAL-Writer restatement"],
                best_for="Standard production prompts needing structural completeness",
                overshoot_guards=["Defined section boundaries"],
                undershoot_guards=[],
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy=f"Full TCRTE with high-contrast borders, CoRe injection (k={core_k}), and all guards.",
                system_prompt=variant_3_system_prompt.strip(),
                user_prompt="[Insert request data here]",
                prefill_suggestion=advanced_prefill,
                token_estimate=len(variant_3_system_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=95, context=90, role=90, tone=85, execution=95),
                strengths=["Maximum TCRTE coverage", "Anti-hallucination guards", "CoRe injection", "RAL-Writer"],
                best_for="Severely underspecified prompts requiring comprehensive repair",
                overshoot_guards=["No preamble", "No hallucination", "Schema validation"],
                undershoot_guards=["All 5 dimensions enforced", "Constraint echo in recency zone"],
            ),
        ]

        model_notes = f"TCRTE Coverage repair: {missing_count} MISSING + {weak_count} WEAK dimensions filled."
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        analysis = OptimizationAnalysis(
            detected_issues=[
                f"{missing_count} TCRTE dimensions were MISSING (score < 35).",
                f"{weak_count} TCRTE dimensions were WEAK (score 35-69).",
                "Structural gaps must be filled before stylistic refinement.",
            ],
            model_notes=model_notes,
            framework_applied="tcrte",
            coverage_delta=compute_coverage_delta_description(request.gap_data, 85),
        )

        response = OptimizationResponse(
            analysis=analysis,
            techniques_applied=["TCRTE Gap Fill", "Dimension Triage", "Answer Integration"],
            variants=variants,
        )

        # Quality gate: critique each variant, enhance weak ones, measure real scores
        response = await self._refine_variants_with_quality_critique(
            response=response,
            raw_prompt=request.raw_prompt,
            task_type=request.task_type,
            api_key=request.api_key,
            quality_gate_mode=request.quality_gate_mode,
            target_model=request.model_id,
        )

        return response


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

    # A deliberately underspecified healthcare prompt (low TCRTE scores)
    UNDERSPECIFIED_HEALTHCARE_PROMPT = """
    Analyze the patient data and tell me if something is wrong.
    """

    # Simulated gap analysis data with low scores
    SIMULATED_GAP_DATA = {
        "tcrte": {
            "task": {"score": 30, "status": "missing", "note": "No measurable output defined"},
            "context": {"score": 20, "status": "missing", "note": "No domain specified"},
            "role": {"score": 0, "status": "missing", "note": "No role defined"},
            "tone": {"score": 0, "status": "missing", "note": "No tone specified"},
            "execution": {"score": 25, "status": "missing", "note": "No output format defined"},
        },
        "overall_score": 15,
    }

    SIMULATED_GAP_ANSWERS = {
        "What domain is this analysis for?": "Cardiology — cardiac catheterisation reporting",
        "What specific output format do you need?": "JSON with risk_level, findings, and recommendations arrays",
        "Who is the intended audience?": "Attending cardiologist reviewing cath lab results",
    }

    async def test_tcrte_coverage_optimizer():
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            print("ERROR: OPENAI_API_KEY not found in .env")
            sys.exit(1)

        request = OptimizationRequest(
            raw_prompt=UNDERSPECIFIED_HEALTHCARE_PROMPT,
            provider="openai",
            model_id="gpt-4.1-nano",
            model_label="GPT-4.1 Nano",
            task_type="analysis",
            framework="tcrte",
            is_reasoning_model=False,
            gap_data=SIMULATED_GAP_DATA,
            answers=SIMULATED_GAP_ANSWERS,
            api_key=api_key,
        )

        optimizer = TcrteCoverageOptimizer()
        print("=" * 80)
        print("TESTING: TCRTE Coverage-First Optimizer (Healthcare — underspecified)")
        print("=" * 80)

        try:
            result = await optimizer.generate_variants(request=request)
            print(f"\n✓ Framework applied: {result.analysis.framework_applied}")
            print(f"✓ Detected issues: {result.analysis.detected_issues}")
            print(f"✓ Variants generated: {len(result.variants)}")
            for variant in result.variants:
                print(f"\n── Variant {variant.id}: {variant.name} ──")
                print(f"   Strategy: {variant.strategy}")
                print(f"   Token estimate: {variant.token_estimate}")
                print(f"   System prompt preview: {variant.system_prompt[:300]}...")
            print("\n✓ TCRTE Coverage test PASSED")
        except Exception as error:
            print(f"\n✗ TCRTE Coverage test FAILED: {error}")
            import traceback
            traceback.print_exc()

    asyncio.run(test_tcrte_coverage_optimizer())

