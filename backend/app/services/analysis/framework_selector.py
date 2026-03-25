"""
Deterministic Auto-Select Framework Router

Every APOST optimization session requires choosing one of eight prompt engineering
frameworks: TCRTE, KERNEL, XML Structured, Progressive, CoT Ensemble, TextGrad,
ReAct, or Reasoning-Aware. In the previous implementation this choice was delegated
to the main LLM, which received the documented decision tree as a block of natural
language instructions and was expected to interpret and apply it. The problem is
that "interpreting a decision tree" is exactly the kind of structured conditional
logic that LLMs are inconsistent at. The same session with provider=anthropic might
select "cot_ensemble" and with provider=openai select "tcrte" — not because the
decision is wrong, but because the LLM samples a slightly different reasoning path.

This module implements the exact same decision tree as deterministic Python if/elif
branches. Given the same inputs, it returns the same framework id every time, on
every run, on every machine. There is no LLM call, no latency cost, and no token
spend for this step.

The decision tree priority order (highest to lowest):
  1. Reasoning models (o-series, extended thinking) always get "reasoning_aware" —
     they have built-in chain-of-thought and do not benefit from CoT injection.
  2. QA tasks or multi-document prompts get "xml_structured" — XML bounding has the
     strongest research backing for tasks that require precise fact retrieval from
     structured or semi-structured sources.
  3. Planning and coding at complexity "complex" get "progressive" — these tasks
     benefit from staged scaffolding that builds complexity incrementally.
  4. Reasoning and analysis at complexity "complex" get "cot_ensemble" — these tasks
     benefit from few-shot CoT demonstrations (real kNN-retrieved examples via the
     Medprompt pattern) rather than zero-shot generation.
  5. Any prompt with overall TCRTE score below 50 gets "tcrte" — meaning the prompt
     itself is so underspecified that the optimizer's first job is to fill structural
     gaps before applying any stylistic framework.
  6. Simple tasks or routing/extraction tasks get "kernel" — the Kernel framework
     produces lean, tool-calling-optimized prompts with minimal overhead.
  7. Creative tasks get "create" — the Create framework prioritises originality
     signals and avoids over-constraining format.
  8. Default fallback: "textgrad" — applies the real iterative backpropagation loop
     to harden the prompt against known failure modes when no other rule fires.

Use this module for every optimization request where framework == "auto". Feed it
the outputs of the TCRTE scorer and the gap analysis complexity field.

Do NOT call this for requests where the user has explicitly selected a framework.
Respect user choice even if the auto-select logic would recommend something different.

The "auto_reason" string returned alongside the framework id is suitable for display
in the UI as "Auto-selected: XML Structured — because: multi-document source + complex"
so users understand and can learn from the selection rather than treating the tool
as a black box.
"""

import logging

logger = logging.getLogger(__name__)


def select_framework(
    is_reasoning_model: bool,
    task_type: str,
    complexity: str,
    tcrte_overall_score: int,
    provider: str,
    recommended_techniques: list[str] | None = None,
) -> tuple[str, str]:
    """
    Apply the APOST decision tree deterministically.

    Returns (framework_id, reason_string).
    framework_id is one of: reasoning_aware | xml_structured | progressive |
                             cot_ensemble | tcrte | kernel | create | textgrad
    reason_string is a short human-readable explanation suitable for UI display.
    """
    techniques = recommended_techniques or []

    # ── Priority 1: Reasoning models bypass all CoT injection ─────────────────
    if is_reasoning_model:
        return (
            "reasoning_aware",
            "Reasoning model detected — built-in chain-of-thought active, "
            "external CoT injection suppressed.",
        )

    # ── Priority 2: QA or multi-document tasks → XML Structured ───────────────
    if task_type == "qa" or any(
        t in techniques for t in ("multi-document", "xml_bounding", "structured_retrieval")
    ):
        return (
            "xml_structured",
            f"QA or multi-document task ({task_type}) — XML Structured Bounding "
            "optimises fact retrieval precision from structured sources.",
        )

    # ── Priority 3: Complex planning / coding → Progressive ───────────────────
    if task_type in ("planning", "coding") and complexity == "complex":
        return (
            "progressive",
            f"Complex {task_type} task — Progressive scaffolding builds "
            "complexity incrementally to reduce instruction-following errors.",
        )

    # ── Priority 4: Complex reasoning / analysis → CoT Ensemble ───────────────
    if task_type in ("reasoning", "analysis") and complexity in ("complex", "expert"):
        return (
            "cot_ensemble",
            f"Complex {task_type} task — CoT Ensemble injects kNN-retrieved "
            "few-shot reasoning traces (Medprompt pattern) to anchor step quality.",
        )

    # ── Priority 5: Underspecified prompt → TCRTE structural repair ───────────
    if tcrte_overall_score < 50:
        return (
            "tcrte",
            f"Overall TCRTE score is {tcrte_overall_score}/100 — structural gaps "
            "must be filled before stylistic refinement can be applied.",
        )

    # ── Priority 6: Simple / routing / extraction → Kernel ────────────────────
    if task_type in ("routing", "extraction", "classification") or complexity == "simple":
        return (
            "kernel",
            f"Simple or tool-oriented task ({task_type}, {complexity}) — Kernel "
            "framework produces lean, low-overhead prompts optimal for structured outputs.",
        )

    # ── Priority 7: Creative tasks → Create ───────────────────────────────────
    if task_type == "creative":
        return (
            "create",
            "Creative task — Create framework maximises originality signals while "
            "avoiding over-constraining format directives.",
        )

    # ── Priority 8: Default → TextGrad iterative hardening ────────────────────
    return (
        "textgrad",
        "No specific rule matched — TextGrad iterative optimization applied to "
        "harden the prompt against known failure modes.",
    )
