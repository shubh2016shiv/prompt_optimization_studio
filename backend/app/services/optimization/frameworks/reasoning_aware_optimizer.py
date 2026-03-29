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

_REASONING_AWARE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "absolute_task": {"type": "string"},
        "hard_constraints": {
            "type": "array",
            "items": {"type": "string"},
        },
        "output_format": {"type": "string"},
    },
    "required": ["absolute_task", "hard_constraints", "output_format"],
    "additionalProperties": False,
}

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
        
        extraction = await self._extract_reasoning_sections(
            provider=request.provider,
            model_id=request.model_id,
            api_key=request.api_key,
            extraction_prompt=prompt_extraction,
        )
        task = extraction["absolute_task"]
        rules = extraction["hard_constraints"]
        fmt = extraction["output_format"]

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
            target_model=request.model_id,
        )

        return response

    async def _extract_reasoning_sections(
        self,
        *,
        provider: str,
        model_id: str,
        api_key: str,
        extraction_prompt: str,
    ) -> dict[str, Any]:
        """
        Extract and validate reasoning-aware sections from model output.

        This routine uses provider-aware structured response settings where
        supported and adds a single repair retry for malformed payloads.
        """
        response_format = self._structured_response_format_for_provider(provider)

        async with LLMClient(api_key=api_key) as llm_client:
            response_text = await llm_client.call(
                provider=provider,
                prompt=extraction_prompt,
                max_tokens=2048,
                model=model_id,
                response_format=response_format,
            )

            try:
                parsed_payload = extract_json_from_llm_response(response_text)
                extracted = coerce_top_level_object(
                    parsed_payload,
                    context_label="reasoning_aware extraction",
                )
            except JSONExtractionError:
                repair_prompt = (
                    "Repair the payload into VALID JSON matching this schema exactly.\n"
                    "Return ONLY JSON.\n\n"
                    f"Schema:\n{json.dumps(_REASONING_AWARE_SCHEMA, ensure_ascii=True)}\n\n"
                    f"Malformed payload:\n{response_text}"
                )
                repaired_response = await llm_client.call(
                    provider=provider,
                    prompt=repair_prompt,
                    max_tokens=2048,
                    model=model_id,
                    response_format=response_format,
                )
                repaired_payload = extract_json_from_llm_response(repaired_response)
                extracted = coerce_top_level_object(
                    repaired_payload,
                    context_label="reasoning_aware repaired extraction",
                )

        absolute_task = extracted.get("absolute_task")
        if isinstance(absolute_task, str) and absolute_task.strip():
            normalized_task = absolute_task.strip()
        else:
            normalized_task = "Execute the objective."

        hard_constraints = extracted.get("hard_constraints")
        normalized_rules: list[str] = []
        if isinstance(hard_constraints, list):
            normalized_rules = [str(item).strip() for item in hard_constraints if str(item).strip()]
        elif isinstance(hard_constraints, str):
            for line in hard_constraints.splitlines():
                cleaned = line.strip().lstrip("-").strip()
                if cleaned:
                    normalized_rules.append(cleaned)
        if not normalized_rules:
            normalized_rules = ["Be accurate and concise."]

        output_format = extracted.get("output_format")
        if isinstance(output_format, str) and output_format.strip():
            normalized_format = output_format.strip()
        elif isinstance(output_format, (dict, list)):
            normalized_format = json.dumps(output_format, indent=2, ensure_ascii=True)
        else:
            normalized_format = "Natural Language."

        return {
            "absolute_task": normalized_task,
            "hard_constraints": normalized_rules,
            "output_format": normalized_format,
        }

    def _structured_response_format_for_provider(self, provider: str) -> Optional[dict[str, Any]]:
        """Return provider-compatible structured response hints when available."""
        if provider == "openai":
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": "reasoning_aware_sections",
                    "strict": True,
                    "schema": _REASONING_AWARE_SCHEMA,
                },
            }
        if provider == "google":
            return {
                "type": "json_schema",
                "json_schema": {"schema": _REASONING_AWARE_SCHEMA},
            }
        return None

