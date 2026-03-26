# TCRTE scoring (`tcrte_scorer.py`)

This document explains the **TCRTE scorer** in plain terms: what problem it solves, how it fits into APOST, how data flows through the system, and how **prompt optimization** uses its output—even if you are new to LLM “scoring” or prompt engineering.

---

## Overview

### What is “scoring” here?

In many apps, a language model is asked to **both** write text and **judge** that text in the same call. That sounds efficient, but the judge part is unstable: small randomness in decoding can change numeric scores a lot from one run to the next. For a **coverage meter** (a single number that should reflect how complete your instructions are), that noise destroys trust.

**TCRTE scoring** is a separate step that only answers: *“How well does this prompt specify five structural ingredients?”* Those ingredients are:

| Letter | Dimension   | Plain-language meaning |
|--------|---------------|-------------------------|
| **T**  | **Task**      | What to produce and how success is measured |
| **C**  | **Context**   | Domain, data sources, time scope |
| **R**  | **Role**      | Who the model should act as |
| **Tone** | **Tone**    | Audience and style |
| **E**  | **Execution** | Output format, length limits, forbidden content |

Each dimension gets an integer **0–100**. An **overall score** (also 0–100) summarizes coverage; **Task** and **Execution** count more toward that overall than the other three, because they track reliability and testability in production.

### What this module does

[`tcrte_scorer.py`](tcrte_scorer.py) exposes **`score_tcrte(raw_prompt, api_key)`**: one HTTP call to OpenAI’s Chat Completions API using:

- A fixed **rubric** (checklist-style rules per dimension).
- **`temperature = 0`** (greedy decoding) so the same input tends to produce the same dimension scores.
- **Post-processing in Python**: dimension scores are clamped to 0–100, and **`overall_score` is always recomputed** as a **weighted average** using weights from [`app.config.Settings`](../../config.py)—not whatever number the model might put in the JSON.

So: the model proposes **per-dimension scores and short notes**; the server owns the **overall** number.

### What this module does *not* do

- It does **not** rewrite your prompt.
- It does **not** choose an optimization framework (that happens later, in Python, using gap-analysis results).
- It does **not** guarantee identical outputs on every request if the remote API or model version changes; it **does** separate scoring from your main “gap analysis” model so the UI is far more stable than self-scoring.

---

## Architecture & Wiring

### Files in this package

| File | Role |
|------|------|
| [`tcrte_scorer.py`](tcrte_scorer.py) | Implements `score_tcrte`, `compute_weighted_tcrte_overall`, and the rubric builder. |
| [`__init__.py`](__init__.py) | Public exports: `score_tcrte`, `compute_weighted_tcrte_overall`. |

### Configuration (single source of truth)

All tunable knobs for this scorer live in **[`app/config.py`](../../config.py)** (`Settings`):

- **`openai_subtask_model`** — fast OpenAI model id (default `gpt-4.1-nano`).
- **`openai_chat_completions_url`**, **`tcrte_score_max_tokens`**, **`tcrte_score_timeout_seconds`**, **`tcrte_score_max_prompt_chars`** — request shape and safety caps.
- **`tcrte_weight_task` … `tcrte_weight_execution`** — must sum to **1.0**; exposed as **`tcrte_dimension_weights`**.

[`optimizer_configuration.py`](../optimization/optimizer_configuration.py) reuses the same model and weight map via `get_settings()` so optimizers and the scorer never drift apart.

### Where `score_tcrte` is called

**Direct import (production path):**

- **[`app/api/routes/gap_analysis.py`](../../api/routes/gap_analysis.py)** — `POST /api/gap-analysis`  
  This is the **only** API route that calls `score_tcrte`. It runs the scorer **before** the main gap-analysis LLM call, then **merges** the rubric output into the JSON returned to the client.

**Indirect use in optimization:**

- **[`app/api/routes/optimization.py`](../../api/routes/optimization.py)** does **not** import `score_tcrte`. The client sends **`gap_data`** from a previous gap-analysis response (including `overall_score` and per-dimension `tcrte`). When `framework == "auto"`, **`select_framework`** in [`framework_selector.py`](../analysis/framework_selector.py) reads **`tcrte_overall_score`** from that payload (e.g. to pick the **TCRTE** framework when overall is below 50).

