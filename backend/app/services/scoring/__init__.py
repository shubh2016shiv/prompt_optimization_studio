"""
Scoring services for APOST.

Purpose:
  Expose the TCRTE scorer used to quantify prompt coverage across
  Task, Context, Role, Tone, and Execution dimensions.
"""

from .tcrte_scorer import compute_weighted_tcrte_overall, score_tcrte

__all__ = ["compute_weighted_tcrte_overall", "score_tcrte"]
