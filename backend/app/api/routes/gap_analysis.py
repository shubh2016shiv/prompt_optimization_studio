"""
Gap Analysis API Route.

POST /api/gap-analysis - Analyze a prompt for TCRTE coverage gaps.

This route pre-computes TCRTE dimension scores using a dedicated gpt-4.1-nano call
at temperature=0 (deterministic/reproducible) BEFORE sending the main gap analysis
prompt to the user's chosen LLM. The pre-computed scores are injected into the prompt
as ground truth so the main LLM focuses on generating gap-interview questions and
technique recommendations rather than re-scoring coverage — which it does inconsistently.

Both the scoring call and the prompt build run concurrently via asyncio.gather to keep
latency minimal. If the scoring call fails for any reason, the route falls back
gracefully to the LLM-generated scores without surfacing an error to the user.
"""

import asyncio

import structlog
from fastapi import APIRouter, HTTPException, Request

from app.models.requests import GapAnalysisRequest
from app.models.responses import GapAnalysisResponse
from app.observability.redaction import redact_sensitive_data
from app.observability.request_context import get_request_id
from app.services.llm_client import LLMClient, LLMClientError
from app.services.json_extractor import extract_json_from_llm_response, JSONExtractionError
from app.services.prompt_builders import build_gap_analysis_prompt
from app.services.scoring import score_tcrte
from app.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/gap-analysis", response_model=GapAnalysisResponse)
async def analyze_gaps(request: GapAnalysisRequest, http_request: Request) -> GapAnalysisResponse:
    """
    Analyze a prompt for TCRTE coverage gaps.

    Returns TCRTE dimension scores (pre-computed deterministically), gap-interview
    questions, recommended optimization techniques, and complexity assessment.
    """
    settings = get_settings()
    request_id = get_request_id(http_request)
    payload = redact_sensitive_data(request.model_dump())
    logger.info(
        "gap_analysis.request_started",
        request_id=request_id,
        provider=request.provider,
        model_id=request.model_id,
        payload=payload,
    )

    # ── Step 1: Pre-compute TCRTE scores at temperature=0 (deterministic) ─────
    # Run in parallel with prompt build since neither depends on the other.
    # The scorer uses only the OpenAI key which may differ from request.api_key
    # if the user's session is Anthropic/Google — so we'll extract from the
    # request's provider context. For non-OpenAI sessions, pass the api_key as-is
    # and let score_tcrte fall back gracefully if the key is rejected.
    async def safe_score_tcrte() -> dict | None:
        try:
            return await score_tcrte(
                raw_prompt=request.raw_prompt,
                api_key=request.api_key,  # user's key; works if provider is OpenAI
            )
        except Exception as exc:
            logger.warning(
                "gap_analysis.tcrte_prescore_failed",
                request_id=request_id,
                error=str(exc),
            )
            return None

    # Build prompt and score in parallel
    precomputed_scores_task = asyncio.create_task(safe_score_tcrte())
    prompt = build_gap_analysis_prompt(
        raw_prompt=request.raw_prompt,
        input_variables=request.input_variables,
        task_type=request.task_type,
        provider=request.provider,
        model_label=request.model_label,
        is_reasoning_model=request.is_reasoning_model,
        precomputed_tcrte=None,  # will inject after scoring; builder accepts None gracefully
    )

    precomputed_scores = await precomputed_scores_task
    tcrte_scores_source = (
        "openai_deterministic" if precomputed_scores is not None else "model_estimated"
    )

    # If we have pre-computed scores, rebuild the prompt with them injected
    if precomputed_scores:
        prompt = build_gap_analysis_prompt(
            raw_prompt=request.raw_prompt,
            input_variables=request.input_variables,
            task_type=request.task_type,
            provider=request.provider,
            model_label=request.model_label,
            is_reasoning_model=request.is_reasoning_model,
            precomputed_tcrte=precomputed_scores,
        )

    # ── Step 2: Main LLM call — generates questions and recommendations ────────
    try:
        async with LLMClient(api_key=request.api_key) as client:
            response_text = await client.call(
                provider=request.provider,
                prompt=prompt,
                max_tokens=settings.max_tokens_gap_analysis,
                model=request.model_id,
            )

        parsed_response = extract_json_from_llm_response(response_text)

        # ── Step 3: Merge pre-computed scores into response ────────────────────
        # GapAnalysisResponse expects "tcrte" with nested {score, status, note} per dimension
        # (see gap_analysis_builder JSON schema). Pre-computed scores override numeric scores
        # and per-dimension notes from score_tcrte; overall_score always from precomputed when present.
        if precomputed_scores and "tcrte" in parsed_response and isinstance(parsed_response["tcrte"], dict):
            tcrte = parsed_response["tcrte"]
            for dim in ("task", "context", "role", "tone", "execution"):
                pre_dim = precomputed_scores.get(dim)
                if not isinstance(pre_dim, dict):
                    continue
                new_score = pre_dim.get("score", 0)
                pre_note = pre_dim.get("note", "")
                if dim not in tcrte or not isinstance(tcrte[dim], dict):
                    tcrte[dim] = {"score": new_score, "status": "weak", "note": pre_note or ""}
                else:
                    tcrte[dim]["score"] = new_score
                    if pre_note:
                        tcrte[dim]["note"] = pre_note
            parsed_response["overall_score"] = precomputed_scores.get(
                "overall_score", parsed_response.get("overall_score", 0)
            )
        elif precomputed_scores:
            # LLM omitted "tcrte"; synthesize minimal structure from rubric output
            parsed_response["tcrte"] = {}
            for dim in ("task", "context", "role", "tone", "execution"):
                pre_dim = precomputed_scores.get(dim, {})
                if isinstance(pre_dim, dict):
                    parsed_response["tcrte"][dim] = {
                        "score": pre_dim.get("score", 0),
                        "status": "weak",
                        "note": pre_dim.get("note", ""),
                    }
            parsed_response["overall_score"] = precomputed_scores.get(
                "overall_score", parsed_response.get("overall_score", 0)
            )

        parsed_response["tcrte_scores_source"] = tcrte_scores_source
        logger.info("gap_analysis.request_completed", request_id=request_id)
        return GapAnalysisResponse(**parsed_response)

    except LLMClientError as e:
        status_code = e.status_code or 502
        logger.warning(
            "gap_analysis.llm_error",
            request_id=request_id,
            status_code=status_code,
            error=str(e),
        )
        raise HTTPException(status_code=status_code, detail=f"LLM API error: {str(e)}")
    except JSONExtractionError as e:
        logger.warning(
            "gap_analysis.json_parse_error",
            request_id=request_id,
            error=str(e),
        )
        raise HTTPException(status_code=502, detail=f"Failed to parse LLM response: {str(e)}")
    except Exception as e:
        logger.exception(
            "gap_analysis.unexpected_error",
            request_id=request_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