So the chain is: **scorer → gap analysis response → stored gap_data → optimize request → auto-select / optimizers**.

### Prompt builders

[`gap_analysis_builder.py`](../prompt_builders/gap_analysis_builder.py) injects precomputed scores into the meta-prompt as **ground truth** so the main model focuses on questions and recommendations, not re-inventing unstable scores.

---

## Scoring mechanism (step-by-step algorithm)

Below is the **logical** sequence implemented in `score_tcrte` (read the source for exact details).

1. **Load settings**  
   `get_settings()` supplies model name, URL, timeouts, max prompt length, and dimension weights.

2. **Build the system message**  
   A long instruction string defines the TCRTE rubric: for each dimension, **add points** for specific signals (e.g. imperative verb present, JSON format specified). The model is told to return **only JSON** with keys `task`, `context`, `role`, `tone`, `execution`, each `{ "score": int, "note": str }`, plus a placeholder `overall_score` (it will be overwritten).

3. **Truncate user content**  
   The raw `raw_prompt` is trimmed to **`tcrte_score_max_prompt_chars`** (default 2000) to avoid huge payloads.

4. **Call OpenAI Chat Completions**  
   `POST` to `openai_chat_completions_url` with `temperature: 0`, `max_tokens` from settings, **no streaming** in this path.

