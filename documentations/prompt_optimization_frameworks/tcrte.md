# TCRTE Coverage Optimization
### *The Prompt Foundation Builder (Gap-Filling)*

> **Who this guide is for:** Users who have submitted extremely short or underspecified prompts (e.g., "Write a marketing email") and need to understand how APOST automatically expands them into production-ready system prompts. Read top-to-bottom for the full mental model.

---

## Table of Contents

1. [What Problem Does TCRTE Solve?](#1-what-problem-does-tcrte-solve)
2. [The Research Foundations](#2-the-research-foundations)
3. [The Core Mental Model](#3-the-core-mental-model)
4. [The 5 Core Dimensions](#4-the-5-core-dimensions)
5. [How It Works: The Algorithm](#5-how-it-works-the-algorithm)
6. [The Three Optimization Tiers](#6-the-three-optimization-tiers)
7. [Implementation Architecture](#7-implementation-architecture)
8. [Configuration and Tuning](#8-configuration-and-tuning)
9. [When to Use TCRTE (and When Not To)](#9-when-to-use-tcrte-and-when-not-to)
10. [Diagnosing Common Failures](#10-diagnosing-common-failures)
11. [Performance Playbook](#11-performance-playbook)
12. [References](#12-references)

---

## 1. What Problem Does TCRTE Solve?

### The Underspecification Problem

Advanced optimization frameworks like *XML Structured Bounding* or *Progressive Disclosure* assume that a prompt actually contains instructions to optimize. If a user submits a prompt that is only 5 words long—such as "Refactor this code for me"—there is nothing to structure. 

The prompt is fundamentally missing the Context (What codebase?), the Tone (Senior engineer or junior?), and the Execution constraints (Do you want comments? Should it be an entire file or a diff?). When sent to a model, the output will simply be the model's uncalibrated default, which drifts wildly based on the exact provider being used.

### What TCRTE Produces

The **TCRTE Coverage-First Optimizer** is APOST's foundational "rescue" framework. Instead of structuring existing text, it detects architectural gaps in your prompt and intelligently fills them. 

It maps the prompt against 5 necessary dimensions (Task, Context, Role, Tone, Execution), scores each dimension from 0-100, and uses LLM hallucination (or user gap-interview answers) to automatically flesh out the missing `Context`, `Role`, and `Execution` rules required to generate a stable, professional baseline.

---

## 2. The Research Foundations

**The finding:** "Zero-shot prompt quality scales log-linearly with the density of task specifications." Prompts that explicitly define a Role, define output Constraints, and ground Context produce vastly more deterministic results than flat instructions, even on highly capable frontier models.
**The source:** Internal empirical standards derived from OpenAI's *Prompt Engineering Guide* and Anthropic's *Claude Documentation*.
**How APOST operationalizes this:** `tcrte_coverage_optimizer.py` acts as an automated prompt engineer. It classifies every dimension as `MISSING` (<35), `WEAK` (<70), or `GOOD` (>=70). It forces the generation of structural blocks to repair any `MISSING` dimensions, ensuring that no prompt ever leaves APOST without a baseline level of structural density.

---

## 3. The Core Mental Model

### The Architect's Blueprint

> **Mental Model — The Blank Canvas vs. The Color-by-Numbers:** If a prompt is a canvas, a terrible prompt is completely blank except for a sticky note that says "Paint a house." Other optimizers try to re-organize the sticky note. TCRTE takes a pencil, draws the outline of the house, adds numbers indicating which colors to put where, and returns the canvas to you ready to be finalized. 

---

## 4. The 5 Core Dimensions

TCRTE relies on the rigid static analysis data `gap_data` provided by the APOST system during prompt submission.

| Dimension | Measure | What happens if it's missing? |
|---|---|---|
| **[ T ] Task** | Is the absolute goal correctly defined? | Model hallucinates the goal. |
| **[ C ] Context** | What is the domain, situation, or user persona? | Model anchors to generic Wikipedia knowledge instead of your specific domain. |
| **[ R ] Role** | Have you told the model *who* it is acting as? | Model defaults to "Helpful AI Assistant" tone, making creative outputs sterile. |
| **[ T ] Tone** | Have you specified formatting, emotion, or register? | Model is either overly casual or overly academic. |
| **[ E ] Execution** | Did you provide hard output rules, schemas, or length boundaries? | The response does not fit your downstream API parser. |

---

## 5. How It Works: The Algorithm

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│     TCRTE GAP-FILLING OPTIMIZATION PIPELINE                     │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │  STAGE 1: DIMENSION TRIAGE           │
  │  Read gap_data scores. Classify:     │
  │  • <35 = MISSING (Must fill)         │
  │  • <70 = WEAK (Should enhance)       │
  │  • >70 = GOOD (Preserve)             │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 2: ANSWER INTEGRATION         │
  │  If user answered the automated gap  │
  │  interview questions, inject those   │
  │  answers directly into the prompt.   │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 3: HYPOTHETICAL REWRITE       │
  │  LLM sub-call generates the missing  │
  │  sections (Role, Context, etc.) by   │
  │  intelligently inferring the task.   │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 4: VARIANT ASSEMBLY           │
  │  Package the generated sections into │
  │  the 3 escalating tiers.             │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 5: INJECTION OF TECHNIQUES    │
  │  Advanced variants receive CoRe and  │
  │  RAL-Writer techniques on the        │
  │  newly filled Execution rules.       │
  └──────────────────────────────────────┘
```

---

## 6. The Three Optimization Tiers

```
┌──────────────────────────────────────────────────────────────┐
│  THE THREE TIERS                                             │
└──────────────────────────────────────────────────────────────┘

  CONSERVATIVE ─────────────────────────────────────────────────
  
  What it does: Appends ONLY the critically MISSING dimensions 
  to the original prompt. Does not rewrite the core narrative.
  
  Meaning: The gentlest fix. Gives the user exactly what they 
  forgot to add, while preserving their exact voice.
  
  ──────────────────────────────────────────────────────────────

  STRUCTURED ───────────────────────────────────────────────────
  
  What it does: Aggressive structural format. Implements the 
  complete 5-section [TASK], [CONTEXT], [ROLE], [TONE], 
  [EXECUTION] architecture as markdown blocks.
  
  Meaning: Upgrades a sloppy prompt to a production baseline 
  that is easy for other developers to read and iterate on.
  
  ──────────────────────────────────────────────────────────────

  ADVANCED ─────────────────────────────────────────────────────
  
  What it does: Full 5-section architecture. Then, runs 
  APOST's shared techniques:
  • Extracts the single most critical Context and loops it 
    via the "CoRe" technique.
  • Executes the RAL-Writer Recency Echo on the Execution 
    rules at the bottom of the prompt.
  
  Meaning: The maximum stability prompt. Best when facing 
  unpredictable user inputs.
  
  ──────────────────────────────────────────────────────────────
```

---

## 7. Implementation Architecture

### Codebase Map

```
┌────────────────────────────────────────────────────────────────┐
│  CODEBASE INTEGRATION                                          │
└────────────────────────────────────────────────────────────────┘

  execute_optimization_request()
        │
        ├── framework_selector.py
        │   → selects tcrte_coverage FIRST if:
        │     Overall TCRTE gap_score < 50
        │     (Takes precedence because no other framework can 
        │      optimize a 5-word prompt)
        │
        ▼
  tcrte_coverage_optimizer.py 
  TcrteCoverageOptimizer
        │
        ├── _classify_dimensions_by_score()
        │
        ├── _build_dimension_repair_instructions()
        │
        ├── LLM Call (Generates the 5 explicit sections) 
        │
        └── _assemble_variant()          ◄── Python Assembly
             │
             ├── apply_ral_writer_constraint_restatement()
             └── inject_context_repetition_at_attention_positions()
```

---

## 8. Configuration and Tuning

### Parameter Reference

Configuration values located in `tcrte_coverage_optimizer.py` and `optimizer_configuration.py`:

| Parameter | Default | Tuning Advice |
|---|---|---|
| `TCRTE_SCORE_THRESHOLD_MISSING` | `35` | Increase to `50` if you want APOST to more aggressively overwrite user prompts instead of just appending to them. |
| `TCRTE_SCORE_THRESHOLD_WEAK` | `70` | The boundary deciding whether the LLM should preserve a block entirely or attempt to "enhance" it. |

---

## 9. When to Use TCRTE (and When Not To)

### Strong Default For:

```
✅  Prompts that score under 50 in the main APOST web UI.
✅  First-draft prompts that only contain the instruction 
    ("Write a twitter post about X").
✅  Any prompt where you do not know the correct execution 
    constraints, and want the LLM to hypothesize some for you.
```

### Consider Alternatives When:

```
⚠️  Your prompt is already highly detailed (Overall score > 70).
    TCRTE will simply return your exact prompt back to you. 
    Use KERNEL, SAMMO, or Progressive Disclosure.
```

---

## 10. Diagnosing Common Failures

| Symptom | Most Likely Cause | Where to Investigate |
|---|---|---|
| The Advanced variant is massively repetitive | The optimizer found missing execution rules, hallucinated them, and then applied CoRe AND RAL-Writer to them. | Use the Structured variant instead for standard use cases. |
| The prompt hallucinated the wrong Context | You provided a 4-word prompt, and the framework tried to guess your domain. | Fill out the *Gap Interview* answers on the UI so the framework has factual ground truth to use during Stage 2. |

---

## 11. Performance Playbook

**Tip 1: Use the Gap Interview!**
When you submit a raw prompt to APOST, the system evaluates it and optionally returns an array of "Questions" (e.g., "What specific schema should this output?"). If you answer those questions and pass them back inside the API `OptimizationRequest` as `answers`, TCRTE skips hallucinating and explicitly drops your answers into the generated Sections. This is the fastest way to build production prompts from scratch.

**Tip 2: Why Advanced TCRTE uses CoRe.**
You might wonder why TCRTE (a foundation framework) leverages `CoRe` (a high-end shared technique documented in `core_attention.md`). Because TCRTE creates prompts that are highly broken down into 5 massive blocks, the distance between the `[CONTEXT]` block at the top and the end of the prompt can become quite large. By executing `CoRe` on the single most critical context element, the Advanced tier ensures the newly generated architecture does not suffer from "Lost in the Middle" syndrome.

---

## 12. References

1. **APOST Internal Documentation:** `APOST_v4_Documentation.md` §3 (The TCRTE Scoring Algorithm).
2. **APOST Codebase:** `backend/app/services/optimization/frameworks/tcrte_coverage_optimizer.py`.
3. **Liu, N. F., et al. (2023).** Basis for the integration of `inject_context_repetition_at_attention_positions()` within the Advanced tier generation.

---

*The TCRTE Coverage Optimizer is part of the APOST prompt optimization suite. It acts as the fallback mechanism for severely underspecified inputs.*
