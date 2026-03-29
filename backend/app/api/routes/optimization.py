"""
Optimization API Route.

POST /api/optimize - Generate optimized prompt variants.

ARCHITECTURE:
═══════════════════════════════════════════════════════════════════════════════

  ┌─────────────────────┐
  │  POST /api/optimize │
  └──────────┬──────────┘
             │
             ▼
  ┌─────────────────────┐  Step 1: FRAMEWORK RESOLUTION
  │  Framework Resolver  │  If framework == "auto", the deterministic Python
  │                      │  framework selector (framework_selector.py) picks the
  └──────────┬──────────┘  optimal framework based on task_type, complexity,
             │              TCRTE scores, and model type. No LLM call needed.
             ▼
  ┌─────────────────────┐  Step 2: CORe HOP COUNT
  │  Hop Counter         │  For frameworks that use context repetition (kernel,
  │                      │  xml_structured, cot_ensemble), estimate the number
  └──────────┬──────────┘  of reasoning hops via gpt-4.1-nano.
             │
             ▼
  ┌─────────────────────┐  Step 3: kNN FEW-SHOT RETRIEVAL
  │  kNN Retriever       │  For cot_ensemble, retrieve k=3 semantically similar
  │                      │  examples from the pre-computed corpus using Gemini
  └──────────┬──────────┘  embeddings. Falls back to LLM-generated examples.
             │
             ▼
  ┌─────────────────────┐  Step 4: STRATEGY EXECUTION
  │  OptimizerFactory    │  Factory resolves framework_id → Strategy class.
  │  → Strategy.         │  Strategy.generate_variants() runs the framework
  │    generate_variants │  algorithm and returns OptimizationResponse.
  └─────────────────────┘

DESIGN DECISIONS:
  - All 8 frameworks (including TextGrad) go through the same Strategy pattern
    pipeline. There are no separate code paths.
  - The route is a thin orchestrator: it resolves the framework, computes
    cross-cutting parameters (core_k, few_shot_examples), and delegates
    ALL framework logic to the Strategy class.
"""

import logging
import os

from fastapi import APIRouter, HTTPException, Request

from app.models.requests import OptimizationRequest
from app.models.responses import OptimizationResponse
from app.services.llm_client import LLMClientError
from app.services.json_extractor import JSONExtractionError
from app.services.analysis import select_framework, count_reasoning_hops
from app.services.optimization import retrieve_k_nearest
from app.services.optimization.base import OptimizerFactory

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_prompt(request: OptimizationRequest, http_request: Request) -> OptimizationResponse:
    """
    Generate three optimized prompt variants (Conservative, Structured, Advanced).

    This is the single unified pipeline for ALL 8 frameworks. The route handles:
      1. Auto-select resolution (if framework == "auto")
      2. CoRe hop counting (for applicable frameworks)
      3. kNN few-shot retrieval (for cot_ensemble)
      4. Strategy delegation via OptimizerFactory

    All framework-specific logic lives inside the Strategy classes, not here.
    """

    # ── Step 1: Resolve framework — deterministic selector if "auto" ──────
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

    # ── Step 2: CoRe hop count (for frameworks that use context repetition) ─
    core_k = 2  # default: start + end
    if effective_framework in ("kernel", "xml_structured", "cot_ensemble"):
        core_k = await count_reasoning_hops(
            raw_prompt=request.raw_prompt,
            api_key=request.api_key,
        )

    # ── Step 3: kNN few-shot retrieval for cot_ensemble ───────────────────
    few_shot_examples = None
    few_shot_source = "not_applicable"
    if effective_framework == "cot_ensemble":
        few_shot_source = "synthetic"
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
                if few_shot_examples:
                    few_shot_source = "knn"
        except Exception as knn_retrieval_error:
            logger.warning("kNN retrieval failed (%s); strategy will generate synthetic examples.", knn_retrieval_error)

    # ── Step 4: Strategy execution via Factory ────────────────────────────
    try:
        strategy = OptimizerFactory.get_optimizer(effective_framework)

        response = await strategy.generate_variants(
            request=request,
            core_k=core_k,
            few_shot_examples=few_shot_examples,
            auto_reason=auto_reason,
        )
        response.analysis.few_shot_source = few_shot_source

        return response

    except ValueError as framework_not_found_error:
        raise HTTPException(status_code=400, detail=str(framework_not_found_error))
    except LLMClientError as llm_error:
        status_code = llm_error.status_code or 502
        raise HTTPException(status_code=status_code, detail=f"LLM API error: {str(llm_error)}")
    except JSONExtractionError as json_error:
        raise HTTPException(status_code=502, detail=f"Failed to parse LLM response: {str(json_error)}")
    except Exception as unexpected_error:
        logger.exception("Unexpected error in optimize_prompt")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(unexpected_error)}")