5. **Parse assistant text**  
   Strip optional markdown fences (` ``` `) if the model wraps JSON.

6. **`json.loads`** into a Python dict.

7. **Clamp each dimension score**  
   For each of `task`, `context`, `role`, `tone`, `execution`, clamp `score` to **[0, 100]**.

8. **Recompute `overall_score` in Python**  
   `compute_weighted_tcrte_overall` applies **`tcrte_dimension_weights`** (defaults: Task 0.25, Context/Role/Tone 0.15 each, Execution 0.30). Result is clamped to **[0, 100]** and stored in `scores["overall_score"]`.

9. **Return** the dict to the caller (gap analysis route).

**Why recompute the overall?**  
The rubric model might still output an `overall_score` field; the server **replaces** it so the number always matches the weighted formula and cannot disagree with the dimension scores.

---

## Usage examples

These snippets are **illustrative** (simplified imports and structure). They match how the app is wired.

### 1. How gap analysis invokes the scorer (actual backend pattern)

The route starts scoring in parallel with building the first prompt, awaits scores, optionally rebuilds the prompt with **ground-truth** TCRTE JSON, then calls the user’s LLM and merges scores.

```python
# Conceptual excerpt — see app/api/routes/gap_analysis.py for the full route.

import asyncio
from app.services.scoring import score_tcrte
from app.services.prompt_builders import build_gap_analysis_prompt

async def analyze_gaps(request):
    async def safe_score_tcrte():
        try:
            # Same OpenAI key the user sent; OpenAI sessions work.
            # Other providers may fail here → return None → LLM fallback.
            return await score_tcrte(
                raw_prompt=request.raw_prompt,
                api_key=request.api_key,
            )
        except Exception:
            return None

    precomputed_task = asyncio.create_task(safe_score_tcrte())
    prompt = build_gap_analysis_prompt(..., precomputed_tcrte=None)
    precomputed = await precomputed_task

    if precomputed:
        prompt = build_gap_analysis_prompt(..., precomputed_tcrte=precomputed)

    # ... LLMClient.call(...), extract_json_from_llm_response(...)
    # ... merge precomputed dimension scores + overall_score into parsed JSON
```

### 2. How optimization uses TCRTE scores (no direct `score_tcrte` call)

Optimization does **not** call the scorer again. It consumes **`gap_data`** the client already has from gap analysis:

```python
# Conceptual excerpt — see app/api/routes/optimization.py

from app.services.analysis import select_framework

if request.framework == "auto":
    tcrte_overall = 0
    if request.gap_data and "overall_score" in request.gap_data:
        tcrte_overall = int(request.gap_data["overall_score"])

    complexity = request.gap_data.get("complexity", "standard") if request.gap_data else "standard"
    techniques = request.gap_data.get("recommended_techniques", []) if request.gap_data else []

    effective_framework, reason = select_framework(
        is_reasoning_model=request.is_reasoning_model,
        task_type=request.task_type,
        complexity=complexity,
        tcrte_overall_score=tcrte_overall,
        provider=request.provider,
        recommended_techniques=techniques,
    )
```

When `tcrte_overall_score < 50`, auto-select can choose the **`tcrte`** optimizer so the pipeline **prioritizes structural coverage** before heavy stylistic frameworks.

### 3. Calling the scorer from tests or scripts

```python
import asyncio
from app.services.scoring import score_tcrte, compute_weighted_tcrte_overall
from app.config import get_settings

async def main():
    raw = "Summarize the attached document."
    api_key = "sk-..."  # user's OpenAI key
    result = await score_tcrte(raw, api_key)
    # result["task"]["score"], ..., result["overall_score"]
    w = get_settings().tcrte_dimension_weights
    assert result["overall_score"] == compute_weighted_tcrte_overall(
        {d: result[d]["score"] for d in ("task", "context", "role", "tone", "execution")},
        w,
    )

asyncio.run(main())
```

---

## Visual ASCII diagram (data flow)

```
  User raw prompt
        |
        v
+------------------+     +-------------------------+
|  score_tcrte()   |     | build_gap_analysis_     |
|  (OpenAI nano,   |     | prompt (first pass)     |
|   temp=0)        |     | precomputed_tcrte=None  |
+--------+---------+     +------------+------------+
         |                            |
         |         await scorer        |
         +------------+----------------+
                      |
                      v
            +---------------------+
            | Rebuild gap prompt  |
            | with PRE-COMPUTED   |
            | TCRTE scores        |
            +----------+----------+
                       |
                       v
            +---------------------+
            | Main LLM (user's    |
            | provider/model)     |
            | gap questions, etc. |
            +----------+----------+
                       |
                       v
            +---------------------+
            | Merge: rubric scores|
            | override LLM scores |
            +----------+----------+
                       |
                       v
              GapAnalysisResponse
              (tcrte + overall_score)
                       |
                       |  client stores as gap_data
                       v
            +---------------------+
            | POST /api/optimize  |
            | framework=="auto"   |
            +----------+----------+
                       |
                       v
            +---------------------+
            | select_framework(   |
            |  tcrte_overall_     |
            |  score from gap_data|
            +----------+----------+
                       |
                       v
            OptimizerFactory / strategy
            (prompt variants)
```

---

## Best practices & testing notes

### Operational

- **OpenAI key**: The scorer uses the **request’s** API key. If the user only has a non-OpenAI key, the scorer call typically fails; the gap route **catches** that and falls back to LLM-generated TCRTE scores—no hard crash for the user.
- **Do not rely on the model’s `overall_score` field** in client code; always use the **`overall_score` after server merge** from gap analysis (which matches the Python weighted formula when pre-scoring succeeded).
- **Tune weights and limits** only via [`Settings`](../../config.py) / environment variables so behavior stays consistent with [`optimizer_configuration.py`](../optimization/optimizer_configuration.py).

### Testing

- Automated tests live in **[`backend/tests/test_tcrte_scorer.py`](../../../tests/test_tcrte_scorer.py)**. They include:
  - **No-network** checks that **`compute_weighted_tcrte_overall`** matches configured weights.
  - **Integration** calls to `score_tcrte` (require a valid **`OPENAI_API_KEY`** in the environment).
  - Assertions that each live response’s **`overall_score`** equals the weighted sum of dimension scores (the invariant the server guarantees).

### When you change the rubric

If you edit checklist text in `_build_tcrte_rubric_system`, re-run tests and expect **dimension scores** to shift; **`overall_score`** will still follow the same Python formula after clamping.

---

## Glossary

- **Rubric** — A fixed checklist of observable signals and point values, instead of “rate this prompt from 1–10.”
- **Greedy decoding (`temperature = 0`)** — At each token, pick the single most likely next token; reduces randomness versus sampling.
- **Ground truth (in gap analysis)** — Precomputed scores injected into the prompt so the main model does not overwrite them with unstable guesses.
- **Prompt optimization (in APOST)** — Generating improved prompt *variants* using a chosen *framework*; TCRTE scores inform **whether** structural repair is the priority (e.g. auto-select `tcrte` when overall is low).

For product-level context, see the repository root **`APOST_v4_Documentation.md`** (TCRTE framework and §3.3 scoring methodology).
