"""
Critique Result Data Models — Internal-Only Structures

These dataclasses represent the output of the PromptQualityCritic evaluation.
They are INTERNAL to the optimization pipeline and never cross the API boundary
directly — the API-facing equivalent is PromptQualityEvaluation in responses.py.

Using dataclasses (not Pydantic) because:
  - These never need JSON serialisation to/from HTTP
  - Lighter weight, faster construction
  - Clear separation: dataclass = internal, Pydantic = API contract
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DimensionScores:
    """
    Scores for each of the 7 quality dimensions (0–100 each).

    Each dimension is evaluated via G-Eval binary checklist decomposition:
    the judge answers ~3 binary yes/no sub-questions per dimension, then
    aggregates them into a 0–100 score.
    """

    role_clarity: int = 0
    """Does the prompt define who the model is and its expertise level?"""

    task_specificity: int = 0
    """Is the task described with enough precision to be unambiguous?"""

    constraint_completeness: int = 0
    """Are all hard constraints (format, length, forbidden content) explicit?"""

    output_format: int = 0
    """Does the prompt specify the exact output structure expected?"""

    hallucination_resistance: int = 0
    """Does the prompt guard against fabrication (cite sources, express uncertainty)?"""

    edge_case_handling: int = 0
    """Does the prompt define behaviour for missing, ambiguous, or invalid input?"""

    improvement_over_raw: int = 0
    """Is this prompt objectively better structured than the original raw prompt?"""


@dataclass
class CritiqueResult:
    """
    Complete result from a PromptQualityCritic evaluation of a single variant.

    This captures everything the critic observed: scores, weaknesses,
    actionable improvement suggestions, and the full reasoning chain
    for debugging.
    """

    overall_score: int
    """Weighted average across all 7 dimensions (0–100)."""

    dimensions: DimensionScores
    """Per-dimension breakdown."""

    weaknesses: list[str] = field(default_factory=list)
    """Specific, actionable weakness descriptions (e.g. 'No fallback for empty input')."""

    enhancement_suggestions: list[str] = field(default_factory=list)
    """Concrete suggestions for what to add or change."""

    strengths: list[str] = field(default_factory=list)
    """What the prompt already does well."""

    reasoning: str = ""
    """Full chain-of-thought reasoning from the judge (for debugging)."""

    passed_quality_gate: bool = False
    """True if overall_score >= QUALITY_GATE_THRESHOLD."""
