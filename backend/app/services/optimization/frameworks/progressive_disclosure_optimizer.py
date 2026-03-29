"""
Progressive Disclosure Optimizer Strategy

Implements the 3-Layer Agent Skills Architecture.

  ┌────────────────────┐
  │ 3-Layer Algorithm  │
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 1. Extract raw intent into Discovery, Activation, Execution via LLM.
  │ Component Parser   │    (Metadata, Triggers, Logical Rules, Scripts/Format)
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 2. Construct 3-layer logical architecture natively in Python.
  │ Layer Sequencing   │    Separates 'When to do X' from 'How to do X'.
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 3. Synthesize chronological execution logic.
  │ Variant Synthesis  │    (Conservative -> Structured -> Advanced with XML Skill borders)
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 4. Emit standard JSON schema for API ingestion.
  │ Output Handshake   │
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

_PROG_DISCLOSURE_PROMPT = """
You are an expert agentic AI architect. Deconstruct the user's raw prompt 
into the 3-Layer Progressive Disclosure architecture.

1. "discovery_metadata": High-level descriptions of what skills/tools are available. 
2. "activation_rules": The precise conditions or triggers for when to apply those skills.
3. "execution_logic": The step-by-step logic, procedures, and rules for executing the skill.
4. "output_format": The rigid output structure to return upon completion.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return exactly matching this JSON object schema:
{{
  "discovery_metadata": "string",
  "activation_rules": "string",
  "execution_logic": "string",
  "output_format": "string"
}}
"""

class ProgressiveDisclosureOptimizer(BaseOptimizerStrategy):
    """Deep implementation of the Progressive Disclosure optimization framework."""

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[List[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:

        logger.info(f"Executing Progressive Disclosure compilation.")

        prompt_extraction = _PROG_DISCLOSURE_PROMPT.format(raw_prompt=request.raw_prompt)
        
        async with LLMClient(api_key=request.api_key) as client:
            response_text = await client.call(
                provider=request.provider,
                prompt=prompt_extraction,
                max_tokens=2048,
                model=request.model_id,
            )

        extracted = extract_json_from_llm_response(response_text)
        meta = extracted.get("discovery_metadata", "Available Capabilities: Answer Questions")
        rules = extracted.get("activation_rules", "If asked a question, answer it.")
        logic = extracted.get("execution_logic", "Generate a helpful response.")
        fmt = extracted.get("output_format", "Natural Language.")

        v1_sys = f"""DISCOVERY LAYER:
{meta}

ACTIVATION LAYER:
{rules}

EXECUTION LAYER:
{logic}
Format: {fmt}"""

        v2_sys = f"""### LAYER 1 — DISCOVERY METADATA
{meta}

### LAYER 2 — ACTIVATION TRIGGERS 
{rules}

### LAYER 3 — EXECUTION LOGIC
{logic}

### OUTPUT SPECIFICATION
{fmt}"""

        v3_sys = f"""<system_architecture>
  <discovery_layer>
    <metadata>
      {meta}
    </metadata>
  </discovery_layer>

  <activation_layer>
    <triggers>
      {rules}
    </triggers>
  </activation_layer>

  <execution_layer>
    <procedures>
      {logic}
    </procedures>
  </execution_layer>

  <formatting_layer>
    <schema>
      {fmt}
    </schema>
  </formatting_layer>
</system_architecture>"""

        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy="Lightly defined 3-layer chronological structure.",
                system_prompt=v1_sys.strip(),
                user_prompt="[Insert request string here]",
                token_estimate=len(v1_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=75, context=70, role=50, tone=50, execution=70),
                strengths=["Readability", "Chronological order"],
                best_for="Simple agent routing",
                overshoot_guards=[],
                undershoot_guards=[]
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy="Full 3-layer architecture via distinct markdown boundaries.",
                system_prompt=v2_sys.strip(),
                user_prompt="[Insert request string here]",
                token_estimate=len(v2_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=85, context=85, role=70, tone=70, execution=85),
                strengths=["Explicit breakdown", "Easy to debug rules"],
                best_for="Standard complex agentic flows",
                overshoot_guards=["Defined Execution boundaries"],
                undershoot_guards=[]
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy="Nested XML boundaries strictly separating Meta from Logic and Formatting.",
                system_prompt=v3_sys.strip(),
                user_prompt="<user_invocation>\n[Insert request string here]\n</user_invocation>",
                token_estimate=len(v3_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=95, context=95, role=85, tone=85, execution=95),
                strengths=["Logic isolation", "Strong Tool Triggering"],
                best_for="Multi-Agent Systems (MAS)",
                overshoot_guards=["Strict Architecture containment"],
                undershoot_guards=["Schema validation"]
            )
        ]
        
        model_notes = "Progressive Disclosure component mapping complete."
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        analysis = OptimizationAnalysis(
            detected_issues=["Execution logic blended inappropriately into Discovery metadata."],
            model_notes=model_notes,
            framework_applied="progressive",
            coverage_delta="Execution pathways cordoned securely.",
            auto_selected_framework="progressive" if auto_reason else None,
            auto_reason=auto_reason
        )

        response = OptimizationResponse(
            analysis=analysis,
            techniques_applied=["3-Layer Architecture", "Progressive Disclosure"],
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
