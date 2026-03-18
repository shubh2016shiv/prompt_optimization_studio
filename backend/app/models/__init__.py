"""Pydantic models for request/response validation."""

from app.models.providers import (
    PROVIDERS,
    FRAMEWORKS,
    TASK_TYPES,
    TCRTE_DIMENSIONS,
    QUICK_ACTIONS,
    Provider,
    Model,
    Framework,
    TaskType,
    TCRTEDimension,
    QuickAction,
)
from app.models.requests import (
    GapAnalysisRequest,
    OptimizationRequest,
    ChatRequest,
)
from app.models.responses import (
    TCRTEScore,
    TCRTEScores,
    GapQuestion,
    GapAnalysisResponse,
    VariantTCRTEScores,
    PromptVariant,
    OptimizationAnalysis,
    OptimizationResponse,
    ChatMessage,
    ChatResponse,
)

__all__ = [
    # Static data
    "PROVIDERS",
    "FRAMEWORKS",
    "TASK_TYPES",
    "TCRTE_DIMENSIONS",
    "QUICK_ACTIONS",
    # Provider types
    "Provider",
    "Model",
    "Framework",
    "TaskType",
    "TCRTEDimension",
    "QuickAction",
    # Request types
    "GapAnalysisRequest",
    "OptimizationRequest",
    "ChatRequest",
    # Response types
    "TCRTEScore",
    "TCRTEScores",
    "GapQuestion",
    "GapAnalysisResponse",
    "VariantTCRTEScores",
    "PromptVariant",
    "OptimizationAnalysis",
    "OptimizationResponse",
    "ChatMessage",
    "ChatResponse",
]
