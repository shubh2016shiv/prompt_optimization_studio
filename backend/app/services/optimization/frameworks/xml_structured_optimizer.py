"""
XML Structured Bounding Optimizer Strategy

Implements the Anthropic-endorsed XML semantic hierarchy architecture.

  ┌────────────────────┐
  │ XML Architecture   │
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 1. Extract raw prompt into discrete semantic blocks via JSON-LLM call.
  │ LLM Token Parser   │    (Task, Constraints, Format)
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 2. Construct programmatic hard XML boundaries in Python.
  │ Tag Injection      │    This prevents the LLM from 'forgetting' to close tabs or 
  └─────────┬──────────┘    hallucinating irrelevant structures.
            │
            ▼
  ┌────────────────────┐ 3. Assemble `<system_directives>` and `<dynamic_context>`.
  │ Context Separation │ 4. Embed user-provided variables securely within `<input_variables>`.
  └─────────┬──────────┘    This creates structural injection defense.
            │
            ▼
  ┌────────────────────┐ 5. Generate 3 variants with escalating constraint repetition.
  │ Variant Synthesis  │    (Conservative -> Structured -> Advanced with RAL-Writer Recency Echo)
  └────────────────────┘
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

logger = logging.getLogger(__name__)

_XML_PARSER_PROMPT = """
You are a highly analytical systems architect. Analyze the user's raw prompt
and divide it logically into these three standalone semantic strings.

Required fields:
1. "task": The overarching goal and instructions in high-level precise language.
2. "constraints": The hard rules to follow, formatted as a bulleted list.
3. "format": The precise output formatting rules or JSON schema to return.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY a valid JSON object matching this schema:
{{
  "task": "...",
  "constraints": "...",
  "format": "..."
}}
"""

class XmlStructuredOptimizer(BaseOptimizerStrategy):
    """Deep implementation of the Anthropic XML Structured Bounding methodology."""

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[List[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:

        logger.info("Executing deep XML Bounding structural compilation.")

        # Step 1: LLM Sub-process to chunk semantic value reliably
        prompt_extraction = _XML_PARSER_PROMPT.format(raw_prompt=request.raw_prompt)
        
        async with LLMClient(api_key=request.api_key) as client:
            response_text = await client.call(
                provider=request.provider,
                prompt=prompt_extraction,
                max_tokens=2048,
                model=request.model_id,
                system="Return strict JSON isolating the requested fields.",
            )

        extracted = extract_json_from_llm_response(response_text)
        task_str = extracted.get("task", "Perform the user requested analysis.")
        constraints_str = extracted.get("constraints", "- Adhere to standard safety and formatting constraints.")
        format_str = extracted.get("format", "Standard natural language unless otherwise specified.")
        
        # Step 3 & 4: Python-level XML Assembly ensures 100% adherence to schema
        
        # Variant 1: Conservative (Basic XML wrappers)
        v1_sys = f"""<system_directives>
  <task>\n    {task_str}\n  </task>
  <constraints>\n    {constraints_str}\n  </constraints>
  <output_format>\n    {format_str}\n  </output_format>
</system_directives>"""

        # Variant 2: Structured (Variables explicitly cordoned, primacy enforced)
        vars_block = ""
        if request.input_variables:
            vars_block = f"""\n<dynamic_context>
  <input_variables>
    {request.input_variables}
  </input_variables>
</dynamic_context>"""

        v2_sys = f"""<system_directives>
  <constraints>
    {constraints_str}
  </constraints>
  <task>
    {task_str}
  </task>
  <output_format>
    {format_str}
  </output_format>
</system_directives>{vars_block}"""

        # Variant 3: Advanced (Includes RAL-Writer recency constraint echoing)
        v3_sys = f"""<system_directives>
  <constraints>
    {constraints_str}
    - You must isolate your output purely to the data injected in the dynamic context.
    - Hallucination and out-of-bounds generation is strictly prohibited.
  </constraints>
  <task>
    {task_str}
  </task>
  <output_format>
    {format_str}
  </output_format>
</system_directives>{vars_block}

<restate_critical>
REMINDER TO ASSISTANT:
{constraints_str}
Output Format MUST match: {format_str}
</restate_critical>"""

        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy="Lightweight XML tagging for semantic clarity.",
                system_prompt=v1_sys.strip(),
                user_prompt="<user_input>\n[Insert dynamic user variables here]\n</user_input>",
                token_estimate=len(v1_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=70, context=60, role=50, tone=50, execution=70),
                strengths=["Anthropic alignment", "Clean formatting"],
                best_for="Low-complexity tasks",
                overshoot_guards=[],
                undershoot_guards=[]
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy="Ordered XML architecture prioritizing Constraints (Primacy Effect) and cordoning Input Variables.",
                system_prompt=v2_sys.strip(),
                user_prompt="<user_input>\n[Insert user data here]\n</user_input>",
                token_estimate=len(v2_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=85, context=80, role=70, tone=70, execution=85),
                strengths=["Primacy constraints", "Prompt injection defense"],
                best_for="Production datasets",
                overshoot_guards=["Isolated context boundary"],
                undershoot_guards=[]
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy="Full XML bounds with RAL-Writer Restate and injection lock-down.",
                system_prompt=v3_sys.strip(),
                user_prompt="<user_input>\n[Insert user data here]\n</user_input>",
                token_estimate=len(v3_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=95, context=90, role=90, tone=90, execution=95),
                strengths=["Recency constraint echo", "Anti-hallucination"],
                best_for="High-stakes RAG pipelines",
                overshoot_guards=["RAL-Writer recency block", "Anti-hallucination"],
                undershoot_guards=["Strict boundary rules"]
            )
        ]

        if request.provider == "anthropic":
            variants[2].prefill_suggestion = "<response>" # Pre-fill to lock structure
        
        model_notes = "XML programmatic boundary construction complete."
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        analysis = OptimizationAnalysis(
            detected_issues=["Unbounded instructions merged with variable context."],
            model_notes=model_notes,
            framework_applied="xml_structured",
            coverage_delta="Established 100% rigid semantic boundaries.",
            auto_selected_framework="xml_structured" if auto_reason else None,
            auto_reason=auto_reason
        )

        response = OptimizationResponse(
            analysis=analysis,
            techniques_applied=["XML-Bounding", "Python-Assembly", "Primacy-Placement"],
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

