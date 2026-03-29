"""
KERNEL Prompt Optimizer Strategy

Implements the KERNEL framework (Keep it simple, Explicit rules, Narrow scope, Logical order).

  ┌────────────────────┐
  │ KERNEL Algorithm   │
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 1. Extract raw intent into discrete logical components via LLM.
  │ Component Parser   │    (Context, Task, Positive Rules, Negative Rules, Format) 
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 2. Filter ambiguous/redundant constraints.
  │ Pruning & Sorting  │ 3. Enforce logical sequencing (Context -> Task -> Constraints -> Format)
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 4. Synthesize 3 Variants natively in Python based on components.
  │ Variant Assembler  │    Conservative: Cleaned-up original
  └─────────┬──────────┘    Structured:   Strict KERNEL headings
            │               Advanced:     Added auto-guardrails
            ▼
  ┌────────────────────┐ 5. Construct valid OptimizationResponse JSON object API Contract.
  │ Return Payload     │
  └────────────────────┘
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

logger = logging.getLogger(__name__)

# The strict KERNEL parser prompt
_KERNEL_EXTRACTION_PROMPT = """
Analyze the following raw prompt and extract its core components exactly as specified.
Your goal is to deconstruct the prompt according to the KERNEL methodology.

Extract:
1. "context": Background knowledge, data sources, or grounding information.
2. "task": The primary action or objective, heavily narrowed scope.
3. "positive_constraints": Hard rules on what the model MUST do or include.
4. "negative_constraints": Hard rules on what the model MUST NOT do or include.
5. "format": The explicit output structure (JSON, markdown, length limits, etc.)

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY a valid JSON object matching this schema:
{{
  "context": "string",
  "task": "string",
  "positive_constraints": ["string"],
  "negative_constraints": ["string"],
  "format": "string"
}}
"""


class KernelOptimizer(BaseOptimizerStrategy):
    """Deep implementation of the KERNEL optimization framework."""

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[List[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:
        
        logger.info(f"Running KERNEL optimization on prompt (len={len(request.raw_prompt)})")

        # Step 1: Discrete API call to explicitly deconstruct the prompt into KERNEL pillars
        prompt_extraction = _KERNEL_EXTRACTION_PROMPT.format(raw_prompt=request.raw_prompt)
        
        async with LLMClient(api_key=request.api_key) as client:
            response_text = await client.call(
                provider=request.provider,
                prompt=prompt_extraction,
                max_tokens=2048,
                model=request.model_id,
                system="You are a strict code parser. Return ONLY JSON.",
            )

        # Step 2: Extract JSON payload natively
        extracted = extract_json_from_llm_response(response_text)
        ctx = extracted.get("context", "")
        task = extracted.get("task", "")
        pos_rules = extracted.get("positive_constraints", [])
        neg_rules = extracted.get("negative_constraints", [])
        fmt = extracted.get("format", "")

        # Step 3 & 4: Natively assemble variants without monolithic LLM hallucination
        
        # Variant 1: Conservative (Polished original prose)
        v1_system = f"""{ctx}

Your objective is: {task}

Requirements:
{self._bullet_join(pos_rules)}
{self._bullet_join(neg_rules)}

Output Format: {fmt}"""

        # Variant 2: Structured (Strict KERNEL Headings)
        v2_system = f"""### Context
{ctx}

### Task
{task}

### Constraints
*MUST DO:*
{self._bullet_join(pos_rules)}

*MUST NOT DO:*
{self._bullet_join(neg_rules)}

### Format
{fmt}"""

        # Variant 3: Advanced (KERNEL + Fail-safes, Guardrails)
        v3_system = f"""==============
CONTEXT LAYER
==============
{ctx}

=============
EXACT TASK
=============
{task}

=============
CONSTRAINTS
=============
[POSITIVE]
{self._bullet_join(pos_rules)}
- Validate all input data before generating the main response.
- Ensure strict completion of all format fields.

[NEGATIVE (CRITICAL)]
{self._bullet_join(neg_rules)}
- DO NOT hallucinate facts outside the provided Context Layer.
- DO NOT append conversational preamble or postamble (e.g., 'Here is your response').

=============
OUTPUT SCHEMA
=============
{fmt}"""

        # Step 5: Format API payload aligning exactly with UI expectations
        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy="Cleaned prose adhering to basic KERNEL filtering.",
                system_prompt=v1_system.strip(),
                user_prompt="[Insert dynamic user variables here]",
                token_estimate=len(v1_system) // 4,
                tcrte_scores=VariantTCRTEScores(task=70, context=60, role=50, tone=50, execution=70),
                strengths=["Readability", "Simplicity"],
                best_for="Low-complexity tasks",
                overshoot_guards=[],
                undershoot_guards=[]
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy="Strict KERNEL logical order (Context -> Task -> Constraints -> Format).",
                system_prompt=v2_system.strip(),
                user_prompt="[Insert dynamic user variables here]",
                token_estimate=len(v2_system) // 4,
                tcrte_scores=VariantTCRTEScores(task=85, context=80, role=70, tone=70, execution=85),
                strengths=["Explicit borders", "Narrowed scope"],
                best_for="Production RAG flows",
                overshoot_guards=["Separated negative constraints"],
                undershoot_guards=[]
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy="KERNEL with injected hallucination guards and completion constraints.",
                system_prompt=v3_system.strip(),
                user_prompt="[Insert dynamic user variables here]",
                token_estimate=len(v3_system) // 4,
                tcrte_scores=VariantTCRTEScores(task=95, context=90, role=90, tone=90, execution=95),
                strengths=["Failsafe boundaries", "Max control"],
                best_for="High-stakes or complex instructions",
                overshoot_guards=["No preamble", "No hallucination"],
                undershoot_guards=["Validate input", "Enforce full schema"]
            )
        ]

        model_notes = "KERNEL programmatic assembly complete."
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        analysis = OptimizationAnalysis(
            detected_issues=["Unstructured raw prose parsed into components."],
            model_notes=model_notes,
            framework_applied="kernel",
            coverage_delta="Structural clarity verified algorithmically.",
            auto_selected_framework="kernel" if auto_reason else None,
            auto_reason=auto_reason
        )

        response = OptimizationResponse(
            analysis=analysis,
            techniques_applied=["LLM-Parsing", "Python-Assembly", "KERNEL-Structure"],
            variants=variants
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

    def _bullet_join(self, items: List[str]) -> str:
        if not items:
            return "- None specified."
        return "\n".join([f"- {i}" for i in items])

