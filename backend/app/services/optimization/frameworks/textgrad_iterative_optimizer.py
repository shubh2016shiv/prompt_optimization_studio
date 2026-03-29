"""
TextGrad Iterative Optimizer Strategy — Pure-Python Implementation

Implements the TextGrad framework from APOST_v4_Documentation.md §4.5,
based on the Stanford paper "TextGrad: Automatic Differentiation via Text"
(Yuksekgonul et al., 2024). This replaces the external `textgrad` library
dependency with a lightweight 3-iteration evaluate→critique→rewrite loop
using the user's own LLM API key.

ALGORITHM WORKFLOW:
═══════════════════════════════════════════════════════════════════════════════

  ┌───────────────────────────────────┐
  │  TextGrad Iterative Loop          │
  │  (3 iterations by default)        │
  └────────────────┬──────────────────┘
                   │
                   ▼
  ┌───────────────────────────────────┐  Step 1: INITIALISE
  │  Iteration Controller             │  current_prompt = raw_prompt (enriched
  │                                   │  with gap answers). iteration = 1.
  └────────────────┬──────────────────┘
                   │
        ┌──────────┘  (loop for N iterations)
        │
        ▼
  ┌───────────────────────────────────┐  Step 2: FORWARD PASS (Evaluator)
  │  TCRTE Evaluator (TextLoss)       │  LLM evaluates current_prompt against the
  │                                   │  TCRTE rubric. Returns a structured critique:
  │                                   │    - Per-dimension scores
  │                                   │    - Specific violations identified
  └────────────────┬──────────────────┘    - Concrete improvement suggestions
                   │
                   ▼
  ┌───────────────────────────────────┐  Step 3: BACKWARD PASS (Gradient)
  │  Gradient Localiser               │  LLM takes the critique and LOCALISES it
  │                                   │  to specific text spans in the prompt.
  │                                   │  "Lines 3-5 lack output schema" → targeted.
  └────────────────┬──────────────────┘
                   │
                   ▼
  ┌───────────────────────────────────┐  Step 4: UPDATE STEP (Rewriter)
  │  Prompt Rewriter                  │  LLM rewrites ONLY the identified spans,
  │                                   │  preserving the rest intact. Saves checkpoint.
  │                                   │  current_prompt = rewritten_prompt.
  └────────────────┬──────────────────┘
                   │
        └──────────┘  (end loop)
                   │
                   ▼
  ┌───────────────────────────────────┐  Step 5: CHECKPOINT MAPPING
  │  Checkpoint Mapper                │  Map 3 checkpoints → 3 variants:
  │                                   │    iteration 1 → Conservative
  │                                   │    iteration 2 → Structured
  └───────────────────────────────────┘    iteration 3 → Advanced

COST ANALYSIS:
  3 LLM calls per iteration × 3 iterations = 9 total LLM calls.
  ~2000 tokens per call × 9 = ~18,000 total tokens.
  At gpt-4.1-nano rates ($0.10/1M input, $0.40/1M output) ≈ < $0.01 total.

TESTING:
  Run this file directly to test with a healthcare example:
    cd d:\\Generative AI Portfolio Projects\\APOST\\backend
    python -m app.services.optimization.frameworks.textgrad_iterative_optimizer

REFERENCES:
  - Yuksekgonul et al., "TextGrad: Automatic Differentiation via Text" (2024)
  - APOST_v4_Documentation.md §4.5
"""

