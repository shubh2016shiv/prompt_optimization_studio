"""
Chat API Route.

POST /api/chat - Send a message to the AI chat assistant.
"""

import structlog
from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.models.requests import ChatRequest
from app.models.responses import ChatMessage, ChatResponse
from app.observability.redaction import redact_sensitive_data
from app.observability.request_context import get_request_id
from app.services.llm_client import LLMClient, LLMClientError
from app.services.prompt_builders import build_chat_system_prompt

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    """
    Send a message to the AI chat assistant.

    The assistant has access to the full session context (raw prompt, variants,
    gap data, answers) and can help refine prompts conversationally.
    """
    settings = get_settings()
    request_id = get_request_id(http_request)
    logger.info(
        "chat.request_started",
        request_id=request_id,
        provider=request.provider,
        model_id=request.model_id,
        payload=redact_sensitive_data(request.model_dump()),
    )

    system_prompt = build_chat_system_prompt(context=request.context)

    messages = []
    for msg in request.history:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    messages.append({
        "role": "user",
        "content": request.message,
    })

    if len(messages) > 28:
        messages = messages[-28:]

    try:
        async with LLMClient(api_key=request.api_key) as client:
            response_text = await client.call_chat(
                provider=request.provider,
                messages=messages,
                system=system_prompt,
                max_tokens=settings.max_tokens_chat,
                model=request.model_id,
            )

        logger.info("chat.request_completed", request_id=request_id)
        return ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=response_text,
            )
        )

    except LLMClientError as error:
        status_code = error.status_code or 502
        logger.warning(
            "chat.llm_error",
            request_id=request_id,
            status_code=status_code,
            error=str(error),
        )
        raise HTTPException(
            status_code=status_code,
            detail=f"LLM API error: {str(error)}",
        )
    except Exception as error:
        logger.exception(
            "chat.unexpected_error",
            request_id=request_id,
            error=str(error),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(error)}",
        )
