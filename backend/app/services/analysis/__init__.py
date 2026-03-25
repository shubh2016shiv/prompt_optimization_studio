"""
Analysis services for APOST.
Exports the hop counter (CoRe adaptive k) and the deterministic framework selector.
"""

from .hop_counter import count_reasoning_hops
from .framework_selector import select_framework

__all__ = ["count_reasoning_hops", "select_framework"]
