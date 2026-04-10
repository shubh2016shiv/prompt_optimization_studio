"""
Deterministic Auto-Select Framework Router.

Goal:
  Choose the most appropriate optimization framework without calling an LLM.
  This keeps routing fast, deterministic, and cost-free.

Inputs and where they come from:
  - task_type: Declared by the client (e.g., reasoning, planning, coding, qa).
  - complexity: Estimated by gap analysis (simple, standard, complex, expert).
  - tcrte_overall_score: A 0-100 coverage score computed earlier in the pipeline.
  - has_evaluation_dataset: Whether empirical examples are available for
    trajectory-based optimization.

What is TCRTE?
  TCRTE is APOST's structural coverage rubric for prompt quality:
    T = Task clarity
    C = Context grounding
    R = Role definition
    T = Tone and constraints
    E = Execution/format instructions
  Each dimension is scored and combined into a single overall score. Lower
  scores mean the prompt is underspecified and needs structural repair before
  stylistic refinements.

Selection philosophy:
  - Prefer specialist frameworks when a clear rule matches (reasoning models,
    QA/multi-doc, complex planning, complex reasoning).
  - Reserve TextGrad (iterative hardening) for truly complex prompts with
    materially weak TCRTE (< 50).
  - For everything else, choose a lower-cost default (kernel or progressive).

Return:
  (framework_id, reason_string) where framework_id is one of:
  reasoning_aware, xml_structured, progressive, cot_ensemble,
  tcrte, kernel, create, textgrad, overshoot_undershoot,
  core_attention, ral_writer, opro, sammo.
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
    has_evaluation_dataset: bool = False,
) -> tuple[str, str]:
    """Apply the APOST decision tree deterministically."""
    techniques = recommended_techniques or []

    if is_reasoning_model:
        return (
            "reasoning_aware",
            "Reasoning model detected - built-in chain-of-thought active, external CoT injection suppressed.",
        )

    if has_evaluation_dataset and any(
        t in techniques for t in ("iterative_refinement", "empirical_optimization")
    ):
        return (
            "opro",
            "Evaluation dataset plus empirical/iterative optimization signal detected - "
            "OPRO selected to learn from prompt-score trajectories.",
        )

    if (
        complexity in ("complex", "expert")
        and task_type in ("extraction", "qa", "analysis")
        and any(t in techniques for t in ("structure_aware", "topological_mutation", "prompt_compression"))
    ):
        return (
            "sammo",
            "Structure-aware optimization signal detected for a high-complexity task - "
            "SAMMO selected to mutate prompt topology and balance quality vs token cost.",
        )

    if task_type == "qa" or any(
        t in techniques for t in ("multi-document", "xml_bounding", "structured_retrieval")
    ):
        return (
            "xml_structured",
            f"QA or multi-document task ({task_type}) - XML Structured Bounding optimises fact retrieval precision from structured sources.",
        )

    if task_type in ("planning", "coding") and complexity == "complex":
        return (
            "progressive",
            f"Complex {task_type} task - Progressive scaffolding builds complexity incrementally to reduce instruction-following errors.",
        )

    if task_type in ("reasoning", "analysis") and complexity in ("complex", "expert"):
        return (
            "cot_ensemble",
            f"Complex {task_type} task - CoT Ensemble injects kNN-retrieved few-shot reasoning traces (Medprompt pattern) to anchor step quality.",
        )

    if complexity == "complex" and tcrte_overall_score < 50:
        return (
            "textgrad",
            f"Complex task with very low TCRTE ({tcrte_overall_score}/100) - TextGrad iterative hardening selected for recovery.",
        )

    if tcrte_overall_score < 50:
        return (
            "tcrte",
            f"Overall TCRTE score is {tcrte_overall_score}/100 - structural gaps must be filled before stylistic refinement can be applied.",
        )

    if 50 <= tcrte_overall_score < 70 and complexity in ("standard", "expert"):
        return (
            "overshoot_undershoot",
            f"Moderate TCRTE ({tcrte_overall_score}/100) with {complexity} task - "
            "prompt has basic structure but lacks failure-mode guardrails. "
            "Overshoot/Undershoot prevention calibrates scope and depth controls.",
        )

    if "context_repetition" in techniques or "long_context" in techniques:
        return (
            "core_attention",
            "High context-loss risk detected (multi-hop/long context). "
            "CoRe Attention-Aware framework selected to restructure for primacy/recency."
        )

    if "constraint_restatement" in techniques or task_type == "coding":
        return (
            "ral_writer",
            "Heavy constraint/rule reliance detected. "
            "RAL-Writer selected to isolate constraints and apply recency echo."
        )

    if task_type in ("routing", "extraction", "classification") or complexity == "simple":
        return (
            "kernel",
            f"Simple or tool-oriented task ({task_type}, {complexity}) - Kernel framework produces lean, low-overhead prompts optimal for structured outputs.",
        )

    if task_type == "creative":
        return (
            "create",
            "Creative task - Create framework maximises originality signals while avoiding over-constraining format directives.",
        )

    if complexity == "complex":
        return (
            "progressive",
            f"No specific rule matched for complex {task_type} task - Progressive selected as lower-cost default.",
        )

    return (
        "kernel",
        f"No specific rule matched for ({task_type}, {complexity}) - Kernel selected as lower-cost default.",
    )
