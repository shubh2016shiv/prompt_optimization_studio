# Overshoot/Undershoot Failure Mode Prevention
### *An Analytical Guardrail Injection Engine*

> **Who this guide is for:** Prompt engineers dealing with long-tail failure modes (like unexpected verbosity or missed edge cases) and backend developers who want to understand APOST's programmatic guardrail injection pipeline. Read top-to-bottom for the full mental model, or jump to any section independently.

---

## Table of Contents

1. [What Problem Does This Framework Solve?](#1-what-problem-does-this-framework-solve)
2. [The Research Foundations](#2-the-research-foundations)
3. [The Core Mental Model](#3-the-core-mental-model)
4. [The 10 Risk Dimensions](#4-the-10-risk-dimensions)
5. [How It Works: The Algorithm](#5-how-it-works-the-algorithm)
6. [The Three Optimization Tiers](#6-the-three-optimization-tiers)
7. [The Guardrail Library (Python Injection)](#7-the-guardrail-library-(python-injection))
8. [The Quality Gate](#8-the-quality-gate)
9. [Implementation Architecture](#9-implementation-architecture)
10. [Configuration and Tuning](#10-configuration-and-tuning)
11. [When to Use Overshoot/Undershoot (and When Not To)](#11-when-to-use-overshoot-undershoot-and-when-not-to)
12. [Diagnosing Common Failures](#12-diagnosing-common-failures)
13. [Performance Playbook](#13-performance-playbook)
14. [Future Directions](#14-future-directions)
15. [References](#15-references)

---

## 1. What Problem Does This Framework Solve?

### The Dual Failure Spectrum

Most prompt frameworks attempt to make the instructions "cleaner" and assume that will yield better results. However, LLM generation failures rarely fall into a single category of "bad instructions." Instead, they polarize into two distinct failure modes on a spectrum:

| Failure Mode | What It Looks Like | Why It Happens |
|---|---|---|
| **Overshoot** | The model generates 3 paragraphs when you wanted 1. It adds caveats ("As an AI...") or hallucinates extra details. | The prompt lacks length anchors, scope locks, and anti-hallucination bounds. The model defaults to maximum helpfulness/verbosity. |
| **Undershoot** | The model skips half the questions asked, drops schema fields, or gives shallow 1-sentence answers to complex logic problems. | The prompt lacks exhaustiveness requirements, depth floors, and explicit edge-case coverage rules. |

> **Mental Model — The Bumper Cars:** A raw prompt is a car driving down a wide highway with no lines. If the model steers left, it crashes into Overshoot (verbosity, hallucination). If it steers right, it crashes into Undershoot (skipping steps, lazy outputs). This optimizer acts as **highway guardrails** — it programmatically measures the risk of deviating from the center, and mathematically injects guards to bounce the model back into bounds.

### What the Engine Produces
Unlike KERNEL (an extraction/rewrite engine), this framework is an **Analytical Guardrail Injection Engine**. It uses an LLM to actively score the prompt across 10 failure risk dimensions, structurally rewrites the prompt, and then uses deterministic Python logic to inject curated, pre-written guardrails directly into the prompt to neutralize the highest-scoring risks.

---

## 2. The Research Foundations

**The finding:** Instruct-tuned models (RLHF) tend to systematically overshoot in conversational contexts (the "sycophancy" or "hyper-verbosity" effect) and undershoot in complex logic/extraction contexts (the "lazy output" effect). 
**The source:** Empirical observations in meta-prompting research architectures (Suzgun & Kalai, 2024; Anthropic's characterization of Claude's RLHF tuning).
**How APOST operationalizes this:** Instead of telling the LLM to rewrite the prompt to "be better," the framework forces an LLM sub-call to evaluate 10 fixed risk topologies (e.g., `enumeration_risk`, `completeness_risk`) on a 0-3 severity scale. It then matches those scores to a static Library of explicit countermeasures. By combining analytical evaluation with hard-coded Python string injection, the guardrails remain highly durable.

---

## 3. The Core Mental Model

### Analytical Scoring + Deterministic Injection

The most critical architectural decision in this framework is that **the LLM does not write the guardrails**. 

When an LLM is asked to write safety rules, it writes vague rules like "Ensure the output is not too long."
When Python injects a safety rule, it can inject a highly calibrated, aggressive constraint like: *"LENGTH CONSTRAINT: Prioritise precision over volume. Avoid restating the question or padding with filler."*

The LLM is only used as a scoring judge (to detect the risks) and a structural formatter (to clean the prompt body). The actual failure prevention mechanism happens purely in software logic.

---

## 4. The 10 Risk Dimensions

During the `Risk Analysis` phase, the raw prompt is mapped into a severity matrix. Each item is scored 0 (No Risk) to 3 (Critical Risk):

#### Overshoot Risks (Generating Too Much)
1. **Verbosity Risk**: No length/scope anchor.
2. **Hallucination Risk**: Broad topic without strong source grounding.
3. **Caveat Risk**: Ambiguous intent causing the model to hedge or add disclaimers.
4. **Tangent Risk**: Loose directives allowing the model to wander off-topic.
5. **Enumeration Risk**: List tasks without a hard upper bound.

#### Undershoot Risks (Generating Too Little)
6. **Completeness Risk**: Multiple tasks grouped together without an exhaustiveness requirement.
7. **Depth Risk**: Complex analysis requested but no "depth floor" anchor provided.
8. **Schema Risk**: Implicit structure requested but no explicit schema provided.
9. **Edge Case Risk**: Complex processes lacking explicit failure/edge handling.
10. **Reasoning Risk**: Nontrivial conclusions required without a "show your work" step.

---

## 5. How It Works: The Algorithm

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│     OVERSHOOT / UNDERSHOOT FAILURE PREVENTION PIPELINE          │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │  STAGE 1: RISK ANALYSIS (LLM Call)   │
  │  LLM evaluates raw prompt across 10  │
  │  dimensions, returning 0-3 scores    │
  │  and evidence matrices inside JSON.  │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 2: GUARD SELECTION (Python)   │
  │  Python logic maps the 0-3 scores    │
  │  to a library of text templates.     │
  │  Creates 3 sets of active guards.    │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 3: STRUCTURAL REWRITE (LLM)   │
  │  LLM reorganizes raw prompt into:    │
  │  Task, Context, Scope, Format.       │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 4: VARIANT ASSEMBLY (Python)  │
  │  Inject the structural components    │
  │  and the selected guards together.   │
  │                                      │
  │  ┌─────────┐ ┌──────────┐ ┌───────┐ │
  │  │CONSERV- │ │STRUCTURED│ │ADVANC-│ │
  │  │ATIVE    │ │          │ │ED     │ │
  │  │(Oversht │ │(Balanced │ │(Max   │ │
  │  │ Guards  │ │ Dual     │ │ Dual  │ │
  │  │ Only)   │ │ Guards)  │ │ +Echo)│ │
  │  └────┬────┘ └────┬─────┘ └───┬───┘ │
  └───────┴───────────┴───────────┴──────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 5: QUALITY GATE               │
  │  Internal judge critiques variants   │
  └──────────────────────────────────────┘
```

---

## 6. The Three Optimization Tiers

Because the Python engine knows the risk severity scores, it adjusts the activation threshold of the guards depending on the tier.

```
┌──────────────────────────────────────────────────────────────┐
│  THE THREE TIERS                                             │
└──────────────────────────────────────────────────────────────┘

  CONSERVATIVE ─────────────────────────────────────────────────
  
  Guard Activation: Only triggers on CRITICAL (severity=3).
  Guard Focus: Overshoot guards only.
  
  What it does: Lightly restructures the prompt and applies 
  a scope-lock or length-calibration to prevent the most 
  common issue: verbosity drift.
  
  Best for: Standard workflows where you just want to stop the 
  model from chattering, but don't want massive prompt overhead.
  
  ──────────────────────────────────────────────────────────────

  STRUCTURED ───────────────────────────────────────────────────
  
  Guard Activation: Triggers on MODERATE + CRITICAL (severity>=2)
  Guard Focus: Balanced Dual Guards (Overshoot & Undershoot).
  
  What it does: Completely structures the prompt and appends a 
  dedicated "### GENERATION GUARDRAILS" section injecting the 
  necessary templates for both ends of the failure spectrum.
  
  Best for: Most production data-processing pipelines.
  
  ──────────────────────────────────────────────────────────────

  ADVANCED ─────────────────────────────────────────────────────
  
  Guard Activation: Triggers on LOW+MODERATE+CRITICAL (severity>=1)
  Guard Focus: Aggressive Dual Guards + Constraint Recency Echo.
  
  What it does: Frames the entire prompt in highly aggressive 
  boundary blocks ("HARD LIMITS"). Injects nearly all triggering 
  guardrails, and uses RAL-Writer to restate them at the bottom.
  
  Best for: Highly complex, unregulated context windows facing 
  untrusted user inputs. Expected to produce very long system prompts.
  
  ──────────────────────────────────────────────────────────────
```

---

## 7. The Guardrail Library (Python Injection)

The strings injected by this framework are not hallucinated by an LLM on the fly. They are hardcoded inside `overshoot_undershoot_optimizer.py`. This ensures perfect determinism.

For example, if the LLM Risk Analyser produces a severity of `3` for `tangent_risk`, the Python engine intercepts this and prepares the `"scope_lock"` guard:

**Scope Lock Guard (Injected verbatim):**
> *"SCOPE CONSTRAINT: Restrict your response EXCLUSIVELY to the specific task described above. Do not discuss tangential topics, provide unsolicited background information, or speculate beyond the provided context."*

If `completeness_risk` scores a `2`, the Python engine prepares the `"exhaustiveness"` guard:

**Exhaustiveness Guard:**
> *"COMPLETENESS CONSTRAINT: You MUST address ALL sub-tasks, questions, or requirements stated in the prompt. Before finalising your response, verify that every explicitly requested element has been covered. An incomplete response is a failed response."*

---

## 8. The Quality Gate

The internal judge evaluates the assembled variants with specific criteria:
- Are the generated guardrails proportional to the task complexity?
- Did the structural rewrite accidentally strip out any original Context mapping?

Because the guards are deterministically injected, the Judge rarely flags them for removal, but may enhance the structural rewrite block preceding them.

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
        │   → selects overshoot_undershoot when:
        │     TCRTE overall score is mildly degraded (50-69) 
        │     AND complexity is standard (middle-ground 
        │     calibration task)
        │
        ▼
  OptimizerFactory.get_optimizer("overshoot_undershoot")
        │
        ▼
  overshoot_undershoot_optimizer.py  ◄─── Core logic
  OvershootUndershootOptimizer
        │
        ├── _analyse_failure_mode_risks() ◄── LLM Call (Analyser)
        │
        ├── _select_guards_for_tier()      ◄── Python selection
        │
        ├── _rewrite_prompt_with_structure() ◄── LLM Call (Rewriter)
        │
        ├── _assemble_variant_prompt()       ◄── Python assembly
        │
        └── _refine_variants_with_quality_critique()
```

---

## 10. Configuration and Tuning

### Parameter Reference

| Parameter | Location | Tuning Advice |
|---|---|---|
| `MAX_TOKENS_FAILURE_MODE_ANALYSIS` | `optimizer_configuration.py` | Governs the JSON extractor running the 0-3 severity matrix. Lower this if the LLM starts expanding on "evidence" for too long. |
| `MAX_TOKENS_COMPONENT_EXTRACTION` | `optimizer_configuration.py` | Governs the structural rewrite pass. |
| `_GUARD_ACTIVATION_THRESHOLD_...` | Hardcoded in the class. | Modify these integer constants (1, 2, 3) inside the class if you want the Conservative tier to trigger more easily. |

---

## 11. When to Use Overshoot/Undershoot (and When Not To)

### Strong Default For:

```
✅  Prompts that exhibit sycophancy (apologizing, caveats).
✅  Extraction tasks where the model frequently skips fields 
    (completeness failure).
✅  Tasks that behave inconsistently (sometimes perfect, 
    sometimes drifting into tangents).
```

### Consider Alternatives When:

```
⚠️  The prompt is designed for a persona/roleplay scenario 
    (The guards will make the bot sound robotic and overly precise). 
    Use CREATE instead.
⚠️  The task relies on a test-set of math/logic problems. 
    Use OPRO instead.
⚠️  The prompt requires complex routing. Use Progressive 
    Disclosure instead.
```

---

## 12. Diagnosing Common Failures

| Symptom | Most Likely Cause | Where to Investigate |
|---|---|---|
| Model continues to use "As an AI..." | The `anti_caveat` guard did not trigger. | The `_analyse_failure_mode_risks` call did not score `caveat_risk` high enough. Examine the raw prompt to see if intent was ambiguous. |
| Prompt gets extremely long | Advanced tier activated all 10 guards. | Use the Structured variant for balancing overhead vs safety. |
| API failures / Fallback triggered | First LLM failed to return the 10-key severity matrix JSON. | `_analyse_failure_mode_risks()` JSON coercion. |

---

## 13. Performance Playbook

**Tip 1: Look at the Variant Strategies Array.**
When you receive the `OptimizationResponse`, check the `techniques_applied` list or the metadata. Because this framework dynamically injects from a library, the metadata tells you *exactly* which guards fired. If `[Anti-Hallucination, Exhaustiveness Requirement]` fired, you know the analyzer flagged those specific risks in your raw prompt.

**Tip 2: Understand the Cost.**
Unlike simpler frameworks that do one LLM extraction pass, this framework does two: one for Risk Analysis (JSON), and one for Structural Rewriting (JSON). Be aware of the latency/cost implications.

---

## 14. Future Directions

1. **Custom Guard Libraries:** Allow users to define their own custom guard dictionaries inside `OptimizationRequest` (e.g., passing a company-specific `brand_safety` guard template to the Python injection engine).
2. **Post-Generation Linters:** Link the specific undershoot guards (like `schema_completeness`) to runtime validators, generating Python enforcement scripts matching the prompt constraints.
3. **Telemetry Tracking:** Track which specific guards trigger most frequently across an organization to identify widespread gaps in internal prompt engineering guidelines.

---

## 15. References

1. **Suzgun, M., & Kalai, A. T. (2024).** "Meta-Prompting: Enhancing Language Models with Task-Agnostic Scaffolding." *arXiv:2401.12954.* — Documents the pervasive tension between underspecification and overgeneration in zero-shot setups.
2. **Anthropic Safety and RLHF Research.** — Characterizations of sycophancy, "As an AI" caveats, and verbosity drift in instruction-tuned large models.
3. **APOST Internal Code:** `backend/app/services/optimization/frameworks/overshoot_undershoot_optimizer.py`.

---

*The Overshoot/Undershoot Failure Prevention Engine is part of the APOST prompt optimization suite. For framework selection guidance, see the auto-router documentation in `framework_selector.py`.*
