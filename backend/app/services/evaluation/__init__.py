"""
Evaluation Package — Internal Prompt Quality Critique Service

This package provides the PromptQualityCritic which acts as an internal
quality gate inside every optimization framework's generate_variants() loop.

It is NOT an API endpoint — it is an invisible internal driver that ensures
every generated prompt variant is objectively good before reaching the user.
"""

from app.services.evaluation.critique_result import CritiqueResult, DimensionScores
from app.services.evaluation.prompt_quality_critic import PromptQualityCritic

__all__ = [
    "PromptQualityCritic",
    "CritiqueResult",
    "DimensionScores",
]
