"""
Analysis services package.

Purpose:
  Centralizes deterministic analysis utilities used by the optimization
  pipeline, including hop counting (CoRe) and framework auto-selection.
"""

from .hop_counter import count_reasoning_hops
from .framework_selector import select_framework

__all__ = ["count_reasoning_hops", "select_framework"]
