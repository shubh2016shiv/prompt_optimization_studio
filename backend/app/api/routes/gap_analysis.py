"""
Gap Analysis API Route.

POST /api/gap-analysis - Analyze a prompt for TCRTE coverage gaps.
"""

from fastapi import APIRouter, HTTPException

from app.models.requests import GapAnalysisRequest
from app.models.responses import GapAnalysisResponse
from app.services.llm_client import LLMClient, LLMClientError
from app.services.json_extractor import extract_json_from_llm_response, JSONExtractionError
from app.services.prompt_builders import build_gap_analysis_prompt
from app.config import get_settings


router = APIRouter()


@router.post("/gap-analysis", response_model=GapAnalysisResponse)
async def analyze_gaps(request: GapAnalysisRequest) -> GapAnalysisResponse:
    """
    Analyze a prompt for TCRTE coverage gaps.

    This endpoint sends the raw prompt to the LLM with a meta-prompt that
    performs a TCRTE coverage audit, returning scores, questions, and
    recommended techniques.
    """
    settings = get_settings()

    # Build the gap analysis prompt
    prompt = build_gap_analysis_prompt(
        raw_prompt=request.raw_prompt,
        input_variables=request.input_variables,
        task_type=request.task_type,
        provider=request.provider,
        model_label=request.model_label,
        is_reasoning_model=request.is_reasoning_model,
    )

    try:
        async with LLMClient(api_key=request.api_key) as client:
            response_text = await client.call_anthropic(
                prompt=prompt,
                max_tokens=settings.max_tokens_gap_analysis,
            )

        # Extract and parse JSON from response
        parsed_response = extract_json_from_llm_response(response_text)

        # Validate and return the response
        return GapAnalysisResponse(**parsed_response)

    except LLMClientError as e:
        status_code = e.status_code or 502
        raise HTTPException(
            status_code=status_code,
            detail=f"LLM API error: {str(e)}",
        )
    except JSONExtractionError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse LLM response: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}",
        )
