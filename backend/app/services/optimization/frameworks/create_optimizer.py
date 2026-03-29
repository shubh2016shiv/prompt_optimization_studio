"""
CREATE Prompt Optimizer Strategy

Implements the CREATE framework: Character, Request, Examples, Adjustments, Type of Output, Extras.

  ┌────────────────────┐
  │ CREATE Algorithm   │
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 1. Extract raw intent into the six specific C.R.E.A.T.E blocks.
  │ Component Parser   │    Uses localized LLM parser to classify user input string appropriately.
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 2. Construct robust strings specifically mapping to Character (Role) and
  │ Component Typing   │    Type of Output (Format rules) independently.
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐ 3. Synthesize chronological execution logic.
  │ Variant Synthesis  │    (Conservative: Basic sequence -> Structured: Marked headers ->
  └─────────┬──────────┘     Advanced: Strict sequential block execution with extra guardrails)
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

_CREATE_EXTRACTION_PROMPT = """
You are an expert mapping algorithm. Deconstruct the user's raw prompt into the CREATE framework.

1. "character": The role or persona the AI should adopt.
2. "request": The precise objective or task.
3. "examples": Any context or demonstrations provided.
4. "adjustments": Constraints, rules, or iterative adjustments to make.
5. "type_of_output": The expected format (e.g., JSON, list, tone, length).
6. "extras": Safety rules, hallucination guards, missing edge-cases.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return exactly matching this JSON object schema:
{{
  "character": "string",
  "request": "string",
  "examples": "string",
  "adjustments": "string",
  "type_of_output": "string",
  "extras": "string"
}}
"""

class CreateOptimizer(BaseOptimizerStrategy):
    """Deep implementation of the CREATE optimization framework."""

    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[List[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:

        logger.info(f"Executing CREATE sequential compilation.")

        prompt_extraction = _CREATE_EXTRACTION_PROMPT.format(raw_prompt=request.raw_prompt)
        
        async with LLMClient(api_key=request.api_key) as client:
            response_text = await client.call(
                provider=request.provider,
                prompt=prompt_extraction,
                max_tokens=2048,
                model=request.model_id,
            )

        extracted = extract_json_from_llm_response(response_text)
        character = extracted.get("character", "You are an AI assistant.")
        req = extracted.get("request", "Process the following input.")
        examples = extracted.get("examples", "- No explicit examples provided.")
        adjustments = extracted.get("adjustments", "- Standard procedural guidelines.")
        output_type = extracted.get("type_of_output", "Format as clear prose.")
        extras = extracted.get("extras", "- Verify facts before outputting.")

        v1_sys = f"""ROLE:
{character}

OBJECTIVE:
{req}

CONTEXT & EXAMPLES:
{examples}

RULES & ADJUSTMENTS:
{adjustments}

OUTPUT FORMAT:
{output_type}"""

        v2_sys = f"""### CHARACTER
{character}

### REQUEST
{req}

### EXAMPLES
{examples}

### ADJUSTMENTS
{adjustments}

### TYPE OF OUTPUT
{output_type}

### EXTRAS
{extras}"""

        v3_sys = f"""====================
[C] CHARACTER
====================
{character}
You must strictly maintain this persona for the duration of the request.

====================
[R] REQUEST
====================
{req}

====================
[E] EXAMPLES (CONTEXT)
====================
{examples}

====================
[A] ADJUSTMENTS & CONSTRAINTS
====================
{adjustments}
- Do not hallucinate capabilities or facts outside of your training or context.
- Assume negative space: if not told to invent, explicitly state what is missing.

====================
[T] TYPE OF OUTPUT
====================
{output_type}

====================
[E] EXTRAS
====================
{extras}
- Validate all schema objects before dispatching token stream."""

        variants = [
            PromptVariant(
                id=1,
                name="Conservative",
                strategy="Lightly structured logical alignment without heavy borders.",
                system_prompt=v1_sys.strip(),
                user_prompt="[Insert request string here]",
                token_estimate=len(v1_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=75, context=65, role=85, tone=60, execution=70),
                strengths=["Readability", "Chronological order"],
                best_for="Low-complexity logical tasks",
                overshoot_guards=[],
                undershoot_guards=[]
            ),
            PromptVariant(
                id=2,
                name="Structured",
                strategy="Full 6-pillar CREATE mapping natively assembled.",
                system_prompt=v2_sys.strip(),
                user_prompt="[Insert request string here]",
                token_estimate=len(v2_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=85, context=85, role=95, tone=80, execution=85),
                strengths=["Explicit breakdown", "Easy to debug"],
                best_for="Iterative development, teaching agents",
                overshoot_guards=["Defined 'Extras' boundaries"],
                undershoot_guards=[]
            ),
            PromptVariant(
                id=3,
                name="Advanced",
                strategy="CREATE with high-contrast borders and programmatic logic lockdowns.",
                system_prompt=v3_sys.strip(),
                user_prompt="[Insert request string here]",
                token_estimate=len(v3_sys) // 4,
                tcrte_scores=VariantTCRTEScores(task=95, context=95, role=95, tone=90, execution=95),
                strengths=["Hallucination defense", "Strong Persona Binding"],
                best_for="Persona-heavy reasoning, interactive chat applications",
                overshoot_guards=["Strict persona logic"],
                undershoot_guards=["Schema validation"]
            )
        ]
        
        model_notes = "CREATE programmatic chronological assembly complete."
        if auto_reason:
            model_notes += f" Auto-select logic: {auto_reason}"

        analysis = OptimizationAnalysis(
            detected_issues=["Mixed instructions and context lacking clear sequential execution steps."],
            model_notes=model_notes,
            framework_applied="create",
            coverage_delta="Logical pipeline established across all 6 sub-routines.",
            auto_selected_framework="create" if auto_reason else None,
            auto_reason=auto_reason
        )

        response = OptimizationResponse(
            analysis=analysis,
            techniques_applied=["CREATE Iterative Steps", "Persona Locking"],
            variants=variants
        )

        # Quality gate: critique each variant, enhance weak ones, measure real scores
        response = await self._refine_variants_with_quality_critique(
            response=response,
            raw_prompt=request.raw_prompt,
            task_type=request.task_type,
            api_key=request.api_key,
        )

        return response
