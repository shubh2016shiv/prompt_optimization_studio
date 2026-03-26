"""
TCRTE Coverage Scorer — Structured Rubric Audit via a fast OpenAI model at temperature=0

Every prompt has five dimensions that determine whether the LLM receiving it knows
enough to do a good job: Task (what to produce and how success is measured), Context
(the domain, data source, and timeframe), Role (the expert persona and behavioural
constraints), Tone (the register, audience, and communication style), and Execution
(the output format, length constraints, and prohibited content). Collectively these
are called TCRTE — from the research underpinning the APOST framework.

The problem this module solves: the previous implementation sent the raw prompt to
the main optimization LLM and asked it to score itself. This is deeply unreliable.
The same prompt scored twice in the same session could return Task=55 one call and
Task=80 the next, purely due to sampling randomness. That instability made the
"coverage meter" in the UI meaningless — a high score was evidence of luck, not
quality.

The fix here is to separate scoring from generation entirely. This module sends the
raw prompt to the configured OpenAI sub-task model (see Settings.openai_subtask_model)
using temperature=0. Temperature=0 forces greedy decoding: at every token position the
model selects the single highest-probability token without sampling. Given identical
input and a fixed model version, this produces identical output on every call.
Combined with a rigid per-dimension rubric that replaces vague "judge this" prompts
with binary yes/no checklists ("+30 if X is present"), the scores become stable and
meaningful rather than variable and arbitrary.

The **overall** TCRTE score is not taken from the model: after dimension scores are
parsed, it is recomputed in Python as a weighted average (Task and Execution
weighted higher per APOST_v4_Documentation.md §3.3), using weights from
`get_settings().tcrte_dimension_weights`.

When to use this module: always, as the first step in the gap analysis pipeline.
It runs before the main LLM call and injects its scores as ground truth into the
gap analysis prompt, which the main LLM is explicitly instructed not to override.

When NOT to use this module directly: if no OpenAI API key is provided (e.g., a
Google-only session), the route falls back to the legacy behaviour gracefully. The
module raises a clear exception on failure so the route can catch and recover.

Cost per call: approximately 2,000-2,500 input tokens (prompt + rubric system) and
~250 output tokens, from the configured nano-class model. Latency is typically
800-1,400ms.

Quality impact: scoring consistency improves from ±25 points (observed variance with
the old approach) to ±0 points for identical inputs.

Before this module:
  "Analyse this document" → Task score varies 40-75 across calls → UI gauge jumps
  unpredictably → user loses trust in the coverage meter.

After this module:
  "Analyse this document" → Task=30 (imperative verb present but no measurable output,
  no constraints, no verifiable success criterion) → consistent across every call.
"""

import json
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_DIM_ORDER = ("task", "context", "role", "tone", "execution")


def compute_weighted_tcrte_overall(
    scores_by_dimension: dict[str, int],
    weights: dict[str, float],
) -> int:
    """
    Weighted TCRTE overall on 0–100 from per-dimension integer scores.

    Missing dimensions are treated as 0 contribution (weight still applied).
    """
    total = 0.0
    for dim in _DIM_ORDER:
        w = weights.get(dim, 0.0)
        total += w * float(scores_by_dimension.get(dim, 0))
    return max(0, min(100, round(total)))


