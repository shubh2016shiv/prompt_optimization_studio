"""
Reasoning-Aware Mode Optimizer Strategy

Implements the declarative constraint architecture for Extended Thinking (o1, o3, Flash-Thinking) models.

  ┌────────────────────────┐
  │ Reasoning-Aware Logic  │
  └─────────┬──────────────┘
            │
            ▼
  ┌────────────────────────┐ 1. Extract raw intent ruthlessly stripping all CoT/reasoning instructions.
  │ Structural Stripper    │    (e.g., Removes "think step by step" or "consider all angles").
  └─────────┬──────────────┘
            │
            ▼
  ┌────────────────────────┐ 2. Parse pure deterministic bounds: 
  │ Boundary Cordoning     │    Output formatting and hard absolute constraints.
  └─────────┬──────────────┘
            │
            ▼
  ┌────────────────────────┐ 3. Synthesize Variants enforcing primacy over everything else.
  │ Variant Synthesis      │    (Conservative -> Structured -> Advanced with aggressive zero-CoT rules)
  └─────────┬──────────────┘
            │
            ▼
  ┌────────────────────────┐ 4. Emit standard JSON API Contract.
  │ Output Handshake       │
  └────────────────────────┘ 
"""

import logging
import re
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
from app.config import get_settings

logger = logging.getLogger(__name__)

_REASONING_AWARE_PROMPT = """
You are an expert prompt engineer tuning a prompt specifically for an ongoing-inference reasoning model
like OpenAI o1/o3 or Gemini Flash-Thinking.

These models perform WORSE when given "how to think" instructions (e.g. "think step by step", "first analyze X").
They need ONLY absolute declarations of boundaries and output format.

Extract from the user's raw prompt and rewrite them cleanly:
1. "absolute_task": The core objective, stated as a declarative imperative.
2. "hard_constraints": Only the absolute rules and boundaries. STRIP OUT any advice on "how" to think.
3. "output_format": The rigid output structure expected.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return exactly matching this JSON schema:
{{
  "absolute_task": "string",
  "hard_constraints": ["strings"],
  "output_format": "string"
}}
"""

class ReasoningAwareOptimizer(BaseOptimizerStrategy):
    """Deep implementation of the Reasoning-Aware mode for inference-time RL models."""

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[List[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:

        logger.info(f"Executing Reasoning-Aware compilation (stripping CoT hooks).")

        prompt_extraction = _REASONING_AWARE_PROMPT.format(raw_prompt=request.raw_prompt)
        
        async with LLMClient(api_key=request.api_key) as client:
            response_text = await client.call(
                provider=request.provider,
                prompt=prompt_extraction,
                max_tokens=2048,
                model=request.model_id,
            )

        extracted = extract_json_from_llm_response(response_text)
        task = extracted.get("absolute_task", "Execute the objective.")
        rules = extracted.get("hard_constraints", ["Be accurate and concise."])
        fmt = extracted.get("output_format", "Natural Language.")

        rules_list = "\n".join([f"- {r}" for r in rules])

        v1_sys = f"""OBJECTIVE
{task}

RULES
{rules_list}

FORMAT
{fmt}"""

        v2_sys = f"""### OBJECTIVE DECLARATION
{task}

### FORMATTING CONTRACT (REQUIRED)
{fmt}

### HARD CONSTRAINTS
{rules_list}
"""

        v3_sys = f"""# EXECUTION MANDATE
{task}

## BOUNDARY CONSTRAINTS
{rules_list}
- Adhere absolutely to the formatting schema. 
- You do not need to explain your reasoning or show a chain of thought. You must proceed directly to emitting the exact final Output Format.

## OUTPUT FORMAT
{fmt}"""

        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy="Lightly defined declarative bullet points stripped of CoT language.",
                system_prompt=v1_sys.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(v1_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=85, context=60, role=50, tone=50, execution=85),
                strengths=["High efficiency", "Anti-interference"],
                best_for="O-series direct executions",
                overshoot_guards=[],
                undershoot_guards=[]
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy="Declarative logic executing Format (Primacy) before Constraints.",
                system_prompt=v2_sys.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(v2_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=95, context=70, role=50, tone=50, execution=95),
                strengths=["Primacy Formatting lock", "Fast thinking resolution"],
                best_for="Schema-locked generation",
                overshoot_guards=["Format initialization"],
                undershoot_guards=[]
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy="Rigid Declarative Mandate with absolute ban on explanatory output generation.",
                system_prompt=v3_sys.strip(),
                user_prompt="[Insert request data here]",
                token_estimate=len(v3_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=95, context=80, role=50, tone=80, execution=95),
                strengths=["Absolute strict execution", "No token waste"],
                best_for="Zero-shot highly-complex formatting logic",
                overshoot_guards=["Explicit CoT inhibition"],
                undershoot_guards=["Schema validation required"]
            )
        ]
        
        model_notes = "Reasoning-Aware suppression of CoT hooks complete."
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        analysis = OptimizationAnalysis(
            detected_issues=["Prompt likely contained CoT induction (e.g. 'think step by step') which degrades o-series performance."],
            model_notes=model_notes,
            framework_applied="reasoning_aware",
            coverage_delta="Stripped all internal-reasoning interference. Reinforced pure task constraints.",
            auto_selected_framework="reasoning_aware" if auto_reason else None,
            auto_reason=auto_reason
        )

        response = OptimizationResponse(
            analysis=analysis,
            techniques_applied=["CoT Suppression", "Declarative Declarations"],
            variants=variants
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
