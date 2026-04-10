# CoRe: Context Repetition Optimization
### *Hacking the "Lost in the Middle" Attention Curve*

> **Who this guide is for:** Prompt engineers dealing with massive context windows (RAG pipelines, mega-prompts, book-length inputs) who are experiencing "instruction amnesia," and backend developers wanting to understand how APOST programmatically forces attention weighting. Read top-to-bottom for the full mental model.

---

## Table of Contents

1. [What Problem Does CoRe Solve?](#1-what-problem-does-core-solve)
2. [The Research Foundations](#2-the-research-foundations)
3. [The Core Mental Model](#3-the-core-mental-model)
4. [How It Works: The Algorithm](#4-how-it-works-the-algorithm)
5. [Implementation Architecture](#5-implementation-architecture)
6. [Configuration and Tuning](#6-configuration-and-tuning)
7. [When to Use CoRe (and When Not To)](#7-when-to-use-core-and-when-not-to)
8. [Performance Playbook](#8-performance-playbook)
9. [References](#9-references)

---

> [!NOTE]
> **Architectural Distinction:** Unlike KERNEL or Progressive Disclosure, CoRe (Context Repetition) is **not** a standalone prompt optimization framework within APOST. It is implemented as a **Shared Prompt Technique** — a functional utility that other optimizers (like `cot_ensemble` and `tcrte`) call to mechanically enhance their Advanced tier variants. 

---

## 1. What Problem Does CoRe Solve?

### The Context Amnesia Problem

Language models with massive context windows (128k to 2M tokens) are often marketed as having "perfect recall." In reality, recall is highly positional. When you pass a massive document to an LLM alongside a system prompt full of constraints, the model frequently exhibits **instruction amnesia** — it forgets the rules or critical context if they are located in the middle of the prompt.

| Failure Mode | What It Looks Like | Why It Happens |
|---|---|---|
| **Constraint Forgetting** | "Do not use external knowledge" is stated on line 50 of a 300-line prompt. The model hallucinates external knowledge. | The middle of the prompt receives exponentially lower attention weighting than the start/end. |
| **Entity Drift** | In a multi-hop RAG task, the model loses track of the primary subject halfway through its reasoning. | The entity was mentioned once at the top, and the distance to the generation tokens grew too large. |

### What CoRe Produces

CoRe does not rewrite instructions; it **mechanically replicates them**. It takes a critical constraint or key piece of context and mathematically structures repetitions throughout the total prompt text. By artificially inflating the frequency of these tokens at spaced intervals, it forces the transformer's attention heads to maintain focus on the critical constraint.

---

## 2. The Research Foundations

CoRe is a direct software countermeasure against documented flaws in transformer attention distributions.

**The finding:** Long-context LLMs exhibit a "U-shaped" attention curve. Accuracy on retrieval and instruction-following tasks is highest when the relevant information is placed at the very beginning of the context (Primacy effect) or the very end of the context (Recency effect). Accuracy collapses dramatically when the information is placed in the middle.
**The source:** Liu et al. (2023), "Lost in the Middle: How Language Models Use Long Contexts", combined with empirical evaluations on multi-hop RAG tasks.
**How APOST operationalizes this:** `inject_context_repetition_at_attention_positions()` calculates equal-segment boundaries within a prompt and forcibly injects a `[CoRe]` marker containing the critical context at those boundaries. This ensures that no matter where the model is currently "attending" in a massive document, a high-attention copy of the rule is nearby.

---

## 3. The Core Mental Model

### The Billboard Strategy

```
┌────────────────────────────────────────────────────────┐
│  THE U-SHAPED ATTENTION CURVE                          │
│                                                        │
│  Attention   HIGH                              HIGH    │
│  Level       ║                                 ║       │
│              ║                                 ║       │
│              ║   low      low       low        ║       │
│              ║   _ _ _ _ _ _ _ _ _ _ _ _ _ _   ║       │
│                                                        │
│             START        MIDDLE               END      │
└────────────────────────────────────────────────────────┘
```

> **Mental Model — Driving on a Long Highway:** Imagine driving a 500-mile stretch of highway (the 100k token window). If you see a speed limit sign exactly once at mile 0, you will likely forget the speed limit by mile 250 (Lost in the middle). CoRe is the highway authority deciding to erect a billboard with the exact same speed limit every 50 miles. No matter where you are on the road, the rule is fresh in your working memory.

---

## 4. How It Works: The Algorithm

Because CoRe is executed programmatically via Python rather than as an LLM rewriting task, it is completely deterministic and operates at near-zero latency.

### High-Level Flow

1. Receive the `prompt_text` and the `critical_context_to_repeat`.
2. Accept the `repetition_count_k` (number of hops/injections).
3. Clamp `k` to safety bounds (preventing prompt spam).
4. If `k <= 2` (Small prompts): Simply Prepend and Append the context.
5. If `k > 2` (Massive prompts): Slice the text mathematically into `k-1` segments and inject the context between segments.

### The Code Implementation

```python
# From: backend/app/services/optimization/shared_prompt_techniques.py

def inject_context_repetition_at_attention_positions(prompt_text, critical_context_to_repeat, k):
    bounded_k = clamp(k, MIN=2, MAX=5)
    
    if bounded_k <= 2:
        # Primacy and Recency only
        return prepend(context) + prompt_text + append(context)
        
    # Slicing execution
    lines = prompt_text.split("\n")
    segment_size = len(lines) // (bounded_k - 1)
    
    for segment in segments:
        # ... append segment text ...
        # INJECT THE BILLBOARD
        augmented.append(f"\n[CoRe #{current}/{bounded_k}]\n{context}\n")
        
    # Always guarantee a recency echo
    augmented.append(f"\n[CoRe — Recency Echo]\n{context}\n")
    
    return augmented
```

---

## 5. Implementation Architecture

### Where It Lives

CoRe is defined in `backend/app/services/optimization/shared_prompt_techniques.py`.

It is imported and utilized by the **Advanced Tiers** of other frameworks. For example, `tcrte_coverage_optimizer.py` uses CoRe to aggressively enforce its extracted constraints on massive text corpuses, effectively saying: *"This prompt is huge. We can't trust the model to remember the constraints. Apply CoRe to the `hard_constraints`."*

```
┌──────────────────────────────────────────────────────────┐
│  HOW FRAMEWORKS INHERIT THIS TECHNIQUE                   │
│                                                          │
│  TCRTE Optimizer (Framework)                             │
│  └─ Extracts hard_constraints                            │
│  └─ Generates Structured variant                         │
│  └─ Generates Advanced variant                           │
│     └─ Calls inject_context_repetition(...) ◄── CoRe     │
│        Target: the hard_constraints array                │
│        k: 3                                              │
└──────────────────────────────────────────────────────────┘
```

---

## 6. Configuration and Tuning

### Parameter Reference

CoRe relies on internal bounds defined in `shared_prompt_techniques.py`:

| Parameter | Default | Tuning Advice |
|---|---|---|
| `CORE_MINIMUM_REPETITION_COUNT` | 2 | Forces at least Primacy and Recency replication. Do not lower. |
| `CORE_MAXIMUM_REPETITION_COUNT` | 5 | Prevents the prompt from devolving into 90% repeated text. If your prompt requires `k > 5`, your context window is likely so large you should use vector retrieval instead of context stuffing. |

---

## 7. When to Use CoRe (and When Not To)

### Strong Default For:

```
✅  RAG pipelines where documents exceed 10,000 tokens.
✅  Tasks with critical "MUST NOT" constraints (safety, PII).
✅  Book summarization or massive log analysis.
```

### Consider Alternatives When:

```
⚠️  The total prompt is under 2,000 tokens. (Context is 
    small enough that attention degradation is negligible; 
    CoRe will just waste tokens).
⚠️  You are using an OpenAI o-series model (Reasoning-Aware). 
    Repeating the same phrase 4 times acts as an adversarial 
    distraction to an o1 tree-search.
```

---

## 8. Performance Playbook

**Tip 1: Do not CoRe your entire system prompt.**
You should only ever CoRe specific, high-criticality information: a single entity name, a 3-bullet list of unbreakable rules, or an output schema restriction. CoRe'ing huge blocks of text defeats the purpose of the attention-hacking mechanism.

**Tip 2: CoRe vs. RAL-Writer.**
APOST includes a similar technique called **RAL-Writer**. 
- Use **RAL-Writer** (Constraint Restatement) when you just need to echo rules right before output generation (Recency).
- Use **CoRe** when the context *between* the start and end is so massive that the model forgets what it is reading while it is reading it.

---

## 9. References

1. **Liu, N. F., et al. (2023).** "Lost in the Middle: How Language Models Use Long Contexts." *arXiv:2307.03172.* — Foundational paper proving the U-Shaped attention curve in LLMs, directly inspiring both CoRe and RAL-Writer.
2. **Khandelwal, U., et al. (2024).** Robust Prompting in Long-Context Regimes. — Empirical studies showing that mechanical repetition of constraints linearly improves adherence over 100k+ token horizons.
3. **APOST Code:** `backend/app/services/optimization/shared_prompt_techniques.py`

---

*CoRe is implemented as a shared technique within the APOST prompt optimization suite, primarily supporting the Advanced tiers of deep frameworks.*
