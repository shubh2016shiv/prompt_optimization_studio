"""
Chain-of-Thought Ensemble Optimizer Strategy (Medprompt Pattern)

Implements the CoT Ensemble framework from APOST_v4_Documentation.md §4.4,
based on Microsoft Research's Medprompt paper. This framework injects kNN-retrieved
few-shot examples with reasoning traces and constructs multi-path ensemble
instructions to improve complex reasoning accuracy.

ALGORITHM WORKFLOW:
═══════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────────────┐
  │   CoT Ensemble Algorithm     │
  └──────────────┬───────────────┘
                 │
                 ▼
  ┌──────────────────────────────┐  Step 1: RECEIVE FEW-SHOT EXAMPLES
  │  Few-Shot Example Receiver   │  Accept kNN-retrieved examples from knn_retriever.py.
  │                              │  These are semantically similar prompt transformations
  └──────────────┬───────────────┘  retrieved via Gemini Embedding API cosine similarity.
                 │
                 ▼
  ┌──────────────────────────────┐  Step 2: SYNTHETIC EXAMPLE GENERATION (FALLBACK)
  │  Synthetic Example Generator │  If kNN examples are unavailable (no GOOGLE_API_KEY,
  │                              │  corpus not loaded), generate 2 synthetic few-shot
  └──────────────┬───────────────┘  examples with reasoning traces via LLM sub-call.
                 │
                 ▼
  ┌──────────────────────────────┐  Step 3: REASONING TRACE BUILDER
  │  CoT Trace Assembly          │  For each example, ensure a full step-by-step
  │                              │  reasoning trace accompanies the transformation.
  └──────────────┬───────────────┘  This demonstrates HOW to optimise, not just WHAT.
                 │
                 ▼
  ┌──────────────────────────────┐  Step 4: MULTI-PATH ENSEMBLE INSTRUCTION
  │  Ensemble Instruction Block  │  Construct the instruction that tells the model to
  │                              │  generate N independent reasoning paths, and then
  └──────────────┬───────────────┘  synthesise across paths for a robust answer.
                 │
                 ▼
  ┌──────────────────────────────┐  Step 5: VARIANT ASSEMBLY (3 Variants)
  │  Variant Assembly            │  Conservative: 1 example + single-path reasoning
  │                              │  Structured:   2 examples + dual-path + self-check
  └──────────────┬───────────────┘  Advanced:     3 examples + tri-path + ensemble
                 │                                + anti-hallucination + CoRe
                 ▼
  ┌──────────────────────────────┐  Step 6: ENHANCEMENT APPLICATION
  │  Enhancement Injection       │  Apply CoRe, RAL-Writer, Prefill, and gap-answer
  └──────────────────────────────┘  integration via shared enhancement utilities.

TESTING:
  Run this file directly to test with a healthcare example:
    cd d:\\Generative AI Portfolio Projects\\APOST\\backend
    python -m app.services.optimization.frameworks.cot_ensemble_optimizer

REFERENCES:
  - Microsoft Research Medprompt: "Can Generalist Foundation Models Outcompete
    Special-Purpose Tuning?" (Nori et al., 2023)
  - APOST_v4_Documentation.md §4.4
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
from app.services.json_extractor import extract_json_from_llm_response
from app.services.optimization.base import BaseOptimizerStrategy
from app.services.optimization.optimizer_configuration import (
    MAX_TOKENS_COMPONENT_EXTRACTION,
    MAX_TOKENS_SYNTHETIC_EXAMPLE_GENERATION,
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
# LLM Prompt Templates for Sub-Tasks
# ──────────────────────────────────────────────────────────────────────────────

_COT_COMPONENT_EXTRACTION_PROMPT = """
Analyze the following prompt and extract its core components for a Chain-of-Thought
ensemble optimization. Focus on identifying the reasoning requirements.

