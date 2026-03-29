"""
Shared Enhancement Utilities for APOST Optimization Frameworks

These pure-function utilities implement the cross-cutting techniques documented in
APOST_v4_Documentation.md §5 that can be applied by ANY framework optimizer.
Extracting them here follows the Single Responsibility Principle — each optimizer
focuses on its own framework logic and calls these utilities for shared behaviour.

┌──────────────────────────────────────────────────────────────────────────────────┐
│                    Enhancement Pipeline (Applied Per Variant)                    │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  1. integrate_gap_interview_answers_into_prompt()                                │
│     Merges user's gap-interview answers into the raw prompt BEFORE component     │
│     extraction. This ensures the LLM parser sees the enriched prompt.            │
│                                                                                  │
│  2. inject_input_variables_block()                                               │
│     Appends the user-declared {{variables}} as a properly fenced block.          │
│                                                                                  │
│  3. inject_context_repetition_at_attention_positions()                           │
│     Applies CoRe (Liu et al., 2023) — repeating critical context at k            │
│     evenly-spaced positions to combat the "lost in the middle" U-curve.          │
│                                                                                  │
│  4. apply_ral_writer_constraint_restatement()                                    │
│     RAL-Writer Restate (APOST §5.2) — echoes middle-zone constraints at the     │
│     end of the prompt so they land in the recency attention zone.                │
│                                                                                  │
│  5. generate_claude_prefill_suggestion()                                         │
│     Claude Prefill (APOST §5.3) — returns the ideal first tokens to lock        │
│     output format for Anthropic models.                                          │
│                                                                                  │
│  6. format_prompt_for_target_provider()                                          │
│     Provider-aware formatting: XML for Claude/Gemini, Markdown for OpenAI.       │
│                                                                                  │
│  7. compute_coverage_delta_description()                                         │
│     Calculates "Coverage improved from X% → Y%" string.                         │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘

Usage example inside any framework optimizer:
    from app.services.optimization.enhancements import (
        integrate_gap_interview_answers_into_prompt,
        inject_context_repetition_at_attention_positions,
        generate_claude_prefill_suggestion,
    )
"""

import logging
from typing import Optional