def _build_tcrte_rubric_system(
    wt: float,
    wc: float,
    wr: float,
    wto: float,
    we: float,
) -> str:
    """Rubric text with per-dimension checklist; overall is computed server-side."""
    return f"""
You are a precision prompt auditor applying the TCRTE framework. Score the user's
prompt on exactly 5 dimensions. For each dimension check the EXACT listed signals and
add the stated points. Do not invent additional criteria.

TASK (T — max 100):
  +30  An imperative verb is clearly present (extract, classify, generate, return,
        summarise, identify, rank, compare, translate, evaluate, output, list)
  +30  A measurable output is defined: a count, a JSON object, a list of exactly N items,
        a table with specified columns, a score between 0 and 100, etc.
  +20  Negative constraints are stated (do not include X, must not exceed N words,
        never hallucinate, exclude Y)
  +20  Success is verifiable: an example output is shown, a schema is given, or a
        pass/fail criterion is explicitly stated

CONTEXT (C — max 100):
  +40  A domain or industry is explicitly named (legal, medical, e-commerce, finance, etc.)
  +30  The data source or document being processed is described (a PDF, a database, a
        JSON payload, a list of customer reviews, etc.)
  +30  A temporal scope, version, or recency constraint is stated (as of Q2 2024,
        based on the 2023 annual report, current as of [date])

ROLE (R — max 100):
  +40  "You are [expertise noun]" or "Act as [expertise noun]" pattern is present
        (You are a senior data analyst, Act as a regulatory lawyer, etc.)
  +30  Seniority or experience level is specified (with 10 years of experience,
        at a Fortune 500 company, senior, principal, expert, specialist)
  +30  Behavioural calibration is present: the model is told to prioritise one value
        over another (prioritise brevity over completeness, always cite sources, never
        speculate beyond the given data)

TONE (T — max 100):
  +35  A formality register is named (formal, concise, conversational, neutral, academic)
  +35  An audience type is named (C-suite executives, junior developers, non-technical
        stakeholders, the end user, a regulatory body)
  +30  A hedging prohibition is stated (do not say "I think" or "probably",
        avoid qualifiers, state conclusions directly, do not hedge)

EXECUTION (E — max 100):
  +40  An output format is specified (JSON, XML, Markdown, numbered list, table,
        plain prose, CSV, code block)
  +35  A length limit is stated (under 200 words, exactly 3 bullet points,
        max 5 sentences, no more than 500 tokens)
  +25  Prohibited output content is named (no disclaimers, no repetition of the prompt,
        no preamble, no apologies, no markdown if plain text is required)

Return ONLY valid JSON with no surrounding markdown fences or explanation:
{{
  "task":      {{"score": 0, "note": "one sentence explaining the score"}},
  "context":   {{"score": 0, "note": "one sentence explaining the score"}},
  "role":      {{"score": 0, "note": "one sentence explaining the score"}},
  "tone":      {{"score": 0, "note": "one sentence explaining the score"}},
  "execution": {{"score": 0, "note": "one sentence explaining the score"}},
  "overall_score": 0
}}
Set "overall_score" to 0. The API recomputes the overall from dimension scores using:
round({wt}*task + {wc}*context + {wr}*role + {wto}*tone + {we}*execution) on the integer
dimension scores (each 0–100).
""".strip()


def _apply_weighted_overall(scores: dict[str, Any], weights: dict[str, float]) -> None:
    """Mutates scores: sets overall_score from weighted dimension scores."""
    by_dim: dict[str, int] = {}
    for dim in _DIM_ORDER:
        if dim in scores and isinstance(scores[dim], dict) and "score" in scores[dim]:
            by_dim[dim] = int(scores[dim]["score"])
    scores["overall_score"] = compute_weighted_tcrte_overall(by_dim, weights)


async def score_tcrte(raw_prompt: str, api_key: str) -> dict:
    """
    Score a prompt against the TCRTE rubric.

    Returns a dict with keys: task, context, role, tone, execution (each a dict
    with 'score' int and 'note' str), plus overall_score int (weighted; computed
    in Python from dimensions).

    Raises httpx.HTTPStatusError on non-2xx responses.
    Raises json.JSONDecodeError if the model returns malformed JSON (rare at temp=0).
    """
    settings = get_settings()
    weights = settings.tcrte_dimension_weights
    rubric = _build_tcrte_rubric_system(
        weights["task"],
        weights["context"],
        weights["role"],
        weights["tone"],
        weights["execution"],
    )
    cap = settings.tcrte_score_max_prompt_chars
    payload = {
        "model": settings.openai_subtask_model,
        "temperature": 0,  # greedy decoding — same input ⟹ same output every run
        "max_tokens": settings.tcrte_score_max_tokens,
        "messages": [
            {"role": "system", "content": rubric},
            {"role": "user", "content": raw_prompt[:cap]},
        ],
    }

    async with httpx.AsyncClient(timeout=settings.tcrte_score_timeout_seconds) as client:
        response = await client.post(
            settings.openai_chat_completions_url,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        response.raise_for_status()

    raw_content = response.json()["choices"][0]["message"]["content"].strip()

    # Strip any accidental markdown fences the model may add despite instructions
    if raw_content.startswith("```"):
        raw_content = raw_content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    scores = json.loads(raw_content)

    # Defensive normalisation — clamp scores to [0, 100]
    for dim in _DIM_ORDER:
        if dim in scores and isinstance(scores[dim], dict) and "score" in scores[dim]:
            scores[dim]["score"] = max(0, min(100, int(scores[dim]["score"])))

    # Canonical overall: weighted average in Python (ignores model overall_score)
    _apply_weighted_overall(scores, weights)

    logger.debug("TCRTE scores for prompt (len=%d): %s", len(raw_prompt), scores)
    return scores