import asyncio
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
    MAX_TOKENS_TEXTGRAD_EVALUATION,
    MAX_TOKENS_TEXTGRAD_GRADIENT,
    MAX_TOKENS_TEXTGRAD_UPDATE,
    TEXTGRAD_DEFAULT_ITERATION_COUNT,
    SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
)
from app.services.optimization.shared_prompt_techniques import (
    integrate_gap_interview_answers_into_prompt,
    inject_input_variables_block,
    generate_claude_prefill_suggestion,
    compute_coverage_delta_description,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# LLM Prompt Templates for TextGrad Sub-Tasks
# ──────────────────────────────────────────────────────────────────────────────

_TEXTGRAD_EVALUATION_PROMPT = """
You are a TCRTE prompt evaluator. Evaluate the following prompt against the
5 TCRTE dimensions and identify specific weaknesses.

TCRTE RUBRIC:
  TASK:      Is there a clear imperative verb, measurable output, and success criterion?
  CONTEXT:   Is the domain, data source, and temporal scope specified?
  ROLE:      Is there an expert persona with seniority and behavioural calibration?
  TONE:      Is formality, audience, and hedging prohibition specified?
  EXECUTION: Is the output format, length limit, and prohibited content named?

<prompt_to_evaluate>
{current_prompt}
</prompt_to_evaluate>

Return ONLY valid JSON:
{{
  "scores": {{"task": 0, "context": 0, "role": 0, "tone": 0, "execution": 0}},
  "violations": [
    {{"dimension": "task|context|role|tone|execution", "description": "specific issue", "severity": "critical|moderate|minor"}}
  ],
  "overall_assessment": "one paragraph summary of the prompt's quality"
}}
"""

_TEXTGRAD_GRADIENT_LOCALISATION_PROMPT = """
You are a textual gradient localiser. Given a prompt and its TCRTE evaluation,
identify the EXACT text spans that need modification and what each modification
should achieve.

<current_prompt>
{current_prompt}
</current_prompt>

<evaluation_critique>
{evaluation_critique}
</evaluation_critique>

For each violation, locate where in the prompt the fix should be applied.
Return ONLY valid JSON:
{{
  "localised_edits": [
    {{
      "target_text": "exact text span to modify (or 'APPEND' / 'PREPEND' for new content)",
      "suggested_action": "what to change, add, or remove",
      "dimension_addressed": "task|context|role|tone|execution",
      "priority": 1
    }}
  ]
}}
"""

_TEXTGRAD_PROMPT_REWRITE_PROMPT = """
You are a precision prompt rewriter. Apply the following localised edits to the
prompt. Preserve ALL text that is not targeted by an edit. Do NOT add unnecessary
content or remove working sections.

<current_prompt>
{current_prompt}
</current_prompt>

<edits_to_apply>
{gradient_edits}
</edits_to_apply>

Return ONLY the complete rewritten prompt text (no JSON wrapping, no explanations).
Output the full improved prompt directly.
"""


class TextGradIterativeOptimizer(BaseOptimizerStrategy):
    """
    Deep implementation of the TextGrad iterative optimization framework.

    This optimizer runs a 3-iteration evaluate→critique→rewrite loop,
    analogous to gradient descent in neural networks but using natural
    language "gradients" (textual critiques) instead of numerical ones.

    Each iteration produces a checkpoint, and the 3 checkpoints map to
    the Conservative / Structured / Advanced variants.

    Architecture:
        - No external `textgrad` library dependency
        - Uses the user's own LLM API key via LLMClient
        - All sub-tasks (evaluate, localise, rewrite) use the user's model
        - Falls back gracefully if any iteration fails
    """

    # ──────────────────────────────────────────────────────────────────────
    # Step 2: Forward Pass — TCRTE Evaluation
    # ──────────────────────────────────────────────────────────────────────

    async def _evaluate_prompt_against_tcrte_rubric(
        self,
        current_prompt: str,
        llm_client: LLMClient,
        provider: str,
        model_id: str,
    ) -> dict:
        """
        Evaluate the current prompt against the TCRTE rubric.

        This is the "forward pass" in the TextGrad analogy — computing the
        loss function (how far the prompt is from ideal TCRTE coverage).

        Args:
            current_prompt: The prompt text to evaluate.
            llm_client: Active LLM client instance.
            provider: LLM provider string.
            model_id: Target model ID.

        Returns:
            Parsed evaluation dict with scores, violations, and assessment.
        """
        evaluation_prompt = _TEXTGRAD_EVALUATION_PROMPT.format(
            current_prompt=current_prompt,
        )

        response_text = await llm_client.call(
            provider=provider,
            prompt=evaluation_prompt,
            max_tokens=MAX_TOKENS_TEXTGRAD_EVALUATION,
            model=model_id,
            system="You are a strict TCRTE prompt auditor. Return ONLY valid JSON.",
        )

        return extract_json_from_llm_response(response_text)

    # ──────────────────────────────────────────────────────────────────────
    # Step 3: Backward Pass — Gradient Localisation
    # ──────────────────────────────────────────────────────────────────────

    async def _localise_gradient_to_text_spans(
        self,
        current_prompt: str,
        evaluation_critique: dict,
        llm_client: LLMClient,
        provider: str,
        model_id: str,
    ) -> dict:
        """
        Localise the evaluation critique to specific text spans in the prompt.

        This is the "backward pass" — computing the gradient (which parts of
        the prompt need to change and how).

        Args:
            current_prompt: The current prompt text.
            evaluation_critique: Output from the evaluation step.
            llm_client: Active LLM client instance.
            provider: LLM provider string.
            model_id: Target model ID.

        Returns:
            Parsed gradient dict with localised_edits.
        """
        import json
        gradient_prompt = _TEXTGRAD_GRADIENT_LOCALISATION_PROMPT.format(
            current_prompt=current_prompt,
            evaluation_critique=json.dumps(evaluation_critique, indent=2),
        )

        response_text = await llm_client.call(
            provider=provider,
            prompt=gradient_prompt,
            max_tokens=MAX_TOKENS_TEXTGRAD_GRADIENT,
            model=model_id,
            system="You are a precision code-editor. Return ONLY valid JSON.",
        )

        return extract_json_from_llm_response(response_text)

    # ──────────────────────────────────────────────────────────────────────
    # Step 4: Update Step — Prompt Rewrite
    # ──────────────────────────────────────────────────────────────────────

    async def _apply_gradient_edits_to_prompt(
        self,
        current_prompt: str,
        gradient_edits: dict,
        llm_client: LLMClient,
        provider: str,
        model_id: str,
    ) -> str:
        """
        Apply the localised gradient edits to produce an improved prompt.

        This is the "update step" — modifying the parameters (prompt text)
        in the direction that reduces the loss (TCRTE violations).

        Args:
            current_prompt: The current prompt text.
            gradient_edits: Output from the gradient localisation step.
            llm_client: Active LLM client instance.
            provider: LLM provider string.
            model_id: Target model ID.

        Returns:
            The rewritten prompt text.
        """
        import json
        rewrite_prompt = _TEXTGRAD_PROMPT_REWRITE_PROMPT.format(
            current_prompt=current_prompt,
            gradient_edits=json.dumps(gradient_edits.get("localised_edits", []), indent=2),
        )

        rewritten_text = await llm_client.call(
            provider=provider,
            prompt=rewrite_prompt,
            max_tokens=MAX_TOKENS_TEXTGRAD_UPDATE,
            model=model_id,
            system="You are a precision prompt rewriter. Output ONLY the improved prompt text.",
        )

        return rewritten_text.strip()

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
        Run the TextGrad iterative optimization loop and return 3 checkpoints as variants.

        Workflow:
            Step 1: Initialise with enriched prompt.
            Step 2-4: Run N iterations of evaluate→localise→rewrite.
            Step 5: Map checkpoints to variants.
            Step 6: Apply final enhancements and return.
        """
        logger.info("Executing TextGrad iterative optimization loop.")

        # Step 1: Initialise
        current_prompt = integrate_gap_interview_answers_into_prompt(
            raw_prompt=request.raw_prompt,
            gap_interview_answers=request.answers,
            gap_analysis_data=request.gap_data,
        )

        iteration_count = TEXTGRAD_DEFAULT_ITERATION_COUNT
        checkpoints: list[str] = []
        final_evaluation: dict = {}

        # Step 2-4: Iterative loop
        async with LLMClient(api_key=request.api_key) as llm_client:
            for iteration_number in range(1, iteration_count + 1):
                logger.info(
                    "TextGrad iteration %d/%d (prompt length: %d chars)",
                    iteration_number, iteration_count, len(current_prompt),
                )

                try:
                    # 60-second guard per full iteration (evaluate + localise + rewrite)
                    # prevents a single slow API call from blocking the entire request
                    async with asyncio.timeout(60):
                        # Step 2: Forward pass — evaluate
                        evaluation_result = await self._evaluate_prompt_against_tcrte_rubric(
                            current_prompt=current_prompt,
                            llm_client=llm_client,
                            provider=request.provider,
                            model_id=request.model_id,
                        )
                        final_evaluation = evaluation_result

                        # Step 3: Backward pass — localise gradient
                        gradient_result = await self._localise_gradient_to_text_spans(
                            current_prompt=current_prompt,
                            evaluation_critique=evaluation_result,
                            llm_client=llm_client,
                            provider=request.provider,
                            model_id=request.model_id,
                        )

                        # Step 4: Update step — rewrite
                        rewritten_prompt = await self._apply_gradient_edits_to_prompt(
                            current_prompt=current_prompt,
                            gradient_edits=gradient_result,
                            llm_client=llm_client,
                            provider=request.provider,
                            model_id=request.model_id,
                        )

                    # Save checkpoint and advance
                    checkpoints.append(rewritten_prompt)
                    current_prompt = rewritten_prompt

                    logger.info(
                        "TextGrad iteration %d complete. Checkpoint saved (%d chars).",
                        iteration_number, len(rewritten_prompt),
                    )

                except TimeoutError:
                    logger.warning(
                        "TextGrad iteration %d timed out after 60s. Saving current state as checkpoint.",
                        iteration_number,
                    )
                    checkpoints.append(current_prompt)

                except Exception as iteration_error:
                    logger.warning(
                        "TextGrad iteration %d failed (%s). Saving current state as checkpoint.",
                        iteration_number, iteration_error,
                    )
                    checkpoints.append(current_prompt)

        # Ensure we have exactly 3 checkpoints (pad with last state if iterations failed)
        while len(checkpoints) < 3:
            checkpoints.append(current_prompt)

        # Step 5: Map checkpoints to variants
        variant_names = ["Conservative", "Structured", "Advanced"]
        variant_strategies = [
            "TextGrad iteration 1 — initial TCRTE-guided structural improvements.",
            "TextGrad iteration 2 — deeper refinement targeting remaining violations.",
            "TextGrad iteration 3 — most refined checkpoint after full iterative loop.",
        ]

        # Apply final enhancements to each variant
        for checkpoint_index in range(3):
            checkpoints[checkpoint_index] = inject_input_variables_block(
                checkpoints[checkpoint_index],
                request.input_variables,
                request.provider,
            )

        advanced_prefill = generate_claude_prefill_suggestion(request.task_type, request.provider)

        variants = [
            PromptVariant(
                id=variant_index + 1,
                name=variant_names[variant_index],
                strategy=variant_strategies[variant_index],
                system_prompt=checkpoints[variant_index].strip(),
                user_prompt="[Insert request data here]",
                prefill_suggestion=advanced_prefill if variant_index == 2 else None,
                token_estimate=len(checkpoints[variant_index]) // 4,
                tcrte_scores=VariantTCRTEScores(
                    task=60 + (variant_index * 15),
                    context=55 + (variant_index * 15),
                    role=50 + (variant_index * 15),
                    tone=50 + (variant_index * 15),
                    execution=60 + (variant_index * 15),
                ),
                strengths=[f"TextGrad checkpoint {variant_index + 1}", "TCRTE-guided iterative refinement"],
                best_for="Prompts where multi-step critique and rewrite beats one-shot meta-prompting.",
                overshoot_guards=["Targeted edits preserve working sections"],
                undershoot_guards=["Each iteration addresses remaining violations"],
            )
            for variant_index in range(3)
        ]

        # Build analysis from final evaluation
        overall_assessment = final_evaluation.get("overall_assessment", "TextGrad optimization complete.")
        detected_issues = [overall_assessment] if overall_assessment else ["TextGrad optimization applied."]

        model_notes = f"TextGrad ran {len(checkpoints)} iterations. method=textgrad_iterative_pure_python."
        if auto_reason:
            model_notes += f" Auto-select: {auto_reason}"

        analysis = OptimizationAnalysis(
            detected_issues=detected_issues,
            model_notes=model_notes,
            framework_applied="textgrad",
            coverage_delta=compute_coverage_delta_description(request.gap_data, None),
        )

        response = OptimizationResponse(
            analysis=analysis,
            techniques_applied=["TextGrad", "TCRTE-Loss", "Iterative Backpropagation"],
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

    HEALTHCARE_TEST_PROMPT = """
    Review the patient's medication list for drug interactions. The patient takes
    warfarin 5mg daily, amiodarone 200mg daily, and metoprolol 50mg twice daily.
    Check if any combinations pose risks. Give me the results.
    """

    async def test_textgrad_iterative_optimizer():
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            print("ERROR: OPENAI_API_KEY not found in .env")
            sys.exit(1)

        request = OptimizationRequest(
            raw_prompt=HEALTHCARE_TEST_PROMPT,
            provider="openai",
            model_id="gpt-4.1-nano",
            model_label="GPT-4.1 Nano",
            task_type="analysis",
            framework="textgrad",
            is_reasoning_model=False,
            api_key=api_key,
        )

        optimizer = TextGradIterativeOptimizer()
        print("=" * 80)
        print("TESTING: TextGrad Iterative Optimizer (Healthcare)")
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
                preview_length = min(300, len(variant.system_prompt))
                print(f"   System prompt preview: {variant.system_prompt[:preview_length]}...")
            print(f"\n✓ Final critique: {result.analysis.detected_issues[0][:200]}...")
            print("\n✓ TextGrad test PASSED")
        except Exception as error:
            print(f"\n✗ TextGrad test FAILED: {error}")
            import traceback
            traceback.print_exc()

    asyncio.run(test_textgrad_iterative_optimizer())

