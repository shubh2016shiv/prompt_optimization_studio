# RAL-Writer (Retrieve-and-Restate) Framework
### *Preventing Constraint Dilution via Disentanglement and Recency*

> **Who this guide is for:** Prompt engineers struggling with LLMs "forgetting" complex bounds (e.g., formatting rules, negative constraints) in large prompts, and backend developers wanting to understand the algorithmic difference between APOST's shared RAL-Writer utility and this standalone constraint extraction framework. Read top-to-bottom for the full mental model.

---

## Table of Contents

1. [What Problem Does RAL-Writer Solve?](#1-what-problem-does-ral-writer-solve)
2. [The Research Foundations](#2-the-research-foundations)
3. [The Core Mental Model](#3-the-core-mental-model)
4. [Standalone Framework vs. Shared Utility](#4-standalone-framework-vs-shared-utility)
5. [How It Works: The Algorithm](#5-how-it-works-the-algorithm)
6. [The Three Optimization Tiers](#6-the-three-optimization-tiers)
7. [The Quality Gate](#7-the-quality-gate)
8. [Implementation Architecture](#8-implementation-architecture)
9. [Configuration and Tuning](#9-configuration-and-tuning)
10. [When to Use RAL-Writer (and When Not To)](#10-when-to-use-ral-writer-and-when-not-to)
11. [Diagnosing Common Failures](#11-diagnosing-common-failures)
12. [Performance Playbook](#12-performance-playbook)
13. [References](#13-references)

---

## 1. What Problem Does RAL-Writer Solve?

### The Constraint Dilution Problem

When users write prompts, they naturally weave rules and constraints into the narrative of the task. 

*Example Raw Prompt:*
> *"You are a historian analyzing this document. Make sure to use British spelling. The document is about the fall of Rome. Summarize the key economic factors, but do not use bullet points. Make sure the output is under 300 words. Describe the trade routes in detail."*

In this prompt, the core task (summarize economic factors of Rome) is entangled with hard constraints (British spelling, no bullet points, < 300 words). If the context text is very large, or the task requires deep reasoning, the LLM will focus its attention on the Roman history and **forget** the formatting rules. This is known as *Constraint Dilution*.

### What RAL-Writer Produces

RAL-Writer Optimization forensically rips the constraints out of the narrative. It creates a pure, clean Task/Context section, and isolates the rules into a rigid, structured Constraints block. Finally, it calculates which rules are most critical and mathematically injects them at the exact end of the prompt (the Recency boundary) so the model sees them immediately before token generation.

---

## 2. The Research Foundations

**The finding:** LLMs suffer from "Lost in the Middle" attention degradation. The attention mechanism places maximum weight on the first 10% of a context window (Primacy) and the last 10% (Recency). Rules buried in the middle are frequently ignored.
**The source:** Liu et al. (2023), "Lost in the Middle: How Language Models Use Long Contexts."
**How APOST operationalizes this:** RAL-Writer utilizes a "Retrieve-and-Restate" mechanism. It extracts the rules early in the prompt (Primacy), and then mechanically retrieves the most critical rules and literally restates them at the bottom of the prompt (Recency Echo).

---

## 3. The Core Mental Model

### The Legal Contract

> **Mental Model — The Narrative vs. The Contract:** A raw prompt is a loose conversation with an employee — instructions are scattered everywhere. A RAL-Writer structured prompt is a Legal Contract. Paragraph 1 defines the scope of work (The Context). Paragraph 2 defines the deliverable (The Task). And the addendum at the very bottom explicitly lists the Terms & Conditions (The Constraints) right before the employee signs it.

```
┌────────────────────────────────────────────────────────┐
│  RAL-WRITER STRUCTURAL DISENTANGLEMENT                 │
│                                                        │
│  [ TASK DIRECTIVE ]                                    │
│   Summarize economic factors of Rome in the text.      │
│                                                        │
│  [ BACKGROUND CONTEXT ]                                │
│   <user_document> ... </user_document>                 │
│                                                        │
│  [ ISOLATED CONSTRAINT BLOCK (MANDATORY) ]             │
│   - Spelling MUST be British English.                  │
│   - Output MUST NOT include bullet points.             │
│   - Length MUST be strictly under 300 words.           │
│                                                        │
│  [ RECENCY ECHO (RAL) ]                                │
│   Reminder: Do not use bullet points. <300 words.      │
└────────────────────────────────────────────────────────┘
```

---

## 4. Standalone Framework vs. Shared Utility

You may see references to `RAL-Writer` in two different contexts within APOST. It is critical to understand the distinction:

| Concept | What It Is | How It Works |
|---|---|---|
| **The Shared Utility** (`shared_prompt_techniques.py`) | A "dumb" Python function. | Other frameworks pass an array of strings to this function, and it simply appends them to the end of the prompt text. |
| **The Standalone Optimizer** (`ral_writer_optimizer.py`) | A comprehensive intelligent framework. | Uses multi-pass LLM reasoning to actually identify implicit vs explicit rules, detect contradictions in the user's prompt, disentangle text, and mathematically structure the prompt block by block. |

When you select `ral_writer` as your `framework` in the API, you are triggering the advanced Standalone Optimizer.

---

## 5. How It Works: The Algorithm

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│     RAL-WRITER CONSTRAINT OPTIMIZATION PIPELINE                 │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │  STAGE 1: FORENSIC EXTRACTION        │
  │  LLM deeply analyses the raw prompt  │
  │  to extract:                         │
  │  • Explicit hard constraints         │
  │  • Soft style preferences            │
  │  • Implicit/Missing rules            │
  │  • Conflicts (Contradictions)        │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 2: DISENTANGLEMENT            │
  │  LLM rewrites the narrative to       │
  │  remove all rules, leaving pure      │
  │  Context and pure Task.              │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 3: ASSEMBLY & ECHO            │
  │  Python injects the narrative, then  │
  │  the rule block. Calculates most     │
  │  critical rules, then executes the   │
  │  Recency Echo.                       │
  │                                      │
  │  ┌─────────┐ ┌──────────┐ ┌───────┐ │
  │  │CONSERV- │ │STRUCTURED│ │ADVANC-│ │
  │  │ATIVE    │ │          │ │ED     │ │
  │  │(No      │ │(Basic    │ │(High  │ │
  │  │ Echo)   │ │ Echo)    │ │ Cont- │ │
  │  │         │ │          │ │ rast) │ │
  │  └────┬────┘ └────┬─────┘ └───┬───┘ │
  └───────┴───────────┴───────────┴──────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 4: QUALITY GATE & ALERTS      │
  │  Any Contradictions found in Stage 1 │
  │  are appended to the Response Metadata│
  └──────────────────────────────────────┘
```

---

## 6. The Three Optimization Tiers

```
┌──────────────────────────────────────────────────────────────┐
│  THE THREE TIERS                                             │
└──────────────────────────────────────────────────────────────┘

  CONSERVATIVE ─────────────────────────────────────────────────
  
  What it does: Creates the clean narrative and adds the 
  Primacy Constraint array. It DOES NOT execute the recency echo.
  
  Best for: Short prompts (<1000 tokens) where constraint 
  dilution is not mechanically possible due to low token distance.
  
  ──────────────────────────────────────────────────────────────

  STRUCTURED ───────────────────────────────────────────────────
  
  What it does: Employs explicit Markdown headers for isolation 
  and executes the recency echo for the top 3 highest-criticality 
  rules. Surfaces implicit requirements.
  
  Best for: Standard production extraction pipelines.
  
  ──────────────────────────────────────────────────────────────

  ADVANCED ─────────────────────────────────────────────────────
  
  What it does: Heavy text-based contrast borders (=====) 
  separating the blocks. Groups rules by Hard / Implicit / Soft. 
  Execute full recency echo + Provider-native Prefill block.
  
  Best for: Massive RAG-based context parsing where the constraint 
  block is physically separated from the output by 80,000 tokens.
  
  ──────────────────────────────────────────────────────────────
```

---

## 7. The Quality Gate

Because RAL-Writer disentangles user text, the Quality Gate is responsible to ensure the Disentanglement LLM did not accidentally discard any actual Context facts during Stage 2. If the gate determines that crucial facts were lost, it will stitch them back into the `Context` block.

---

## 8. Implementation Architecture

### Codebase Map

```
┌────────────────────────────────────────────────────────────────┐
│  CODEBASE INTEGRATION                                          │
└────────────────────────────────────────────────────────────────┘

  execute_optimization_request()
        │
        ├── framework_selector.py
        │   → selects ral_writer when:
        │     task_type is extraction/classification BUT
        │     the raw prompt has high constraint density OR 
        │     contains explicit contradictions.
        │
        ▼
  OptimizerFactory.get_optimizer("ral_writer")
        │
        ▼
  ral_writer_optimizer.py  ◄─── Core logic
  RalWriterOptimizer
        │
        ├── _extract_constraints()      ◄── LLM Call (Analyser)
        │
        ├── _disentangle_narrative()    ◄── LLM Call (Rewriter)
        │
        ├── _assemble_variant()         ◄── Python Assembly
        │    │
        │    └── apply_ral_writer_constraint_restatement()
        │
        └── _refine_variants_with_quality_critique()
```

---

## 9. Configuration and Tuning

### Parameter Reference

| Parameter | Location | Tuning Advice |
|---|---|---|
| `MAX_TOKENS_COMPONENT_EXTRACTION` | `optimizer_configuration.py` | Controls the token budget for the Extraction and Disentanglement LLM calls. |
| Criticality Selection | Hardcoded in `_assemble_variant` | By default, only rules marked `"criticality": "high"` by the extractor are echoed. If none exist, it echoes the top 3. |

---

## 10. When to Use RAL-Writer (and When Not To)

### Strong Default For:

```
✅  Prompts that begin with "You must absolutely never..."
✅  Heavily stylized generation (strict voice, tone, syntax constraints).
✅  Context-heavy prompts where the model hallucinates formats 
    because it focused too hard on the background knowledge.
```

### Consider Alternatives When:

```
⚠️  The prompt requires step-by-step reasoning logic. 
    (RAL-Writer manages rules, not reasoning loops). Use 
    CoT Ensemble or OPRO.
⚠️  The primary issue is the model generating too much/too little text, 
    but rules are otherwise followed. 
    Use Overshoot/Undershoot.
```

---

## 11. Diagnosing Common Failures

| Symptom | Most Likely Cause | Where to Investigate |
|---|---|---|
| Critical rule is ignored | The Extractor didn't mark it "high" criticality. | The Recency Echo only picks up rules marked "high". If the LLM didn't prioritize it, it won't echo. Make the rule harsher in the `raw_prompt`. |
| Prompt metadata shows "Conflicts" | The user requested two impossible things (e.g., "Summarize deeply" + "Keep it under 10 words"). | Check the `detected_issues` array on the Response. RAL-Writer explicitly flags contradictions. |

---

## 12. Performance Playbook

**Tip 1: Surface the Implicit Rules.**
RAL-Writer contains a unique sub-layer during `_extract_constraints()` where it is asked to identify `missing_implicit_constraints`. For example, if the prompt says "Return a CSV," it implicitly requires "Escape internal commas with quotes." RAL-Writer discovers these and appends them to the Structured and Advanced variants, making your prompts vastly more robust to edge cases without any extra manual design work.

**Tip 2: Fix Contradictions Before Production.**
If the RAL-Writer Optimization Response returns conflicts inside `analysis.detected_issues`, do not ignore them. An LLM cannot mathematically optimize around a direct contradiction; it will simply hallucinate one rule over the other based on random probability thresholds. Resolve the contradiction in your source prompt and rerun the optimization.

---

## 13. References

1. **Liu, N. F., et al. (2023).** "Lost in the Middle: How Language Models Use Long Contexts." *arXiv:2307.03172.* — Foundational paper proving Primacy/Recency bias.
2. **APOST Codebase:** `backend/app/services/optimization/frameworks/ral_writer_optimizer.py`.
3. **APOST Codebase:** `backend/app/services/optimization/shared_prompt_techniques.py` (Contains the underlying echo utility function).

---

*The RAL-Writer Standalone Optimizer is part of the APOST prompt optimization suite. For framework selection guidance, see the auto-router documentation in `framework_selector.py`.*
