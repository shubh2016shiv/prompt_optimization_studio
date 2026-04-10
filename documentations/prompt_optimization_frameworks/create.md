# CREATE: A Comprehensive Guide to Prompt Optimization
### *Character, Request, Examples, Adjustments, Type of Output, Extras*

> **Who this guide is for:** Both newcomers who want to understand how to balance creative freedom with structural reliability in prompts, and seasoned engineers who want to understand CREATE's deep rewrite pipeline, its implementation logic, and its production trade-offs. Read top-to-bottom for the full mental model, or jump to any section independently.

---

## Table of Contents

1. [What Problem Does CREATE Solve?](#1-what-problem-does-create-solve)
2. [The Research Foundations](#2-the-research-foundations)
3. [The Core Mental Model](#3-the-core-mental-model)
4. [The Six Pillars Explained](#4-the-six-pillars-explained)
5. [How It Works: The Algorithm](#5-how-it-works-the-algorithm)
6. [The CREATE Blueprint](#6-the-create-blueprint)
7. [The Three Optimization Tiers](#7-the-three-optimization-tiers)
8. [The Quality Gate](#8-the-quality-gate)
9. [Implementation Architecture](#9-implementation-architecture)
10. [Configuration and Tuning](#10-configuration-and-tuning)
11. [When to Use CREATE (and When Not To)](#11-when-to-use-create-and-when-not-to)
12. [Diagnosing Common Failures](#12-diagnosing-common-failures)
13. [Performance Playbook](#13-performance-playbook)
14. [Future Directions](#14-future-directions)
15. [References](#15-references)

---

## 1. What Problem Does CREATE Solve?

### The "Creative Chaos" Problem

While frameworks like KERNEL and XML Structured Bounding are excellent for rigid, analytical tasks (like extraction and routing), they can over-constrain tasks that require nuance, tone, and stylistic execution. 

However, raw "creative" prompts are notoriously fragile in production. They blur together:
- **Tone vs. Rules:** "Write a fun email but don't promise refunds" mixes persona with a hard constraint.
- **Intent vs. Format:** "Summarize this into a dramatic 3-paragraph JSON" muddles the structural contract completely.
- **Demonstrations vs. Requirements:** Examples are provided, but the model doesn't know if it should copy the *style* of the example or the *content* of the example.

This blurring causes a high rate of format violations, persona drift, and ignored safety rules when deployed at scale.

> **Mental Model — The Method Actor and the Director:** A raw prompt treats the LLM like an amateur actor: "Just go out there and be funny, but make sure you hit your marks and don't swear." CREATE acts as a professional director assigning a role. It separates the character (the persona), the script (the request), the blocking constraints (adjustments), and the camera setup (type of output) into explicit, distinct categories.

### What CREATE Produces

CREATE takes a sprawling, mixed-intent prompt and restructures it into six explicit pillars that separate creative expression from deterministic constraints. This ensures the output remains expressive and stylistically aligned while adhering to rigid production formats.

---

## 2. The Research Foundations

CREATE is grounded in research on how Large Language Models separate stylistic emulation from semantic reasoning.

### 2.1 Persona Adoption and Instruction Bleed

**The finding:** LLMs instruction-tuned with RLHF are highly capable of adopting personas ("act as a Pirate"), but maintaining that persona increases cognitive load and often causes the model to "bleed" out of its constraints or forget the primary task.
**How CREATE operationalizes this:** By structurally isolating the `Character` from the `Adjustments` (constraints). When the persona is explicitly separated from the operational rules, the model is less likely to prioritize tone over compliance.

### 2.2 Demonstration Anchoring (Few-Shot Prompting)

**The finding:** Providing explicit examples (even just one or two) anchors both style and format far more effectively than zero-shot instructions. (Brown et al., 2020)
**How CREATE operationalizes this:** The `Examples` pillar is a dedicated structural section. This forces the optimization rewrite to clarify exactly *what* the example is demonstrating (e.g., "Note how this example uses a specific tone, but does not use the actual data you should use").

### 2.3 Explicit Output Contracts

**The finding:** Bounding the output space (e.g., "provide exactly three sentences") significantly reduces hallucination and verbosity drift.
**How CREATE operationalizes this:** The `Type of Output` pillar explicitly separates the content requirements from the schema requirements, ensuring downstream parsers don't break.

---

## 3. The Core Mental Model

### Expressiveness + Reliability

Most prompt engineers believe there is a direct trade-off between how creative a prompt is and how reliable it is. CREATE proves this false by using **containment**.

You can let a model be as creative, verbose, or stylistically unique as necessary *provided* those instructions are contained within the `Character` and `Request` pillars, while the `Adjustments` and `Type of Output` pillars remain rigidly deterministic.

```
┌────────────────────────────────────────────────────────┐
│  THE CREATE CONTAINMENT STRATEGY                       │
│                                                        │
│  [ EXPRESSIVE ZONE ]                                   │
│  Character: Be warm, empathetic, and slightly poetic.  │
│  Request:   Write a welcoming onboarding email.        │
│  Examples:  "Welcome aboard, voyager of the stars..."  │
│                                                        │
│  [ DETERMINISTIC ZONE ]                                │
│  Adjustments:    MUST NOT offer discounts.             │
│                  MUST reference the user_name variable.│
│  Type of Output: JSON {"subject": str, "body": str}    │
│  Extras:         If user_name is missing, use "friend".│
└────────────────────────────────────────────────────────┘
```

---

## 4. The Six Pillars Explained

The acronym CREATE corresponds to the six structural elements the framework enforces.

### C — Character
**Role:** The persona, perspective, or expertise the assistant must adopt.
**Prevents:** Tone drift, generic "AI-sounding" responses, and inconsistent voice.

### R — Request
**Role:** The single bounded task objective. What explicitly needs to be done.
**Prevents:** Scope creep and multi-objective confusion.

### E — Examples
**Role:** Reference patterns, demonstrations, or exemplars.
**Prevents:** Formatting mismatches and stylistic misunderstandings.

### A — Adjustments
**Role:** Hard constraints, MUST rules, and MUST NOT behaviors.
**Prevents:** Hallucination, ignored rules, and business logic violations.

### T — Type of Output
**Role:** The explicit structural contract (e.g., markdown, JSON, byte-limits).
**Prevents:** Unparseable results and downstream integration failures.

### E — Extras
**Role:** Safety bounds, failure-mode handling, and edge-cases.
**Prevents:** Confident failures when data is missing or ambiguous.

---

## 5. How It Works: The Algorithm

### High-Level Flow

The CREATE pipeline performs a deep extraction followed by objective-specific rewrites. It does not simply paste the original text under headings.

```
┌─────────────────────────────────────────────────────────────────┐
│                    CREATE ALGORITHM FLOW                        │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │  STAGE 1: ENRICH                     │
  │  Merge gap-interview answers into    │
  │  the raw prompt to fill missing intent│
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 2: BLUEPRINT PARSE            │
  │  LLM → strict JSON extraction        │
  │                                      │
  │  Extracts the 6 pillars PLUS:        │
  │  • forbidden_behaviors (MUST NOT)    │
  │  • verification_checks               │
  │                                      │
  │  ❌ Parse fails? → Use default       │
  │     conservative blueprint           │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 3: TIERED DEEP REWRITES       │
  │  3 parallel full rewrites            │
  │                                      │
  │  ┌─────────┐ ┌──────────┐ ┌───────┐ │
  │  │CONSERV- │ │STRUCTURED│ │ADVANC-│ │
  │  │ATIVE    │ │          │ │ED     │ │
  │  │         │ │          │ │       │ │
  │  │Pillar   │ │MUST/MUST │ │Strict │ │
  │  │alignment│ │NOT,      │ │valid- │ │
  │  │         │ │execution │ │ation &│ │
  │  │         │ │choreogr- │ │anti-  │ │
  │  │         │ │aphy      │ │halluc │ │
  │  └────┬────┘ └────┬─────┘ └───┬───┘ │
  │       │           │           │     │
  │  ❌fail?      ❌fail?     ❌fail?   │
  │       ↓           ↓           ↓     │
  │  Deterministic template fallback      │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 4: INJECT VARIABLES           │
  │  Append {{input_variables}} block    │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 5: QUALITY GATE               │
  │  Internal judge critiques variants   │
  └──────────────────────────────────────┘
```

### Pseudo-code

```python
def create_optimize(request):
    # Stage 1: Enrich
    enriched = integrate_gap_answers(request)

    # Stage 2: Parse Blueprint
    blueprint = llm_parse_json(enriched, schema=CREATE_SCHEMA)
    # Falls back to _default_blueprint() on error

    # Stage 3: Deep Rewrites
    rewritten = {}
    for tier in ["conservative", "structured", "advanced"]:
        try:
            rewritten[tier] = llm_rewrite(
                raw_prompt=enriched,
                blueprint=blueprint,
                objective=TIER_OBJECTIVES[tier]
            )
        except Exception:
            rewritten[tier] = deterministic_fallback_create(blueprint, tier=tier)

    # Stage 4: Inject Variables
    for tier in rewritten:
        rewritten[tier] = inject_input_variables(rewritten[tier], request)

    # Stage 5: Quality Gate
    response = build_variants(rewritten)
    return quality_gate(response, request)
```

---

## 6. The CREATE Blueprint

Before rewriting, the optimizer extracts an intermediate representation (the blueprint) that maps the raw text into the six pillars plus two critical safety fields.

### Blueprint Fields

| Field | Pillar | Purpose |
|---|---|---|
| `character` | Character | The persona to adopt. |
| `request` | Request | The primary objective. |
| `examples` | Examples | References or few-shot templates. |
| `adjustments` | Adjustments | Rules that must be followed. |
| `type_of_output` | Output | Schema, format, and structure. |
| `extras` | Extras | Edge-case behavior and context scope. |
| `forbidden_behaviors` | (Safety) | Explicit MUST NOT actions derived from implied bounds. |
| `verification_checks` | (Validation) | Conditions to check before emitting the final text. |

> **Why extract `forbidden_behaviors` separately?** Many users write rules like "Ensure the email is polite." The LLM parser converts this implicit boundary into a formal forbidden behavior: "MUST NOT use confrontational language." This gives the rewrite passes stronger guardrails to work with.

---

## 7. The Three Optimization Tiers

Like all APOST frameworks, CREATE generates three distinct prompt architectures from the blueprint.

```
┌──────────────────────────────────────────────────────────────┐
│  THE THREE TIERS                                             │
└──────────────────────────────────────────────────────────────┘

  CONSERVATIVE ─────────────────────────────────────────────────
  
  What it does:
  • Reorganizes the prompt into the 6 pillars explicitly.
  • Cleans vague language while preserving exact original intent.
  
  Best for: Prompts that are mostly correct but need to be 
  cleaner and easier for humans to read and maintain.
  
  ──────────────────────────────────────────────────────────────

  STRUCTURED ───────────────────────────────────────────────────
  
  What it does:
  • All CONSERVATIVE benefits, plus:
  • Normalizes `adjustments` into strict MUST/MUST NOT lists.
  • Adds an explicit ordered execution choreography (e.g., "1. 
    Review request, 2. Apply persona, 3. Validate format").
  
  Best for: Production systems where the output must adhere to 
  strict business rules without losing tone.
  
  ──────────────────────────────────────────────────────────────

  ADVANCED ─────────────────────────────────────────────────────
  
  What it does:
  • All STRUCTURED benefits, plus:
  • Injects strict failure-resistant validation guards.
  • Explicitly advises the model to abstain rather than hallucinate 
    if required evidence is missing.
  • Generates a Claude prefill suggestion (if Anthropic).
  
  Best for: High-stakes applications where format fidelity and 
  truthfulness are non-negotiable.
  
  ──────────────────────────────────────────────────────────────
```

---

## 8. The Quality Gate

Because CREATE prompts are often used for text generation tasks that require stylistic finesse, the shared quality gate evaluates specific creative and structural metrics:

- Is the persona distinct and unambiguous?
- Are the constraints (MUST/MUST NOT) structurally separated from the stylistic instructions?
- Is the output format rigid enough to parse programmatically?
- (Advanced) Are the verification checks executable by the model?

If `quality_gate_mode` is set to `full` or `sample_one_variant`, the internal judge will enhance any variant that fails to meet these criteria.

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
        │   → selects create when:
        │     task_type == "creative"
        │     OR techniques include few_shot, persona_design
        │
        ▼
  OptimizerFactory.get_optimizer("create")
        │
        ▼
  create_optimizer.py  ◄─── Core logic lives here
  CreateOptimizer
        │
        ├── _parse_create_blueprint()
        │
        ├── _rewrite_with_create_objective()
        │
        ├── _fallback_create_prompt() (deterministic string logic)
        │
        └── _refine_variants_with_quality_critique()
```

### Fallback Guarantee
If the LLM rewrite fails, `_fallback_create_prompt()` explicitly serializes the parsed blueprint into a template:
```
CHARACTER: {character}
REQUEST: {request}
EXAMPLES:
- {example}
...
```
This guarantees that APOST will never throw an API error due to model output failure.

---

## 10. Configuration and Tuning

### Parameter Reference

| Parameter | Location | Tuning Advice |
|---|---|---|
| `MAX_TOKENS_COMPONENT_EXTRACTION` | `optimizer_configuration.py` | Lower if the parsed JSON incorporates too much raw text instead of summarizing constraints. |
| `MAX_TOKENS_CREATE_REWRITE` | `optimizer_configuration.py` | Turn down if the rewrite starts hallucinating instructions. Turn up if the Examples section is truncated. |
| `quality_gate_mode` | `OptimizationRequest` | Set to `sample_one_variant` for a balance of cost and high-quality outputs. |

---

## 11. When to Use CREATE (and When Not To)

### CREATE Is a Strong Default For:

```
✅  Copywriting, email generation, and creative drafting
✅  Tasks requiring a specific persona, tone, or perspective
✅  Prompts that rely heavily on few-shot examples
✅  User-facing chat agent system prompts
```

### Consider Alternatives When:

```
⚠️  The task is pure classification/extraction → KERNEL has lower 
    overhead and is less chatty.
⚠️  The prompt contains large multi-document contexts with high 
    injection risk → XML Structured Bounding offers superior 
    context isolation.
⚠️  The prompt requires complex multi-hop reasoning → CoT 
    Ensemble or Reasoning Aware provide better logical scaffolding.
```

---

## 12. Diagnosing Common Failures

| Symptom | Most Likely Cause | Where to Investigate |
|---|---|---|
| Persona isn't adopted | Missing from `character` parsing | `_parse_create_blueprint()`, raw prompt |
| Examples cause hallucination | Model copying content of examples rather than style | Add constraints to `extras` / `forbidden_behaviors` |
| Output format fails | `type_of_output` insufficiently explicit | Ensure quality gate is enabled to tighten schema |
| API 502 / Empty variants | Parse or rewrite LLMs returning invalid responses | Fallback logic triggering; check logs for model API errors |

---

## 13. Performance Playbook

**Tip 1: Make examples work for you, not against you.**
If your request contains examples, the CREATE parse will capture them. Ensure the original examples are high-quality, as the deeper rewrites will anchor heavily onto them to extrapolate the `Type of Output`.

**Tip 2: Use CREATE for Human-in-the-Loop workflows.**
Because CREATE's structure is extremely readable (compared to deeply nested XML or dense CoT trajectories), it is the best framework to choose if non-technical domain experts need to review and tweak the output variants manually after generation.

---

## 14. Future Directions

1. **Example Retrieval:** Integrate kNN semantic retrieval into the `Examples` pillar. Rather than hardcoding examples, the optimized prompt would include a placeholder that a runtime RAG system fills with the nearest-neighbor examples.
2. **Persona Consistency Linting:** Add deterministic validation checks ensuring that the rules established in `Character` are not directly violated by the `Adjustments` (e.g., "Speak like an aggressive pirate" vs. "MUST use corporate business English").
3. **Tone Calipers:** Generate variants not just by structural rigidity (the standard 3 tiers), but by tone variability (e.g., formal variant, casual variant, persuasive variant) while keeping constraints static.

---

## 15. References

1. **Brown, T., et al. (2020).** "Language Models are Few-Shot Learners." *NeurIPS 2020.* — Foundational paper for the necessity of the `Examples` pillar.
2. **APOST Internal Documentation:** `APOST_v4_Documentation.md` and `backend/app/services/optimization/frameworks/OPTIMIZERS.md`.
3. **Mishra, S., et al. (2022).** "Cross-Task Generalization via Natural Language Crowdsourcing Instructions." *ACL 2022.* — Demonstrates that explicit task boundaries (like separating persona from instruction) reduce error.

---

*CREATE is part of the APOST prompt optimization suite. For tasks where creative persona is unnecessary, consider the KERNEL framework. For framework selection guidance, see the auto-router documentation in `framework_selector.py`.*
