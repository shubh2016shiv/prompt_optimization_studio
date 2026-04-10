"""
Shared contracts for task-level evaluation components.

Why this module exists:
  The task-evaluation pipeline has multiple cooperating parts (deterministic
  scorer, rubric judge, pairwise judge, orchestration service). This file
  centralizes their shared internal value objects and callback signatures so
  each component can stay focused on its single responsibility.

Association with other modules:
  - Produced by:
      deterministic_scorer.py, rubric_judge.py
  - Consumed by:
      task_level_evaluation.py (orchestration)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable


CancellationCheck = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class DeterministicCaseScore:
    """
    Result returned by deterministic scoring logic for one dataset case.

    Fields:
      score:
        Deterministic score in range [0, 100].
      should_use_rubric:
        Indicates whether deterministic evidence is uncertain and rubric judging
        should be used to refine the score.
      failure_reason:
        Optional machine-readable reason when deterministic scoring identifies a
        known failure pattern.
    """

    score: int
    should_use_rubric: bool
    failure_reason: str | None


@dataclass(frozen=True)
class RubricCaseScore:
    """
    Result returned by rubric judging logic for one dataset case.

    Fields:
      score:
        Judge score in range [0, 100].
      failure_reason:
        Optional machine-readable reason provided by the judge.
    """

    score: int
    failure_reason: str | None