from app.services.optimization.optimizer_configuration import (
    CORE_MINIMUM_REPETITION_COUNT,
    CORE_MAXIMUM_REPETITION_COUNT,
    PREFILL_SUGGESTION_BY_TASK_TYPE,
    PREFILL_DEFAULT,
    PROVIDER_FORMATTING_RULES,
    PROVIDER_FORMATTING_DEFAULT,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Gap Interview Answer Integration
# ══════════════════════════════════════════════════════════════════════════════

def integrate_gap_interview_answers_into_prompt(
    raw_prompt: str,
    gap_interview_answers: Optional[dict[str, str]],
    gap_analysis_data: Optional[dict],
) -> str:
    """
    Merge the user's gap-interview answers into the raw prompt text.

    The gap analysis phase generates questions like "What domain is this for?"
    and the user answers "Cardiology — cardiac catheterisation reporting".
    This function takes those answers and weaves them into the prompt so that
    subsequent component extraction captures the enriched context.

    Step 1: If no answers are provided, return the raw prompt unchanged.
    Step 2: Group answers by their TCRTE dimension (if gap_analysis_data
            contains question metadata with dimension info).
    Step 3: Append a structured "ADDITIONAL CONTEXT FROM USER" section to
            the raw prompt with all answers organised by dimension.

    Args:
        raw_prompt: The original user prompt.
        gap_interview_answers: Dict of question_text → answer_text from the
                               gap interview UI. May be None if user skipped.
        gap_analysis_data: The full gap analysis response dict, containing
                           TCRTE scores and question metadata. May be None.

    Returns:
        Enriched prompt string with answers integrated.
    """
    if not gap_interview_answers:
        return raw_prompt

    # Build the enrichment block
    enrichment_lines = ["\n\n--- ADDITIONAL CONTEXT (from gap interview) ---"]
    for question_text, answer_text in gap_interview_answers.items():
        if answer_text and answer_text.strip():
            enrichment_lines.append(f"Q: {question_text}")
            enrichment_lines.append(f"A: {answer_text}")
            enrichment_lines.append("")  # blank separator

    if len(enrichment_lines) <= 1:
        # All answers were empty
        return raw_prompt

    enriched_prompt = raw_prompt + "\n".join(enrichment_lines)
    logger.debug(
        "Integrated %d gap-interview answers into prompt (was %d chars, now %d chars)",
        len(gap_interview_answers),
        len(raw_prompt),
        len(enriched_prompt),
    )
    return enriched_prompt


# ══════════════════════════════════════════════════════════════════════════════
# 2. Input Variables Injection
# ══════════════════════════════════════════════════════════════════════════════

def inject_input_variables_block(
    system_prompt: str,
    input_variables: Optional[str],
    provider: str,
) -> str:
    """
    Append the user-declared input variables as a properly fenced block.

    Variables like '{{documents}} - array of PDFs' need to be visible in the
    generated system prompt so the LLM knows what dynamic data will be injected
    at runtime.

    Args:
        system_prompt: The assembled system prompt text.
        input_variables: User-declared template variables, e.g. '{{patient_data}} - FHIR bundle'.
        provider: The target LLM provider for format selection.

    Returns:
        System prompt with variables block appended (or unchanged if no variables).
    """
    if not input_variables or not input_variables.strip():
        return system_prompt

    provider_rules = PROVIDER_FORMATTING_RULES.get(provider, PROVIDER_FORMATTING_DEFAULT)

    if provider_rules["delimiter_style"] == "xml":
        variables_block = f"\n<input_variables>\n{input_variables.strip()}\n</input_variables>"
    else:
        variables_block = f"\n### Input Variables\n{input_variables.strip()}"

    return system_prompt + variables_block


# ══════════════════════════════════════════════════════════════════════════════
# 3. CoRe — Context Repetition at Attention-Favorable Positions
#    Reference: Liu et al., 2023. "Lost in the Middle: How Language Models
#    Use Long Contexts." Up to 26% accuracy improvement on multi-hop tasks.
# ══════════════════════════════════════════════════════════════════════════════

def inject_context_repetition_at_attention_positions(
    prompt_text: str,
    critical_context_to_repeat: str,
    repetition_count_k: int,
) -> str:
    """
    Insert critical context at k evenly-spaced positions throughout the prompt.

    The "lost in the middle" phenomenon means transformers pay most attention to
    tokens at the START and END of their input window; tokens in the middle get
    down-weighted. CoRe mitigates this by repeating the critical context at
    strategically spaced positions so that regardless of where the model is
    attending, a high-attention copy is always nearby.

    Step 1: Clamp k to [CORE_MINIMUM, CORE_MAXIMUM] for safety.
    Step 2: If k == 2, place critical context at START and END only.
    Step 3: If k > 2, split prompt into (k-1) segments and insert
            critical context at each boundary.
    Step 4: Mark each repetition with a [CoRe #{n}] tag for debuggability.

    Args:
        prompt_text: The full prompt or system prompt to augment.
        critical_context_to_repeat: The essential information that must not
                                     be lost (e.g. "Patient is on warfarin").
        repetition_count_k: Number of insertion points (from hop_counter).

    Returns:
        Augmented prompt with CoRe repetitions injected.
    """
    if not critical_context_to_repeat or not critical_context_to_repeat.strip():
        return prompt_text

    bounded_k = max(
        CORE_MINIMUM_REPETITION_COUNT,
        min(int(repetition_count_k), CORE_MAXIMUM_REPETITION_COUNT),
    )

    core_marker = f"\n[CoRe — Critical Context Reminder]\n{critical_context_to_repeat.strip()}\n"

    if bounded_k <= 2:
        # Simple: prepend + append
        return core_marker + prompt_text + core_marker

    # Split into (k-1) segments and insert at each boundary
    lines = prompt_text.split("\n")
    if len(lines) < bounded_k:
        # Prompt is too short to meaningfully split; just prepend + append
        return core_marker + prompt_text + core_marker

    segment_size = len(lines) // (bounded_k - 1)
    augmented_lines: list[str] = []

    for segment_index in range(bounded_k - 1):
        start_line = segment_index * segment_size
        end_line = (
            (segment_index + 1) * segment_size
            if segment_index < bounded_k - 2
            else len(lines)
        )
        augmented_lines.extend(lines[start_line:end_line])
        # Insert CoRe marker between segments (not after the last one)
        if segment_index < bounded_k - 2:
            augmented_lines.append(f"\n[CoRe #{segment_index + 2}/{bounded_k}]\n{critical_context_to_repeat.strip()}\n")

    # Always add at the very end (recency position)
    augmented_lines.append(f"\n[CoRe #{bounded_k}/{bounded_k} — Recency Echo]\n{critical_context_to_repeat.strip()}\n")

    logger.debug("CoRe injection: k=%d, inserted %d context repetitions", bounded_k, bounded_k - 1)
    return "\n".join(augmented_lines)


# ══════════════════════════════════════════════════════════════════════════════
# 4. RAL-Writer — Constraint Restatement in Recency Zone
#    Reference: APOST_v4_Documentation.md §5.2
# ══════════════════════════════════════════════════════════════════════════════

def apply_ral_writer_constraint_restatement(
    system_prompt: str,
    critical_constraints_to_echo: list[str],
    provider: str,
) -> str:
    """
    Echo critical constraints at the END of the system prompt.

    The RAL-Writer technique places constraints that are "lost in the middle"
    into the recency zone (last 10-15% of the prompt) where attention weights
    are highest. This is especially effective for Anthropic models which show
    strong recency bias.

    Step 1: If no constraints are provided, return unchanged.
    Step 2: Build a restate block appropriate for the provider's format.
    Step 3: Append to the end of the system prompt.

    Args:
        system_prompt: The full system prompt to augment.
        critical_constraints_to_echo: List of constraint strings to echo.
        provider: Target provider for format selection.

    Returns:
        System prompt with constraint restatement appended.
    """
    if not critical_constraints_to_echo:
        return system_prompt

    constraints_text = "\n".join(f"- {constraint}" for constraint in critical_constraints_to_echo)

    provider_rules = PROVIDER_FORMATTING_RULES.get(provider, PROVIDER_FORMATTING_DEFAULT)

    if provider_rules["delimiter_style"] == "xml":
        restate_block = (
            f"\n\n<restate_critical>\n"
            f"REMINDER — The following constraints MUST be honoured:\n"
            f"{constraints_text}\n"
            f"</restate_critical>"
        )
    else:
        restate_block = (
            f"\n\n---\n"
            f"**REMINDER — Critical Constraints:**\n"
            f"{constraints_text}\n"
            f"---"
        )

    return system_prompt + restate_block


# ══════════════════════════════════════════════════════════════════════════════
# 5. Claude Prefill Suggestion Generator
#    Reference: APOST_v4_Documentation.md §5.3
# ══════════════════════════════════════════════════════════════════════════════

def generate_claude_prefill_suggestion(
    task_type: str,
    provider: str,
) -> Optional[str]:
    """
    Generate the ideal first tokens to pre-fill the assistant turn for Claude.

    Anthropic's Claude supports "prefilling" — injecting the first few tokens
    of the assistant's response to structurally lock the output format. For
    example, pre-filling with "{" forces JSON output.

    Step 1: Check if the provider is Anthropic (only Claude supports prefill).
    Step 2: Look up the task_type in the prefill mapping table.
    Step 3: Return the suggestion or None if not applicable.

    Args:
        task_type: The task type selected by the user (e.g. "extraction", "qa").
        provider: The target LLM provider.

    Returns:
        Prefill string or None if not applicable.
    """
    if provider != "anthropic":
        return None

    suggestion = PREFILL_SUGGESTION_BY_TASK_TYPE.get(task_type, PREFILL_DEFAULT)
    if not suggestion:
        return None

    return suggestion


# ══════════════════════════════════════════════════════════════════════════════
# 6. Provider-Aware System Prompt Formatting
#    Reference: APOST_v4_Documentation.md §6
# ══════════════════════════════════════════════════════════════════════════════

def format_section_for_target_provider(
    section_name: str,
    section_content: str,
    provider: str,
) -> str:
    """
    Format a single section (e.g. "TASK", "CONSTRAINTS") for the target provider.

    - Anthropic/Google → XML: <task>content</task>
    - OpenAI Standard  → Markdown: ### TASK\\ncontent

    Args:
        section_name: The section label (e.g. "task", "constraints").
        section_content: The text content of the section.
        provider: Target LLM provider.

    Returns:
        Formatted section string.
    """
    provider_rules = PROVIDER_FORMATTING_RULES.get(provider, PROVIDER_FORMATTING_DEFAULT)
    template = provider_rules["section_header_format"]
    return template.format(name=section_name, content=section_content)


# ══════════════════════════════════════════════════════════════════════════════
# 7. Coverage Delta Description
# ══════════════════════════════════════════════════════════════════════════════

def compute_coverage_delta_description(
    pre_optimisation_gap_data: Optional[dict],
    post_optimisation_overall_score_estimate: Optional[int],
) -> str:
    """
    Compute a human-readable coverage improvement string.

    Example output: "Coverage improved from 35% → 82% after gap answers
    and KERNEL structural enforcement."

    Step 1: Extract overall_score from gap_data (pre-optimisation).
    Step 2: If post score is available, compute the delta.
    Step 3: Return formatted string.

    Args:
        pre_optimisation_gap_data: The gap analysis data from the request.
        post_optimisation_overall_score_estimate: Estimated score of the
                                                   optimised variant (may be None).

    Returns:
        A string like "Coverage improved from X% → Y%".
    """
    pre_score = None
    if pre_optimisation_gap_data and "overall_score" in pre_optimisation_gap_data:
        pre_score = int(pre_optimisation_gap_data["overall_score"])

    if pre_score is not None and post_optimisation_overall_score_estimate is not None:
        return f"Coverage improved from {pre_score}% → {post_optimisation_overall_score_estimate}% after optimisation."

    if pre_score is not None:
        return f"Pre-optimisation coverage was {pre_score}%. Structural enforcement applied."

    return "Structural optimisation applied. Pre-optimisation scores were not available."


# ══════════════════════════════════════════════════════════════════════════════
# 8. Bullet List Formatter (used by multiple frameworks)
# ══════════════════════════════════════════════════════════════════════════════

def format_list_as_bullet_points(items: list[str]) -> str:
    """
    Format a list of strings as markdown-style bullet points.

    Returns "- None specified." if the list is empty, ensuring the prompt
    never has a missing section.
    """
    if not items:
        return "- None specified."
    return "\n".join(f"- {item}" for item in items)
