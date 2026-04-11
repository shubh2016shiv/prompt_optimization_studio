"""
Normalization helpers for deterministic auto-selection inputs.

These helpers keep the public optimize request contract backward compatible while
ensuring the selector sees canonical, validated inputs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import math

_COMPLEXITY_ALIASES: dict[str, str] = {
    "simple": "simple",
    "medium": "standard",
    "standard": "standard",
    "complex": "complex",
    "expert": "expert",
}

_NON_ROUTING_TECHNIQUES = {"prefill"}

_TECHNIQUE_ALIASES: dict[str, str | None] = {
    "core": "context_repetition",
    "context_repetition": "context_repetition",
    "long_context": "context_repetition",
    "ral-writer": "constraint_restatement",
    "constraint_restatement": "constraint_restatement",
    "xml-bounding": "xml_bounding",
    "xml_bounding": "xml_bounding",
    "multi-document": "xml_bounding",
    "structured_retrieval": "xml_bounding",
    "cot-ensemble": "cot_ensemble",
    "cot_ensemble": "cot_ensemble",
    "progressive-disclosure": "progressive_disclosure",
    "progressive_disclosure": "progressive_disclosure",
    "prefill": None,
    "iterative_refinement": "empirical_optimization",
    "empirical_optimization": "empirical_optimization",
    "structure_aware": "structure_aware",
    "topological_mutation": "structure_aware",
    "prompt_compression": "structure_aware",
}


@dataclass(frozen=True)
class NormalizedAutoSelectionInput:
    """Canonical selection inputs plus debug metadata for observability."""

    tcrte_overall_score: int
    complexity: str
    recommended_techniques: list[str]
    defaults_applied: list[str] = field(default_factory=list)
    unknown_techniques: list[str] = field(default_factory=list)
    ignored_techniques: list[str] = field(default_factory=list)
    malformed_gap_data: bool = False


def normalize_complexity(value: object) -> str:
    """Map raw complexity labels to canonical selector values."""
    if not isinstance(value, str):
        return "standard"
    normalized_value = value.strip().lower()
    return _COMPLEXITY_ALIASES.get(normalized_value, "standard")


def normalize_recommended_techniques(value: object) -> list[str]:
    """Return canonical selector technique tokens in first-seen order."""
    normalized, _, _ = _normalize_recommended_techniques_with_metadata(value)
    return normalized


def normalize_gap_data_for_auto_selection(gap_data: object) -> NormalizedAutoSelectionInput:
    """Coerce raw gap_data into safe, canonical selector inputs."""
    defaults_applied: list[str] = []
    unknown_techniques: list[str] = []
    ignored_techniques: list[str] = []
    malformed_gap_data = False

    if gap_data is None:
        gap_data_mapping: Mapping[str, object] = {}
    elif isinstance(gap_data, Mapping):
        gap_data_mapping = gap_data
    else:
        gap_data_mapping = {}
        malformed_gap_data = True
        defaults_applied.extend(["overall_score", "complexity", "recommended_techniques"])

    raw_score = gap_data_mapping.get("overall_score")
    score, used_default_score = _coerce_score(raw_score)
    if used_default_score and "overall_score" not in defaults_applied:
        defaults_applied.append("overall_score")

    raw_complexity = gap_data_mapping.get("complexity")
    complexity = normalize_complexity(raw_complexity)
    if raw_complexity is None and "complexity" not in defaults_applied:
        defaults_applied.append("complexity")
    elif complexity == "standard" and raw_complexity != "standard":
        raw_complexity_normalized = raw_complexity.strip().lower() if isinstance(raw_complexity, str) else None
        if raw_complexity_normalized not in _COMPLEXITY_ALIASES and "complexity" not in defaults_applied:
            defaults_applied.append("complexity")

    raw_techniques = gap_data_mapping.get("recommended_techniques")
    techniques, unknown_techniques, ignored_techniques = _normalize_recommended_techniques_with_metadata(
        raw_techniques
    )
    if raw_techniques is None and "recommended_techniques" not in defaults_applied:
        defaults_applied.append("recommended_techniques")
    elif not isinstance(raw_techniques, list) and "recommended_techniques" not in defaults_applied:
        defaults_applied.append("recommended_techniques")

    return NormalizedAutoSelectionInput(
        tcrte_overall_score=score,
        complexity=complexity,
        recommended_techniques=techniques,
        defaults_applied=defaults_applied,
        unknown_techniques=unknown_techniques,
        ignored_techniques=ignored_techniques,
        malformed_gap_data=malformed_gap_data,
    )


def _coerce_score(value: object) -> tuple[int, bool]:
    """Safely parse overall_score and clamp to the selector's expected range."""
    parsed_score: int | None = None

    if isinstance(value, bool):
        parsed_score = None
    elif isinstance(value, int):
        parsed_score = value
    elif isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            parsed_score = int(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                parsed_score = int(stripped)
            except ValueError:
                try:
                    float_value = float(stripped)
                except ValueError:
                    parsed_score = None
                else:
                    if math.isfinite(float_value) and float_value.is_integer():
                        parsed_score = int(float_value)

    if parsed_score is None:
        return 0, True

    return max(0, min(parsed_score, 100)), False


def _normalize_recommended_techniques_with_metadata(
    value: object,
) -> tuple[list[str], list[str], list[str]]:
    """Normalize raw technique labels while tracking ignored inputs."""
    if not isinstance(value, list):
        return [], [], []

    normalized_techniques: list[str] = []
    seen_normalized: set[str] = set()
    unknown_techniques: list[str] = []
    ignored_techniques: list[str] = []

    for raw_item in value:
        raw_label = str(raw_item).strip()
        if not raw_label:
            continue

        normalized_key = raw_label.lower()
        if normalized_key in _NON_ROUTING_TECHNIQUES:
            ignored_techniques.append(raw_label)
            continue

        canonical_signal = _TECHNIQUE_ALIASES.get(normalized_key)
        if canonical_signal is None:
            unknown_techniques.append(raw_label)
            continue

        if canonical_signal not in seen_normalized:
            normalized_techniques.append(canonical_signal)
            seen_normalized.add(canonical_signal)

    return normalized_techniques, unknown_techniques, ignored_techniques
