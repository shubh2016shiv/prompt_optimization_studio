"""
Scoring services for APOST.
Exports the TCRTE scorer that provides structured, reproducible prompt coverage analysis.
"""

from .tcrte_scorer import compute_weighted_tcrte_overall, score_tcrte

__all__ = ["compute_weighted_tcrte_overall", "score_tcrte"]
