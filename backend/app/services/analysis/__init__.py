"""
Analysis services package.

Purpose:
  Centralizes deterministic analysis utilities used by the optimization
  pipeline, including hop counting (CoRe) and framework auto-selection.
"""

from .hop_counter import count_reasoning_hops
from .auto_selection_normalizer import normalize_gap_data_for_auto_selection
from .framework_selector import select_framework

__all__ = ["count_reasoning_hops", "normalize_gap_data_for_auto_selection", "select_framework"]
