# Reasoning-Aware Optimization: A Comprehensive Guide
### *Declarative Prompts for Test-Time Compute Models*

> **Who this guide is for:** Prompt engineers transitioning from standard LLMs (like GPT-4) to test-time reasoning models (like OpenAI o1/o3 or DeepSeek R1), and backend developers who need to understand how APOST structurally adapts prompts for models that do their own internal chain of thought. Read top-to-bottom for the full mental model, or jump to any section independently.

---

## Table of Contents

1. [What Problem Does Reasoning-Aware Solve?](#1-what-problem-does-reasoning-aware-solve)
2. [The Research Foundations](#2-the-research-foundations)
3. [The Core Mental Model](#3-the-core-mental-model)
4. [The Declarative Contract Structure](#4-the-declarative-contract-structure)
5. [How It Works: The Algorithm](#5-how-it-works-the-algorithm)
6. [The Three Optimization Tiers](#6-the-three-optimization-tiers)
7. [Provider-Aware JSON Extraction](#7-provider-aware-json-extraction)
8. [The Quality Gate](#8-the-quality-gate)
9. [Implementation Architecture](#9-implementation-architecture)
10. [Configuration and Tuning](#10-configuration-and-tuning)
11. [When to Use Reasoning-Aware (and When Not To)](#11-when-to-use-reasoning-aware-and-when-not-to)
12. [Diagnosing Common Failures](#12-diagnosing-common-failures)
13. [Performance Playbook](#13-performance-playbook)
14. [Future Directions](#14-future-directions)
15. [References](#15-references)

---

## 1. What Problem Does Reasoning-Aware Solve?

### The "Over-Steering" Problem

For years, the standard approach to getting good outputs from LLMs involved explicit procedural heavy-lifting: "Think step by step", "First analyze A, then consider B, then evaluate C", or "Use a scratchpad to write out your logic before answering."

With the advent of Test-Time Compute models (also called inference-time reasoning models, like OpenAI o1), this paradigm broke. **These models perform their own hidden Chain-of-Thought (CoT).** When a user provides explicit instructions on *how* to think, it creates two major fail states:

| Failure State | What It Looks Like | Why It Happens |
|---|---|---|
| **Negative Interference** | The model's reasoning gets worse, ignores edge cases, or hallucinates. | The prompt forces the model to abandon its highly-trained internal search policy to follow humans' often flawed logic steps. |
| **Explanation Bleed** | The final API output includes paragraphs of explanations before the JSON payload. | The prompt asked the model to "show its work," causing it to emit internal thoughts directly into external output. |

> **Mental Model — The Micromanager vs. The Architect:** When you prompt GPT-4, you are a micromanager showing a junior employee exactly how to do the math. When you prompt an o1 model, you are an architect handing a blueprint to a master builder. The builder only cares about the rigid constraints and the final dimensions (output format). If you try to tell the builder how to hold the hammer, the house will suffer.

### What Reasoning-Aware Produces

Reasoning-Aware Optimization strips explicit "how to think" instructions out of the raw prompt. It transforms the prompt into a rigid **Declarative Execution Contract**: exactly *what* must be done, what constraints are *unbreakable*, and exactly *what shape* the output must take.

---

## 2. The Research Foundations

Reasoning-Aware framework replaces academic prompt-engineering techniques with modern best practices surrounding test-time scaling.

### 2.1 The Paradigm Shift to Test-Time Compute

**The finding:** Models trained with Reinforcement Learning to perform latent reasoning (like the o-series) develop search policies (like tree-search or path-exploration) that vastly outperform human-designed CoT templates. Providing them with a "step-by-step" guide acts as a constraint that artificially limits their search space.
**The source:** OpenAI o1 System Documentation & Developer Best Practices; DeepSeek R1 Technical Report. 
**How APOST operationalizes this:** The `_extract_reasoning_sections` LLM call is specifically instructed to *purge* procedural scaffolding, scratchpad instructions, and "act as a reasoning agent" tropes from the raw prompt, leaving only the constraints.

### 2.2 Format Primacy over Procedural Instruction

**The finding:** Inference-heavy models can over-think and drift away from schema requirements unless the structural contract is heavily prioritized.
**The source:** Empirical evaluations of test-time models on strict JSON/schema-adherence benchmarks (e.g., SEAL leaderboards).
**How APOST operationalizes this:** In the Structured and Advanced tiers, the generated prompt places the `OUTPUT CONTRACT` early in the context window (primacy) and frames all hard constraints around satisfying that specific format. 

---

## 3. The Core Mental Model

### The Declarative Contract

A standard prompt is procedural. A Reasoning-Aware prompt is declarative. 

```
┌────────────────────────────────────────────────────────┐
│  PROCEDURAL (BAD FOR O1) vs DECLARATIVE (GOOD FOR O1)  │
│                                                        │
│  [ RAW PROCEDURAL PROMPT ]                             │
│  "Analyze the attached code. First review the          │
│  imports, then review the syntax. Think step by step   │
│  about the security profile. Show your logic.          │
│  Return a JSON with your findings."                    │
│                                                        │
│  [ REASONING-AWARE PROMPT ]                            │
│  "ABSOLUTE TASK: Audit the code for security flaws.    │
│                                                        │
│  OUTPUT FORMAT:                                        │
│  { 'flaws': [str], 'severity_score': int }             │
│                                                        │
│  HARD CONSTRAINTS:                                     │
│  - Severity score MUST be 1-10.                        │
│  - MUST only reference CWE-defined vulnerabilities."   │
└────────────────────────────────────────────────────────┘
```
The optimized prompt trusts the model to figure out *how* to audit the code; it merely defines the rules of the game and the shape of the victory condition.

---

## 4. The Declarative Contract Structure

Unlike frameworks like CREATE or Progressive Disclosure, which generate heavily structured multi-part blueprints, Reasoning-Aware targets an intentionally spartan schema:

| Field | Type | Purpose in Optimization |
|---|---|---|
| `absolute_task` | string | The pure objective stated as an imperative (No context, no fluff). |
| `hard_constraints` | list[str] | Absolute boundaries, deliberately stripped of any CoT prompts. |
| `output_format` | string | The required payload schema. |

> **Why so lean?** Reasoning models use token volume as "thinking space". Giving them massive, verbose system prompts reduces their available latent capacity to actually solve the problem. The goal is the absolute minimum instructions necessary for determinism.

---

## 5. How It Works: The Algorithm

### High-Level Flow

Reasoning-Aware avoids multi-pass rewriting to minimize API drift on complex tasks. It focuses purely on extraction, normalization, and assembly.

```
┌─────────────────────────────────────────────────────────────────┐
│               REASONING-AWARE ALGORITHM FLOW                    │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │  INPUT                               │
  │  OptimizationRequest                 │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 1: STRIP & EXTRACT            │
  │  LLM → strict JSON extraction        │
  │                                      │
  │  Extracts:                           │
  │  • absolute_task                     │
  │  • hard_constraints (MINUS CoT rules)│
  │  • output_format                     │
  │                                      │
  │  ❌ Parse fails? → One repair retry  │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 2: NORMALIZE                  │
  │  Ensure strings are strings, rules   │
  │  are lists, format is string-coerced │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 3: THE THREE TIERS            │
  │  Direct programmatic assembly        │
  │                                      │
  │  ┌─────────┐ ┌──────────┐ ┌───────┐ │
  │  │CONSERV- │ │STRUCTURED│ │ADVANC-│ │
  │  │ATIVE    │ │          │ │ED     │ │
  │  │         │ │          │ │       │ │
  │  │Task →   │ │Task →    │ │Strict │ │
  │  │Rules →  │ │Format →  │ │no-CoT │ │
  │  │Format   │ │Rules     │ │mandate│ │
  │  └────┬────┘ └────┬─────┘ └───┬───┘ │
  │       │           │           │     │
  └───────┴───────────┴───────────┴──────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 4: QUALITY GATE               │
  │  Internal judge critiques variants   │
  └──────────────────────────────────────┘
```

### Pseudo-code

```python
def reasoning_aware_optimize(request):
    extraction_prompt = build_extraction_prompt_strip_cot(request.raw_prompt)

    # 1. Extract Schema with Provider-Specific Structured Hints
    ext_payload = llm_call(
        prompt=extraction_prompt, 
        response_format=get_structured_response_hint(request.provider)
    )
    
    # 1B. Retry Loop
    try:
        data = parse_json(ext_payload)
    except JSONError:
        data = parse_json(llm_call(repair_prompt=ext_payload))

    # 2. Normalize Types
    task = normalize_str(data["absolute_task"])
    rules = normalize_list(data["hard_constraints"])
    fmt = normalize_str(data["output_format"])

    # 3. Assemble Declarative Variants
    v1 = assemble_conservative(task, rules, fmt)
    v2 = assemble_structured(task, rules, fmt)
    v3 = assemble_advanced(task, rules, fmt, forbid_explanations=True)

    # 4. Quality Gate
    response = build_variants([v1, v2, v3])
    return quality_gate(response, request)
```

---

## 6. The Three Optimization Tiers

```
┌──────────────────────────────────────────────────────────────┐
│  THE THREE TIERS                                             │
└──────────────────────────────────────────────────────────────┘

  CONSERVATIVE ─────────────────────────────────────────────────
  
  What it does:
  • Emits the prompt in standard logical order: Objective → 
    Constraints → Output Format.
  
  Best for: Minor architectural cleanup where the model generally 
  succeeds but the original prompt was messy.
  
  ──────────────────────────────────────────────────────────────

  STRUCTURED ───────────────────────────────────────────────────
  
  What it does:
  • Reverses ordering for Format Primacy: Objective → Output 
    Format Contract → Constraints.
  
  Best for: Standard production deployment for data extraction, 
  where schema stability is the most frequent point of failure.
  
  ──────────────────────────────────────────────────────────────

  ADVANCED ─────────────────────────────────────────────────────
  
  What it does:
  • All STRUCTURED benefits, plus:
  • Inserts the Explanation Suppressor: an aggressive "Emit ONLY 
    the output format without conversational preamble, without 
    showing your reasoning steps, and without explanation."
  
  Best for: High-throughput API loops where "thinking bleed" 
  (the model returning prose before the JSON) breaks parsers.
  
  ──────────────────────────────────────────────────────────────
```

---

## 7. Provider-Aware JSON Extraction

Because Reasoning-Aware uses programmatic text-assembly rather than an LLM rewrite loop (to maintain maximum spartan efficiency), the initial extraction pass *must* be perfect. 

To guarantee this, the extractor leverages specific native features of the underlying `provider` passing through the request:
- **OpenAI:** Uses strict `response_format = { type: "json_schema", strict: true }` to force exactly the 3 extracted keys.
- **Google:** Submits `response_format = { type: "json_schema" }` compatible with Gemini.
- **Anthropic / Others:** Relies on robust regex and AST-parsing coercion via `json_extractor.py`.

---

## 8. The Quality Gate

The internal judge evaluates the assembled variants with criteria tailored specifically against test-time reasoning constraints:
- **Did any CoT remain?** Does the prompt still contain instructions like "first do X, then do Y"? (If so, the judge strips it out).
- **Is the format binding?** Is the output schema isolated effectively?

If `quality_gate_mode` is enabled, the judge will aggressively delete procedural fluff from the variants.

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
        │   → selects reasoning_aware FIRST if:
        │     is_reasoning_model == True 
        │     (Takes precedence over all other framework rules)
        │
        ▼
  OptimizerFactory.get_optimizer("reasoning_aware")
        │
        ▼
  reasoning_aware_optimizer.py  ◄─── Core logic
  ReasoningAwareOptimizer
        │
        ├── _extract_reasoning_sections()
        │
        ├── _structured_response_format_for_provider()
        │
        └── _refine_variants_with_quality_critique()
```

---

## 10. Configuration and Tuning

### Parameter Reference

| Parameter | Location | Tuning Advice |
|---|---|---|
| `extraction_max_tokens` | Hardcoded inside `reasoning_aware_optimizer.py` (2048) | Rarely needs tuning unless the `raw_prompt` is thousands of tokens long, requiring a larger extraction context. |
| `quality_gate_mode` | Request-level | Keep it to `sample_one_variant` (typically Advanced) to ensure the Explanation Suppressor holds firm against your specific model. |

---

## 11. When to Use Reasoning-Aware (and When Not To)

### Strong Default For:

```
✅  Any prompt sent to OpenAI o1, o1-mini, o3-mini.
✅  Any prompt sent to DeepSeek R1 or QwQ.
✅  Tasks where the model keeps printing "Here is my step 
    by step thought process..." right before emitting JSON.
```

### Consider Alternatives When:

```
⚠️  You are using standard GPT-4o, Claude 3.5, or Gemini Pro. 
    Reasoning-Aware will actively prevent these models from "thinking",
    making them perform WORSE on complex tasks.
⚠️  You actually want the model to output a CoT trajectory for 
    audit logging. Use CoT Ensemble or KERNEL instead.
```

---

## 12. Diagnosing Common Failures

| Symptom | Most Likely Cause | Where to Investigate |
|---|---|---|
| Output still includes reasoning steps | Model ignoring the suppressor command | Tweak the `forbid_explanations` clause in the Advanced template assembly. |
| Model hallucinates wildly | Raw prompt completely relied on the user's manual logic, which this framework stripped out. | The user's prompt needs more hard constraints, not more logic. Review `raw_prompt` and `hard_constraints` extraction. |
| Extraction fails (JSON Error) | Provider ignored structured hints | Review `json_extractor.py` and the `_structured_response_format_for_provider()` dictionary mappings. |

---

## 13. Performance Playbook

**Tip 1: Do not use this framework on non-reasoning models.**
Removing Cot instructions from GPT-4o will dramatically lower performance on math and logic. APOST's auto-router explicitly safeguards this by only assigning this framework if `is_reasoning_model` is `True`. 

**Tip 2: Trust the Model's Search Policy.**
If an o1 model fails your Reasoning-Aware prompt, your instinct will be to tell it *how* to solve the problem. Suppress that instinct. Add **tests** and **negative constraints** instead. (e.g. Instead of "Check if X=Y", write "Constraint: Fail the analysis if X is not equal to Y").

---

## 14. Future Directions

1. **Test-Driven Assertions:** Extend the Advanced tier to generate assertable Python or Regex checks that the model is commanded to virtually "test" its own output against before returning.
2. **Configuration Overrides:** Centralize the extraction token budgets inside `optimizer_configuration.py` alongside the other frameworks for runtime observability.
3. **Implicit Variable Injection:** Support the `input_variables` mapping standard across the exact same layer format used by progressive and kernel, adding a minor layer of templating capability.

---

## 15. References

1. **OpenAI o1 Developer Guidance (2024).** OpenAI documentation outlining best practices for inference-time compute models (avoiding CoT meta-prompting, maintaining declarative constraints).
2. **Liu, N. F., et al. (2023).** "Lost in the Middle: How Language Models Use Long Contexts." *arXiv:2307.03172.* — Basis for structure primacy formatting.
3. **DeepSeek R1 Technical Report (2025).** Contextual verification that extended reasoning models degrade when forced into explicit user-designed CoT chains.
4. **APOST Internal Documentation:** `APOST_v4_Documentation.md` and `backend/app/services/optimization/frameworks/reasoning_aware_optimizer.py`.

---

*Reasoning-Aware Optimization is part of the APOST prompt optimization suite. For framework selection guidance, see the auto-router documentation in `framework_selector.py`.*
