"""
Scoring services for APOST.
Exports the TCRTE scorer that provides structured, reproducible prompt coverage analysis.
"""

from .tcrte_scorer import score_tcrte

__all__ = ["score_tcrte"]
