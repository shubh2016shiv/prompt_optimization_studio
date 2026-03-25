"""
Chat API Route.

POST /api/chat - Send a message to the AI chat assistant.
"""

from fastapi import APIRouter, HTTPException

from app.models.requests import ChatRequest
from app.models.responses import ChatResponse, ChatMessage
from app.services.llm_client import LLMClient, LLMClientError
from app.services.prompt_builders import build_chat_system_prompt
from app.config import get_settings


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a message to the AI chat assistant.

    The assistant has access to the full session context (raw prompt, variants,
    gap data, answers) and can help refine prompts conversationally.
    """
    settings = get_settings()

    # Build system prompt with context
    system_prompt = build_chat_system_prompt(context=request.context)

    # Build message history for the API call
    messages = []

    # Add previous messages from history
    for msg in request.history:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    # Add the new user message
    messages.append({
        "role": "user",
        "content": request.message,
    })

    # Limit history to last 28 messages to prevent context overflow
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

        return ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=response_text,
            )
        )

    except LLMClientError as e:
        status_code = e.status_code or 502
        raise HTTPException(
            status_code=status_code,
            detail=f"LLM API error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}",
        )