Extract:
1. "task": The primary objective that requires step-by-step reasoning.
2. "reasoning_steps": A list of the sequential reasoning steps needed to complete the task.
3. "constraints": Hard rules the model must follow.
4. "output_format": The expected output structure.
5. "critical_context": The most important context that must not be lost (for CoRe injection).

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY valid JSON matching this schema:
{{
  "task": "string",
  "reasoning_steps": ["step1", "step2", ...],
  "constraints": ["constraint1", ...],
  "output_format": "string",
  "critical_context": "string"
}}
"""

_SYNTHETIC_FEW_SHOT_GENERATION_PROMPT = """
Generate {count} few-shot examples for the following task type: "{task_type}".
Each example should be a prompt optimization transformation that includes:
1. An original raw prompt (before optimization)
2. The optimized system prompt (after optimization)
3. A step-by-step reasoning trace explaining each optimization decision

The examples should be realistic, domain-appropriate, and demonstrate clear
reasoning about WHY each change was made.

Return ONLY valid JSON:
{{
  "examples": [
    {{
      "raw_prompt": "the original prompt text",
      "optimized_system_prompt": "the improved prompt text",
      "reasoning_trace": "Step 1: ... Step 2: ... Step 3: ..."
    }}
  ]
}}
"""


class ChainOfThoughtEnsembleOptimizer(BaseOptimizerStrategy):
    """
    Deep implementation of the CoT Ensemble / Medprompt optimization framework.

    This optimizer constructs prompts that leverage few-shot examples with
    reasoning traces and multi-path ensemble instructions. It is the primary
    framework for complex reasoning and analysis tasks.

    Architecture:
        1. Receives kNN-retrieved examples (if available) from the knn_retriever
        2. Falls back to LLM-generated synthetic examples if kNN is unavailable
        3. Constructs multi-path reasoning instructions scaled by variant tier
        4. Applies all enhancement techniques (CoRe, RAL-Writer, Prefill)
    """

    # ──────────────────────────────────────────────────────────────────────
    # Step 1-2: Prepare Few-Shot Examples
    # ──────────────────────────────────────────────────────────────────────

    async def _ensure_few_shot_examples_are_available(
        self,
        few_shot_examples_from_knn: Optional[List[Any]],
        task_type: str,
        request: OptimizationRequest,
        desired_example_count: int = 2,
    ) -> List[dict]:
        """
        Ensure we have few-shot examples. If kNN examples are provided, use them.
        Otherwise, generate synthetic examples via an LLM sub-call.

        Args:
            few_shot_examples_from_knn: Examples from knn_retriever, or None.
            task_type: The task type for generating relevant examples.
            request: The optimisation request (for API key and provider).
            desired_example_count: How many synthetic examples to generate.

        Returns:
            A list of dicts, each with keys: raw_prompt, optimized_system_prompt,
            reasoning_trace.
        """
        # If kNN provided valid examples, use them directly
        if few_shot_examples_from_knn and len(few_shot_examples_from_knn) > 0:
            logger.info(
                "Using %d kNN-retrieved few-shot examples for CoT Ensemble.",
                len(few_shot_examples_from_knn),
            )
            return [
                ex if isinstance(ex, dict) else {"raw_prompt": str(ex), "optimized_system_prompt": "", "reasoning_trace": ""}
                for ex in few_shot_examples_from_knn
            ]

        # Fallback: generate synthetic examples via LLM
        logger.info(
            "kNN examples unavailable. Generating %d synthetic few-shot examples via LLM.",
            desired_example_count,
        )
        generation_prompt = _SYNTHETIC_FEW_SHOT_GENERATION_PROMPT.format(
            count=desired_example_count,
            task_type=task_type,
        )

        try:
            async with LLMClient(api_key=request.api_key) as llm_client:
                llm_response_text = await llm_client.call(
                    provider=request.provider,
                    prompt=generation_prompt,
                    max_tokens=MAX_TOKENS_SYNTHETIC_EXAMPLE_GENERATION,
                    model=request.model_id,
                    system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
                )
            parsed_response = extract_json_from_llm_response(llm_response_text)
            generated_examples = parsed_response.get("examples", [])
            logger.info("Successfully generated %d synthetic few-shot examples.", len(generated_examples))
            return generated_examples
        except Exception as generation_error:
            logger.warning(
                "Synthetic example generation failed (%s). Proceeding with zero examples.",
                generation_error,
            )
            return []

    # ──────────────────────────────────────────────────────────────────────
    # Step 3: Format Few-Shot Examples as Demonstration Blocks
    # ──────────────────────────────────────────────────────────────────────

    def _format_examples_as_demonstration_blocks(
        self,
        examples: List[dict],
        max_examples_to_include: int,
    ) -> str:
        """
        Format few-shot examples into a structured demonstration block.

        Each example is wrapped in numbered tags with raw→optimized→trace
        sections for maximum clarity to the target LLM.

        Args:
            examples: List of example dicts with raw_prompt, optimized_system_prompt,
                      reasoning_trace keys.
            max_examples_to_include: Cap on how many examples to include.

        Returns:
            Formatted string block of demonstrations.
        """
        if not examples:
            return ""

        selected_examples = examples[:max_examples_to_include]
        demonstration_parts: list[str] = []

        for example_index, example in enumerate(selected_examples, start=1):
            raw_text = example.get("raw_prompt", "N/A")
            optimised_text = example.get("optimized_system_prompt", "N/A")
            reasoning_text = example.get("reasoning_trace", "N/A")

            demonstration_parts.append(
                f"--- Example {example_index} ---\n"
                f"BEFORE (Raw Prompt):\n{raw_text}\n\n"
                f"AFTER (Optimized):\n{optimised_text}\n\n"
                f"REASONING TRACE:\n{reasoning_text}\n"
            )

        return "\n".join(demonstration_parts)

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
        Generate 3 CoT Ensemble variants with escalating ensemble depth.

        Workflow:
            Step 1: Integrate gap-interview answers into the raw prompt.
            Step 2: Extract prompt components via LLM sub-call.
            Step 3: Prepare few-shot examples (kNN or synthetic).
            Step 4: Assemble 3 variants with escalating complexity.
            Step 5: Apply enhancements (CoRe, RAL-Writer, Prefill, variables).
            Step 6: Return structured OptimizationResponse.
        """
        logger.info("Executing CoT Ensemble / Medprompt optimization.")

        # Step 1: Enrich prompt with gap-interview answers
        enriched_prompt = integrate_gap_interview_answers_into_prompt(
            raw_prompt=request.raw_prompt,
            gap_interview_answers=request.answers,
            gap_analysis_data=request.gap_data,
        )

        # Step 2: Extract components via LLM
        extraction_prompt = _COT_COMPONENT_EXTRACTION_PROMPT.format(raw_prompt=enriched_prompt)

        async with LLMClient(api_key=request.api_key) as llm_client:
            extraction_response_text = await llm_client.call(
                provider=request.provider,
                prompt=extraction_prompt,
                max_tokens=MAX_TOKENS_COMPONENT_EXTRACTION,
                model=request.model_id,
                system=SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
            )

        extracted_components = extract_json_from_llm_response(extraction_response_text)
        task_description = extracted_components.get("task", "Complete the requested analysis.")
        reasoning_steps = extracted_components.get("reasoning_steps", ["Analyze the input.", "Generate output."])
        constraints = extracted_components.get("constraints", [])
        output_format = extracted_components.get("output_format", "Natural language response.")
        critical_context = extracted_components.get("critical_context", "")

        # Step 3: Prepare few-shot examples
        all_examples = await self._ensure_few_shot_examples_are_available(
            few_shot_examples_from_knn=few_shot_examples,
            task_type=request.task_type,
            request=request,
        )

        # Step 4: Assemble 3 variants with escalating ensemble depth

        # ── Variant 1: Conservative — 1 example + single-path reasoning ──
        conservative_examples_block = self._format_examples_as_demonstration_blocks(
            all_examples, max_examples_to_include=1,
        )
        reasoning_steps_text = "\n".join(f"  {i}. {step}" for i, step in enumerate(reasoning_steps, 1))

        variant_1_system_prompt = f"""TASK: {task_description}

APPROACH — Single-Path Reasoning:
Follow these steps sequentially:
{reasoning_steps_text}

{f"DEMONSTRATION:{chr(10)}{conservative_examples_block}" if conservative_examples_block else ""}

CONSTRAINTS:
{format_list_as_bullet_points(constraints)}

OUTPUT FORMAT: {output_format}"""

        # ── Variant 2: Structured — 2 examples + dual-path + self-check ──
        structured_examples_block = self._format_examples_as_demonstration_blocks(
            all_examples, max_examples_to_include=2,
        )

        variant_2_system_prompt = f"""TASK: {task_description}

APPROACH — Dual-Path Reasoning with Self-Check:
You must generate TWO independent reasoning paths for this task.
For each path, show your working step by step.

Path 1 — Analytical Approach:
{reasoning_steps_text}

Path 2 — Verification Approach:
  1. Re-read the original input from a different angle.
  2. Challenge any assumptions from Path 1.
  3. Identify potential errors or oversights.

SELF-CHECK:
After both paths, compare results. If they agree, proceed with confidence.
If they disagree, explain the discrepancy and choose the more robust answer.

{f"DEMONSTRATIONS:{chr(10)}{structured_examples_block}" if structured_examples_block else ""}

CONSTRAINTS:
{format_list_as_bullet_points(constraints)}

OUTPUT FORMAT: {output_format}"""

        # ── Variant 3: Advanced — 3 examples + tri-path + ensemble + guards ──
        advanced_examples_block = self._format_examples_as_demonstration_blocks(
            all_examples, max_examples_to_include=3,
        )

        variant_3_system_prompt = f"""TASK: {task_description}

APPROACH — Tri-Path Ensemble Synthesis:
You must generate THREE independent reasoning paths. Each path must approach
the problem from a fundamentally different angle. After all three, synthesise
across paths using majority-vote logic.

Path 1 — Sequential Analytical Approach:
{reasoning_steps_text}

Path 2 — Adversarial Verification:
  1. Assume Path 1's answer is WRONG. What evidence would disprove it?
  2. Check boundary conditions and edge cases.
  3. Re-derive the answer independently.

Path 3 — First-Principles Decomposition:
  1. Strip the problem to its most fundamental components.
  2. Solve each component in isolation.
  3. Reassemble the component solutions into a coherent answer.

ENSEMBLE SYNTHESIS:
Compare all three paths. For each claim, count how many paths agree.
If unanimous: high confidence — proceed.
If 2-of-3 agree: moderate confidence — explain the dissent.
If all disagree: flag uncertainty — present all three perspectives.

{f"DEMONSTRATIONS:{chr(10)}{advanced_examples_block}" if advanced_examples_block else ""}

CONSTRAINTS:
{format_list_as_bullet_points(constraints)}
- Do NOT hallucinate facts outside the provided context.
- Do NOT skip any ensemble path — all three must be shown.

OUTPUT FORMAT: {output_format}"""

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

        # Prefill suggestion for Advanced Anthropic variant
        advanced_prefill = generate_claude_prefill_suggestion(request.task_type, request.provider)

        # Step 6: Build response
        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy="Single-path CoT with 1 few-shot example for guided reasoning.",
                system_prompt=variant_1_system_prompt.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(variant_1_system_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=75, context=70, role=50, tone=50, execution=75),
                strengths=["Guided reasoning path", "Few-shot grounding"],
                best_for="Moderately complex reasoning tasks",
                overshoot_guards=[],
                undershoot_guards=[],
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy="Dual-path CoT with 2 examples, self-check verification, and RAL-Writer.",
                system_prompt=variant_2_system_prompt.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(variant_2_system_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=85, context=80, role=60, tone=60, execution=85),
                strengths=["Multi-path verification", "Self-check logic", "RAL-Writer restatement"],
                best_for="Complex analysis requiring verification",
                overshoot_guards=["Self-check prevents hallucination drift"],
                undershoot_guards=[],
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy="Tri-path ensemble with 3 kNN examples, majority-vote synthesis, CoRe, and full guards.",
                system_prompt=variant_3_system_prompt.strip(),
                user_prompt="[Insert request data here]",
                prefill_suggestion=advanced_prefill,
                token_estimate=len(variant_3_system_prompt) // 4,
                tcrte_scores=VariantTCRTEScores(task=95, context=90, role=70, tone=70, execution=95),
                strengths=["Ensemble consensus", "Anti-hallucination guards", "CoRe injection", "kNN few-shot grounding"],
                best_for="High-stakes reasoning (medical, legal, financial analysis)",
                overshoot_guards=["Must complete all 3 paths", "No hallucination"],
                undershoot_guards=["Ensemble synthesis required", "Majority-vote logic enforced"],
            ),
        ]

        model_notes = f"CoT Ensemble (Medprompt) with {len(all_examples)} few-shot example(s) applied."
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        analysis = OptimizationAnalysis(
            detected_issues=["Complex reasoning task requiring multi-path verification and few-shot grounding."],
            model_notes=model_notes,
            framework_applied="cot_ensemble",
            coverage_delta=compute_coverage_delta_description(request.gap_data, 85),
        )

        response = OptimizationResponse(
            analysis=analysis,
            techniques_applied=["CoT Ensemble", "Medprompt kNN", "Multi-Path Reasoning", "Self-Check"],
            variants=variants,
        )

        # Quality gate: critique each variant, enhance weak ones, measure real scores
        response = await self._refine_variants_with_quality_critique(
            response=response,
            raw_prompt=request.raw_prompt,
            task_type=request.task_type,
            api_key=request.api_key,
            quality_gate_mode=request.quality_gate_mode,
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

    # Load environment from backend/.env
    backend_directory = Path(__file__).resolve().parent.parent.parent.parent.parent
    env_file_path = backend_directory / ".env"
    load_dotenv(env_file_path)

    HEALTHCARE_TEST_PROMPT = """
    You are a clinical decision support system. Given a patient's lab results,
    medication history, and current symptoms, determine if the patient is at risk
    for adverse drug interactions. The patient is on warfarin, metformin, and
    lisinopril. Recent labs show INR of 4.2 (elevated), HbA1c of 7.8%, and
    creatinine of 1.8 mg/dL. The patient reports dizziness and easy bruising.
    Output a structured risk assessment with severity levels.
    """

    async def test_cot_ensemble_optimizer():
        """Test the CoT Ensemble optimizer with a healthcare scenario."""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            print("ERROR: OPENAI_API_KEY not found in .env")
            sys.exit(1)

        request = OptimizationRequest(
            raw_prompt=HEALTHCARE_TEST_PROMPT,
            provider="openai",
            model_id="gpt-4.1-nano",
            model_label="GPT-4.1 Nano",
            task_type="reasoning",
            framework="cot_ensemble",
            is_reasoning_model=False,
            api_key=api_key,
        )

        optimizer = ChainOfThoughtEnsembleOptimizer()
        print("=" * 80)
        print("TESTING: CoT Ensemble Optimizer (Healthcare)")
        print("=" * 80)

        try:
            result = await optimizer.generate_variants(request=request)
            print(f"\n✓ Framework applied: {result.analysis.framework_applied}")
            print(f"✓ Techniques: {result.techniques_applied}")
            print(f"✓ Variants generated: {len(result.variants)}")
            for variant in result.variants:
                print(f"\n── Variant {variant.id}: {variant.name} ──")
                print(f"   Strategy: {variant.strategy}")
                print(f"   Token estimate: {variant.token_estimate}")
                print(f"   System prompt preview: {variant.system_prompt[:200]}...")
            print("\n✓ CoT Ensemble test PASSED")
        except Exception as error:
            print(f"\n✗ CoT Ensemble test FAILED: {error}")
            import traceback
            traceback.print_exc()

    asyncio.run(test_cot_ensemble_optimizer())
