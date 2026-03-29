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
    EvaluationDatasetCase,
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
    OptimizationJobCreatedResponse,
    OptimizationJobStatusResponse,
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
    "EvaluationDatasetCase",
    "ChatRequest",
    # Response types
    "TCRTEScore",
    "TCRTEScores",
    "GapQuestion",
    "GapAnalysisResponse",
    "VariantTCRTEScores",
    "PromptVariant",
    "OptimizationAnalysis",
    "OptimizationJobCreatedResponse",
    "OptimizationJobStatusResponse",
    "OptimizationResponse",
    "ChatMessage",
    "ChatResponse",
]
