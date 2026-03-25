"""
Optimization API Route.

POST /api/optimize - Generate optimized prompt variants.

This route has three specialized code paths layered on top of the existing
meta-prompt builder:

1. framework == "auto"
   Calls the deterministic Python framework selector (framework_selector.py)
   instead of delegating the decision to the LLM. The selected framework id and
   reason string are logged and returned in the response analysis field.

2. framework == "textgrad"
   Calls the real TextGrad iterative optimization loop (textgrad_optimizer.py)
   which runs 3 forward→evaluate→gradient→update iterations. The three checkpoints
   map to Conservative / Structured / Advanced variants respectively. This is the
   only case that bypasses the standard meta-prompt builder entirely.

3. framework == "cot_ensemble"
   Retrieves k=3 semantically similar prompt examples from the curated few-shot
   corpus using Gemini Embedding API kNN (knn_retriever.py) and injects them into
   the optimizer prompt. Falls back to LLM-generated examples if kNN is unavailable.

All other frameworks use the existing meta-prompt builder path unchanged.
"""

import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException, Request

from app.models.requests import OptimizationRequest
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)
from app.services.llm_client import LLMClient, LLMClientError
from app.services.json_extractor import extract_json_from_llm_response, JSONExtractionError
from app.services.prompt_builders import build_optimizer_prompt
from app.services.analysis import select_framework, count_reasoning_hops
from app.services.optimization import run_textgrad_optimization, retrieve_k_nearest
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _textgrad_result_to_optimization_response(
    textgrad_result: dict[str, str],
    *,
    auto_reason: str | None = None,
) -> OptimizationResponse:
    """
    Map TextGrad checkpoint strings to the same list[PromptVariant] shape as the
    standard optimizer JSON path so response_model validation succeeds.
    """
    slot_keys = ("conservative", "structured", "advanced")
    names = ("Conservative", "Structured", "Advanced")
    strategies = (
        "First TextGrad iteration — targeted adjustments from TCRTE critique.",
        "Second iteration — deeper restructuring along the optimization trajectory.",
        "Third iteration — most refined checkpoint after full iterative loop.",
    )
    variants: list[PromptVariant] = []
    for i, (key, name, strategy) in enumerate(zip(slot_keys, names, strategies, strict=True), start=1):
        body = textgrad_result.get(key) or ""
        token_estimate = max(1, len(body) // 4)
        variants.append(
            PromptVariant(
                id=i,
                name=name,
                strategy=strategy,
                system_prompt=body,
                user_prompt="",
                prefill_suggestion=None,
                token_estimate=token_estimate,
                tcrte_scores=VariantTCRTEScores(
                    task=0, context=0, role=0, tone=0, execution=0
                ),
                strengths=["TCRTE-guided iterative refinement via TextGrad."],
                best_for="Prompts where multi-step critique and rewrite beats one-shot meta-prompting.",
                overshoot_guards=[],
                undershoot_guards=[],
            )
        )

    critique = (textgrad_result.get("final_loss") or "").strip()
    detected = [critique] if critique else ["No final critique text returned."]
    model_notes = (
        "Variants are TextGrad checkpoints (3 iterations); full instructions are in "
        "system_prompt (user_prompt intentionally empty). "
        "method=textgrad_iterative."
    )
    if auto_reason:
        model_notes = f"{model_notes} Auto-select: {auto_reason}"

    analysis = OptimizationAnalysis(
        detected_issues=detected,
        model_notes=model_notes,
        framework_applied="textgrad",
        coverage_delta="See three checkpoints for the optimization trajectory; scores not re-estimated post-TextGrad.",
    )
    return OptimizationResponse(
        analysis=analysis,
        techniques_applied=["TextGrad", "TCRTE-loss"],
        variants=variants,
    )


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_prompt(request: OptimizationRequest, http_request: Request) -> OptimizationResponse:
    """
    Generate three optimized prompt variants (Conservative, Structured, Advanced).
    """
    settings = get_settings()

    # ── Resolve framework: deterministic selector if "auto" ───────────────────
    effective_framework = request.framework
    auto_reason: str | None = None

    if request.framework == "auto":
        tcrte_overall = 0
        if request.gap_data and "overall_score" in request.gap_data:
            tcrte_overall = int(request.gap_data["overall_score"])

        techniques: list[str] = []
        if request.gap_data and "recommended_techniques" in request.gap_data:
            techniques = request.gap_data["recommended_techniques"]

        complexity = "standard"
        if request.gap_data and "complexity" in request.gap_data:
            complexity = request.gap_data["complexity"]

        effective_framework, auto_reason = select_framework(
            is_reasoning_model=request.is_reasoning_model,
            task_type=request.task_type,
            complexity=complexity,
            tcrte_overall_score=tcrte_overall,
            provider=request.provider,
            recommended_techniques=techniques,
        )
        logger.info("Auto-select chose framework=%s: %s", effective_framework, auto_reason)

    # ── CoRe hop count (for frameworks that use context repetition) ───────────
    core_k = 2  # default: start + end
    if effective_framework in ("core", "xml_structured", "cot_ensemble"):
        core_k = await count_reasoning_hops(
            raw_prompt=request.raw_prompt,
            api_key=request.api_key,
        )

    # ── TextGrad path: real iterative optimization loop ───────────────────────
    if effective_framework == "textgrad":
        try:
            textgrad_result = await run_textgrad_optimization(
                raw_prompt=request.raw_prompt,
                provider=request.provider,
                model_id=request.model_id,
                api_key=request.api_key,
                n_iterations=3,
            )
            return _textgrad_result_to_optimization_response(
                textgrad_result, auto_reason=auto_reason
            )
        except Exception as exc:
            logger.warning("TextGrad path failed (%s); falling back to standard builder.", exc)
            # Fall through to standard builder below

    # ── kNN few-shot retrieval for cot_ensemble ───────────────────────────────
    few_shot_examples = None
    if effective_framework == "cot_ensemble":
        try:
            corpus_state = getattr(http_request.app.state, "few_shot_corpus", None)
            google_key = os.getenv("GOOGLE_API_KEY")
            if corpus_state and google_key:
                few_shot_examples = await retrieve_k_nearest(
                    query=request.raw_prompt,
                    task_type=request.task_type,
                    google_api_key=google_key,
                    precomputed_corpus=corpus_state,
                    k=3,
                )
                logger.info("kNN retrieved %d examples for cot_ensemble.", len(few_shot_examples))
        except Exception as exc:
            logger.warning("kNN retrieval failed (%s); LLM will generate examples.", exc)

    # ── Build model info dict ─────────────────────────────────────────────────
    model_info = {
        "id": request.model_id,
        "label": request.model_label,
        "reasoning": request.is_reasoning_model,
    }

    # ── Standard meta-prompt builder path ────────────────────────────────────
    prompt = build_optimizer_prompt(
        raw_prompt=request.raw_prompt,
        input_variables=request.input_variables,
        framework=effective_framework,
        task_type=request.task_type,
        provider=request.provider,
        model=model_info,
        is_reasoning_model=request.is_reasoning_model,
        answers=request.answers,
        gap_data=request.gap_data,
        core_k=core_k,
        few_shot_examples=few_shot_examples,
    )

    try:
        async with LLMClient(api_key=request.api_key) as client:
            response_text = await client.call(
                provider=request.provider,
                prompt=prompt,
                max_tokens=settings.max_tokens_optimization,
                model=request.model_id,
            )

        parsed_response = extract_json_from_llm_response(response_text)

        # Inject auto-select metadata into the analysis field if present
        if auto_reason and isinstance(parsed_response.get("analysis"), dict):
            parsed_response["analysis"]["auto_selected_framework"] = effective_framework
            parsed_response["analysis"]["auto_reason"] = auto_reason

        return OptimizationResponse(**parsed_response)

    except LLMClientError as e:
        status_code = e.status_code or 502
        raise HTTPException(status_code=status_code, detail=f"LLM API error: {str(e)}")
    except JSONExtractionError as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse LLM response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
