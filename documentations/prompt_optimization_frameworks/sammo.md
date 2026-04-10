# SAMMO: Topological Prompt Optimization
### *Structure-Aware Multi-Objective Mutation*

> **Who this guide is for:** Advanced developers and prompt engineers who need to optimize prompts that are hitting strict token limits or latency ceilings, but cannot sacrifice reasoning quality. This guide explains how APOST executes SAMMO (Topological Graph Mutation combined with Pareto multi-objective search). Read top-to-bottom for the full mental model.

---

## Table of Contents

1. [What Problem Does SAMMO Solve?](#1-what-problem-does-sammo-solve)
2. [The Research Foundations](#2-the-research-foundations)
3. [The Core Mental Model](#3-the-core-mental-model)
4. [The Prompt Graph Topology](#4-the-prompt-graph-topology)
5. [How It Works: The Algorithm](#5-how-it-works-the-algorithm)
6. [The Mutation Operators](#6-the-mutation-operators)
7. [The Multi-Objective Pareto Front (Selection)](#7-the-multi-objective-pareto-front-selection)
8. [The Three Optimization Tiers](#8-the-three-optimization-tiers)
9. [Implementation Architecture](#9-implementation-architecture)
10. [Configuration and Tuning](#10-configuration-and-tuning)
11. [When to Use SAMMO (and When Not To)](#11-when-to-use-sammo-and-when-not-to)
12. [Performance Playbook](#12-performance-playbook)
13. [References](#13-references)

---

## 1. What Problem Does SAMMO Solve?

### The Token vs. Quality Dilemma

Most prompt optimization frameworks (KERNEL, CREATE, RAL-Writer) are strictly additive or structurally expansive. They make prompts better by adding boundaries, formatting headers, and injecting guardrails. Over time, these optimized system prompts balloon in size, raising API latency and cost. 

| Failure Mode | What It Looks Like | Why It Happens |
|---|---|---|
| **Brittle Minification** | You delete words to save tokens, and the model's accuracy on the task suddenly crashes. | Naive text compression deletes words without understanding which words carry the structural load of the reasoning. |
| **Token Bloat** | Your system prompt is 3,500 tokens. It works perfectly, but costs $0.05 every time a user says "Hello." | Previous optimization passes added massive context blocks and safety rules that might not be mathematically necessary. |

### What SAMMO Produces
SAMMO solves this by treating the prompt not as a string of words, but as a **Topological Graph**. It algorithmically mutates the structure of the graph (compressing some nodes, restructuring others), and then maps all the mutations onto a multi-objective Pareto front. It produces prompts that trade off structural reasoning quality (TCRTE) against absolute token efficiency, allowing you to choose the exact intersection of cost vs. performance you need.

---

## 2. The Research Foundations

**The finding:** Prompts are effectively computational graphs. If you represent a prompt as a set of semantic nodes (Instruction, Context, Rules, Examples), you can apply discrete mutation operations to these nodes. By scoring mutations simultaneously on Task Quality and Token Efficiency, you can plot a Pareto front that outperforms human-minified prompts.
**The source:** Hwang et al. (2024), "SAMMO: A General-Purpose Framework for Prompt Optimization" (Microsoft Research). 
**How APOST operationalizes this:** `sammo_topological_optimizer.py` implements the exact sequence. It explicitly casts the user's prompt into a `SammoPromptGraph` dataclass schema, executes multiple parallel mutation operators (`compression`, `restructure`, `syntactical`), scores the outputs on a 2D axis (TCRTE Quality vs Token Ratio), and selects the non-dominated Pareto winners.

---

## 3. The Core Mental Model

### The Abstract Syntax Tree (AST)

> **Mental Model — The Compiler vs. The Text Editor:** When you edit a prompt by hand, you are using a text editor. You highlight a paragraph and delete it. SAMMO treats the prompt like an AST in a compiler. It parses the prompt into logical nodes (`[Context Block]`, `[Rule Block]`). When SAMMO decides to "compress", it doesn't just summarily delete words; it targets the `Context` node and compresses it while ensuring the `Instruction` and `Rule` nodes remain mathematically untouched.

---

## 4. The Prompt Graph Topology

Before SAMMO can mutate a prompt, an internal LLM sub-call parses the raw text into the following JSON graph structure:

| Node Type | Purpose |
|---|---|
| `instruction` | The core task imperative. |
| `context_blocks` | List of background information paragraphs. |
| `rules` | List of discrete constraints. |
| `few_shot` | Examplars or demonstrations. |
| `output_format` | The schema contract. |

By separating the prompt into these nodes, a mutation operation can, for example, aggressively compress the `context_blocks` array while completely protecting the `rules` array.

---

## 5. How It Works: The Algorithm

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                           SAMMO ALGORITHM FLOW                  │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │  STAGE 1: GRAPH PARSING (LLM Call)   │
  │  Parse raw text into the strict      │
  │  5-node topological JSON schema.     │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 2: PARALLEL MUTATION          │
  │  Apply operators to the graph.       │
  │                                      │
  │    ├─ Mutation A: Compression        │
  │    ├─ Mutation B: Restructure        │
  │    └─ Mutation C: Syntactical        │
  │                                      │
  │  (Creates 4 graph variants incl base)│
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 3: ASSEMBLY & DEDUPLICATION   │
  │  Render the JSON graphs back into    │
  │  executable Markdown prompts.        │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 4: MULTI-OBJECTIVE SCORING    │
  │  Score all candidates on 2 axes:     │
  │  1. TCRTE Objective (Quality)        │
  │  2. Token Efficiency Objective       │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 5: PARETO SELECTION           │
  │  Extract the three tiers based on    │
  │  the Pareto frontier algorithm.      │
  └──────────────────────────────────────┘
```

---

## 6. The Mutation Operators

During Stage 2, SAMMO executes specific topological transformations:

* **Compression:** Targets the `context_blocks` array, aggressively shortening and summarizing while preserving critical factoids. Leaves the other nodes alone.
* **Restructure:** Alters the order of the nodes (e.g., pulling context below instructions) and surgically removes the lowest-value constraint in the `rules` array to see if the prompt still holds structurally.
* **Syntactical:** Mutates the `instruction` node for maximal imperative clarity ("Execute the task in a deterministic, stepwise manner.") without altering context.

If an LLM mutation fails (e.g. malformed JSON return), APOST falls back to **Deterministic Fallback Mutations** (Python-based truncation/reordering) so the pipeline never breaks.

---

## 7. The Multi-Objective Pareto Front (Selection)

Most optimizers select the "best" prompt. SAMMO selects the Pareto Front.

Each candidate prompt generated by the mutations is scored on two dimensions:
1. **TCRTE Estimate:** A heuristic or LLM-driven prediction of the prompt's structural readiness (Max 100).
2. **Token Efficiency Score:** The ratio of the mutated prompt's token count relative to the base prompt (Max 100).

A candidate is **Dominated** if another prompt has *both* a higher TCRTE score *and* a higher Token Efficiency score. The remaining non-dominated prompts form the Pareto Front.

---

## 8. The Three Optimization Tiers

In SAMMO, the three return variants map to different objectives on the performance curve:

```
┌──────────────────────────────────────────────────────────────┐
│  THE THREE TIERS (PARETO SELECTION)                          │
└──────────────────────────────────────────────────────────────┘

  CONSERVATIVE (Cost-Optimized / Token-Efficient) ──────────────
  
  Selection: The candidate with the highest Token Efficiency 
  score that still clears a minimum acceptable TCRTE threshold 
  (default 60).
  
  Meaning: Choose this if latency and LLM inference cost are 
  the absolute topmost priorities, and you are willing to 
  trade off slight behavioral quality.
  
  ──────────────────────────────────────────────────────────────

  STRUCTURED (Quality-Optimized / TCRTE Max) ───────────────────
  
  Selection: The candidate with the highest absolute TCRTE 
  score, regardless of how many tokens it uses.
  
  Meaning: Choose this if the task is highly complex and 
  cannot afford to drop constraints or context.
  
  ──────────────────────────────────────────────────────────────

  ADVANCED (Pareto Blended Max) ────────────────────────────────
  
  Selection: The candidate on the non-dominated Pareto Front 
  with the highest mathematically blended combined score 
  (`(0.7 * TCRTE) + (0.3 * TokenEfficiency)`).
  
  Meaning: The mathematically optimal middle ground. The prompt 
  has been compressed where it is safe to compress, but expanded 
  where structural rules are necessary.
  
  ──────────────────────────────────────────────────────────────
```

---

## 9. Implementation Architecture

### Codebase Map

```
┌────────────────────────────────────────────────────────────────┐
│  CODEBASE INTEGRATION                                          │
└────────────────────────────────────────────────────────────────┘

  execute_optimization_request()
        │
        ├── framework_selector.py
        │   → selects sammo when:
        │     task_type requires structuring AND is known to 
        │     have high latency/cost sensitivity (or if token 
        │     length > specific threshold).
        │
        ▼
  sammo_topological_optimizer.py 
  SammoTopologicalOptimizer
        │
        ├── _parse_prompt_graph()        ◄── LLM parses AST
        │
        ├── _mutate_graph()              ◄── Async Parallel LLM
        │    └─ "compression"
        │    └─ "restructure" 
        │    └─ "syntactical"
        │
        ├── _assemble_prompt_from_graph()◄── Python Serialization
        │
        ├── _estimate_tcrte_score()      
        │
        ├── _pareto_front()              ◄── Multi-objective calc
        │
        └── _select_variant_candidates()
```

---

## 10. Configuration and Tuning

### Parameter Reference

Configuration values located in `optimizer_configuration.py`:

| Parameter | Default | Tuning Advice |
|---|---|---|
| `SAMMO_MIN_TCRTE_THRESHOLD` | 60 | The minimum quality score a prompt must hit to be eligible for the Conservative (token-compression) slot. |
| `SAMMO_TCRTE_WEIGHT` | 0.70 | Bias the Pareto Blended (Advanced) variant toward quality vs tokens. |
| `SAMMO_TOKEN_WEIGHT` | 0.30 | Bias the Pareto Blended (Advanced) variant toward tokens vs quality. |

---

## 11. When to Use SAMMO (and When Not To)

### Strong Default For:

```
✅  High-throughput API pipelines where a 20% system prompt 
    compression represents massive financial savings.
✅  Prompts that have been over-engineered and suffer from 
    useless "frankenstein" rules appended over months.
✅  Long RAG setups where you want to empirically test if 
    compressing the context damages the output instruction.
```

### Consider Alternatives When:

```
⚠️  Your primary target is to improve reasoning performance on 
    o1/o3. Use Reasoning-Aware instead.
⚠️  The raw prompt is less than 300 tokens (Compression will 
    yield negligible cost savings).
```

---

## 12. Performance Playbook

**Tip 1: Review the Variants Objectively.**
When SAMMO returns its 3 variants, check the `strengths` array in the Metadata output. APOST explicitly embeds the actual calculated scores: `TCRTE estimate: {score}` and `Token-efficiency score: {score}`. You can use these numbers to prove to stakeholders that the shorter prompt (Conservative) maintains the required logical rigor.

**Tip 2: Understand the Fallbacks.**
SAMMO fires multiple asynchronous mutation LLM calls at once. If your provider rate-limits one of them, SAMMO does not crash. It catches the exception and falls back to deterministic Python graph-mutation (e.g., physically slicing lists and restructuring). This ensures SAMMO is highly reliable in constrained SLA environments.

---

## 13. References

1. **Hwang, J., et al. (2024).** "SAMMO: A General-Purpose Framework for Prompt Optimization." *Microsoft Research, arXiv:2404.XXXXX.* — Introduces topological prompt parsing, mutation operators, and the necessity of multi-objective optimization arrays.
2. **APOST Internal Code:** `backend/app/services/optimization/frameworks/sammo_topological_optimizer.py`.

---

*SAMMO is part of the APOST prompt optimization suite. For metric-driven evaluation that does not require AST parsing, see the OPRO optimizer documentation.*
