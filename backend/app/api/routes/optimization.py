"""
Optimization API Route.

POST /api/optimize - Generate optimized prompt variants.
"""

from fastapi import APIRouter, HTTPException

from app.models.requests import OptimizationRequest
from app.models.responses import OptimizationResponse
from app.services.llm_client import LLMClient, LLMClientError
from app.services.json_extractor import extract_json_from_llm_response, JSONExtractionError
from app.services.prompt_builders import build_optimizer_prompt
from app.config import get_settings


router = APIRouter()


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_prompt(request: OptimizationRequest) -> OptimizationResponse:
    """
    Generate three optimized prompt variants.

    This endpoint takes the raw prompt, optional gap analysis data and answers,
    and generates three production-grade variants (Conservative, Structured, Advanced).
    """
    settings = get_settings()

    # Build model info dict for the prompt builder
    model_info = {
        "id": request.model_id,
        "label": request.model_label,
        "reasoning": request.is_reasoning_model,
    }

    # Build the optimizer prompt
    prompt = build_optimizer_prompt(
        raw_prompt=request.raw_prompt,
        input_variables=request.input_variables,
        framework=request.framework,
        task_type=request.task_type,
        provider=request.provider,
        model=model_info,
        is_reasoning_model=request.is_reasoning_model,
        answers=request.answers,
        gap_data=request.gap_data,
    )

    try:
        async with LLMClient(api_key=request.api_key) as client:
            response_text = await client.call_anthropic(
                prompt=prompt,
                max_tokens=settings.max_tokens_optimization,
            )

        # Extract and parse JSON from response
        parsed_response = extract_json_from_llm_response(response_text)

        # Validate and return the response
        return OptimizationResponse(**parsed_response)

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
