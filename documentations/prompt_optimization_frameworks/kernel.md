# KERNEL: A Comprehensive Guide to Prompt Optimization
### *Keep It Simple, Explicit, Narrow, Known Success, Logical Order*

> **Who this guide is for:** Both newcomers who have never heard of prompt engineering frameworks and seasoned engineers who want to understand KERNEL's theory, mechanics, and production trade-offs. Read top-to-bottom for the full mental model, or jump to any section independently.

---

## Table of Contents

1. [What Problem Does KERNEL Solve?](#1-what-problem-does-kernel-solve)
2. [The Research Foundations](#2-the-research-foundations)
3. [The KERNEL Mental Model](#3-the-kernel-mental-model)
4. [The Five Pillars Explained](#4-the-five-pillars-explained)
5. [How KERNEL Works: The Algorithm](#5-how-kernel-works-the-algorithm)
6. [The Blueprint: KERNEL's Decomposition Schema](#6-the-blueprint-kernels-decomposition-schema)
7. [The Three Optimization Tiers](#7-the-three-optimization-tiers)
8. [The Quality Gate](#8-the-quality-gate)
9. [Implementation Architecture](#9-implementation-architecture)
10. [Configuration and Tuning](#10-configuration-and-tuning)
11. [When to Use KERNEL (and When Not To)](#11-when-to-use-kernel-and-when-not-to)
12. [Diagnosing Common Failures](#12-diagnosing-common-failures)
13. [Performance Playbook](#13-performance-playbook)
14. [Future Directions](#14-future-directions)
15. [References](#15-references)

---

## 1. What Problem Does KERNEL Solve?

### The Core Failure Mode of Production Prompts

Most prompt failures in production are not caused by the model being "wrong." They are caused by the prompt being **underspecified**. The model is doing exactly what it was asked to do — the problem is that the prompt didn't ask clearly enough.

Here are the four failure archetypes KERNEL is designed to eliminate:

| Failure Type | What It Looks Like | Why It Happens |
|---|---|---|
| **Unbounded** | Model writes a 5-page essay when you wanted a 3-sentence summary | Multiple implied objectives, no prioritization |
| **Implicit constraints** | Model occasionally ignores a rule that "feels obvious" from context | Rules embedded in tone, not stated explicitly |
| **Unverifiable** | Output looks plausible but is subtly wrong | No definition of what "correct" actually means |
| **Format-weak** | Model returns JSON sometimes, prose other times | Output schema never explicitly described |

> **Mental Model — The Contractor Analogy:** Imagine hiring a contractor to renovate your kitchen. If you say "make it nice," you'll get whatever they think is nice. If you say "replace the countertops with white quartz, DO NOT touch the cabinets, and finish by Friday," you get what you wanted. KERNEL is the process of turning "make it nice" prompts into contractor-grade specifications.

### What KERNEL Produces

KERNEL takes a raw, ambiguous prompt and rewrites it into a **lean, enforceable instruction contract** that:

1. States exactly one bounded objective
2. Makes every constraint explicit (MUST / MUST NOT format)
3. Defines verifiable success criteria
4. Specifies the output format precisely
5. Orders instructions so critical constraints appear early and steps are logically sequenced

---

## 2. The Research Foundations

KERNEL is an engineering synthesis, not a single paper's algorithm. Its design choices are grounded in well-established findings from NLP and cognitive science research.

### 2.1 Instruct-Tuning and Explicit Constraints

**The finding:** Instruction-tuned models (fine-tuned to follow directives) reliably follow *explicit* rules but often miss *implicit* ones embedded in prose tone.

**The source:** Ouyang et al. (2022) demonstrated in InstructGPT that RLHF-trained models show dramatically improved adherence to stated user intentions. The operative word is *stated* — rules that are written down, not inferred.

**How KERNEL operationalizes this:** By converting ambiguous guidelines into binary MUST/MUST NOT statements. "Be concise" becomes "MUST NOT exceed 150 words." The model has a clear, checkable rule instead of a subjective heuristic.

### 2.2 The "Lost in the Middle" Effect

**The finding:** Language models with long context windows are significantly worse at using information placed in the *middle* of the context. Performance is highest for content at the very beginning or end of the prompt.

**The source:** Liu et al. (2023) showed that retrieval accuracy for facts placed mid-document drops substantially compared to facts placed at document boundaries. This generalizes to instruction following: constraints buried in paragraph 4 of a long prompt are more likely to be violated than constraints in paragraph 1.

**How KERNEL operationalizes this:** By enforcing a compact, logically ordered prompt structure where the most critical constraints appear early — before the model has processed enough tokens to begin "forgetting" them in attention. The framework also strips unnecessary prose that would push critical instructions toward the middle.

```
┌─────────────────────────────────────────┐
│  ATTENTION STRENGTH ACROSS CONTEXT       │
│                                          │
│  High ████████                           │
│        ║      ║                          │
│        ║      ╚════════════╗             │
│  Low   ║                  ║             │
│        ║   MIDDLE ZONE    ║             │
│        ║  (constraints    ║             │
│        ║   often lost)    ║             │
│        ║                  ╚═════ High   │
│       START              END            │
│  (task &            (output format)     │
│  constraints)                           │
└─────────────────────────────────────────┘

  ↑ KERNEL places critical rules HERE     
    to exploit high-attention zones        
```

### 2.3 KISS Principle and Cognitive Load Reduction

**The finding:** Shorter, simpler instructions reduce the surface area for misinterpretation. This maps to the software engineering KISS (Keep It Simple, Stupid) principle applied to prompt design.

**The reasoning:** Every additional sentence in a prompt is an opportunity for ambiguity or contradiction. KERNEL optimizes for *reliability per token* — maximizing how much correct behavior each token of instruction buys you. This is why KERNEL is lower cost and lower latency than iterative optimization methods like TextGrad, while still producing meaningful improvements.

---

## 3. The KERNEL Mental Model

### Think of a Prompt as a Contract, Not a Conversation

A common beginner mistake is writing prompts as if you're having a casual conversation: "Hey, can you summarize this article? Keep it short and make sure it's accurate." This works sometimes, but it's fragile.

KERNEL asks you to switch mental models: **a prompt is a formal specification**, like a function signature or a legal contract. It has:

- A single, well-defined purpose (the function's purpose)
- Explicit preconditions (MUST rules)
- Explicit prohibitions (MUST NOT rules)
- A defined return type (output format)
- Acceptance criteria (success definition)

> **Mental Model — The Type System Analogy:** In programming, a dynamically-typed language (Python without type hints) will run your code even if you pass the wrong type — and fail mysteriously at runtime. A statically-typed language (TypeScript, Rust) forces you to be explicit upfront, catching errors before they happen. KERNEL applies static typing to prompts. "Be accurate" is dynamic typing. "MUST cite the source document for every factual claim" is static typing.

### The Reliability-Per-Token Principle

KERNEL's design goal is not the most creative prompt or the longest prompt — it's the *most reliable* prompt per unit of tokens. This leads to several counterintuitive design choices:

- **Shorter is often better.** Every token that doesn't add a new constraint or clarify the task is a token that could confuse the model.
- **Explicit beats implicit.** "Don't make things up" is implicit. "MUST NOT include any information not present in the provided source text" is explicit.
- **Narrow beats broad.** A prompt that does one thing well is more reliable than a prompt that does three things adequately.

---

## 4. The Five Pillars Explained

The acronym KERNEL maps to five engineering principles. Each addresses a specific failure mode.

### K — Keep It Simple

**What it prevents:** Overly complex, ambiguous task descriptions that leave the model uncertain about what to do.

**How it works:** KERNEL distills the prompt to one clear, primary objective. All secondary goals either become constraints or are removed. The task statement should be unambiguous enough that a new hire could execute it without asking clarifying questions.

**Example transformation:**
```
BEFORE: "Analyze this customer feedback and identify themes, 
         sentiment, actionable insights, and also flag any 
         urgent issues and suggest product improvements."

AFTER:  "Extract the top 3 recurring complaint themes from 
         the customer feedback below."
```

The "after" version can be verified. The "before" version produces different outputs every run because six different things were asked for.

### E — Explicit Constraints

**What it prevents:** Ignored constraints, scope drift, and the model making "reasonable" assumptions that diverge from intent.

**How it works:** Every rule gets its own MUST or MUST NOT line. No rules hidden in prose. No rules implied by examples. If it matters, it's stated as a directive.

**Example transformation:**
```
BEFORE: "Try to keep your response professional and not too long."

AFTER:  "MUST: Use formal business English throughout.
         MUST NOT: Exceed 200 words in the response."
```

### R — Reasonable Narrow Scope

**What it prevents:** Hallucinated expansions, the model "helpfully" doing things you didn't ask for, and outputs that go beyond the task boundaries.

**How it works:** The task statement explicitly defines what is *in scope*, and constraints define what is *out of scope*. The model has a bounded problem, not an open-ended one.

**Mental Model — Bounding Box:** Think of scope as a bounding box drawn around the problem. KERNEL draws that box explicitly. Without it, the model expands to fill whatever space it perceives as reasonable — which may be much larger than you intended.

### N — Known Success Criteria

**What it prevents:** "Looks plausible" outputs that pass without being correct, and outputs that are technically compliant but useless.

**How it works:** KERNEL adds a verifiable success definition. Instead of relying on the model's judgment of what "good" means, success criteria are stated as checkable conditions.

```
BEFORE: (no success criteria — just trust the model)

AFTER:  "A correct response:
         ✓ Contains exactly 3 themes, each with a label and 1-sentence explanation
         ✓ Each theme is grounded in at least one direct quote from the text
         ✓ Total length is under 150 words"
```

### L — Logical Order

**What it prevents:** Missed steps, inconsistent outputs, and the model executing instructions out of sequence.

**How it works:** Instructions are sequenced so that context-setting comes first, constraints come before execution steps, and format specification comes last (so it's fresh in the model's attention when generating output). This exploits the "Lost in the Middle" effect intentionally — the most important rules go where attention is highest.

**Canonical KERNEL Order:**
```
1. Role / persona (if needed)
2. Primary task (single objective)
3. MUST constraints
4. MUST NOT constraints
5. Step-by-step execution (if multi-step)
6. Success criteria
7. Output format specification
8. Input variables / data
```

---

## 5. How KERNEL Works: The Algorithm

### High-Level Flow

The KERNEL optimization pipeline has five stages. Below is a step-by-step diagram followed by explanation of each stage.

```
┌──────────────────────────────────────────────────────────────────┐
│                    KERNEL ALGORITHM FLOW                         │
└──────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────┐
  │  INPUT                              │
  │  OptimizationRequest                │
  │  • raw_prompt                       │
  │  • gap_interview_answers            │
  │  • input_variables                  │
  │  • provider + model_id              │
  └──────────────┬──────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │  STAGE 1: ENRICH                    │
  │  Merge gap-interview answers        │
  │  into the raw prompt                │
  │                                     │
  │  Purpose: Fill implicit knowledge   │
  │  gaps before optimization begins    │
  └──────────────┬──────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │  STAGE 2: PARSE BLUEPRINT           │
  │  LLM → strict JSON extraction       │
  │                                     │
  │  Extracts:                          │
  │  • task (single objective)          │
  │  • context                          │
  │  • positive_constraints (MUST)      │
  │  • negative_constraints (MUST NOT)  │
  │  • success_criteria                 │
  │  • output_format                    │
  │                                     │
  │  ❌ Parse fails?                    │
  │  → Use conservative defaults        │
  └──────────────┬──────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │  STAGE 3: TIERED REWRITES           │
  │  3 parallel rewrite passes          │
  │                                     │
  │  ┌──────────┐ ┌──────────┐ ┌──────┐ │
  │  │CONSERV-  │ │STRUCTURED│ │ADVAN-│ │
  │  │ATIVE     │ │          │ │CED   │ │
  │  │          │ │          │ │      │ │
  │  │Simplify, │ │Add MUST/ │ │Add   │ │
  │  │1 objecti-│ │MUST NOT, │ │valid-│ │
  │  │ve, remove│ │strict    │ │ation,│ │
  │  │ambiguity │ │ordering  │ │anti- │ │
  │  │          │ │          │ │halluc│ │
  │  └────┬─────┘ └────┬─────┘ └──┬───┘ │
  │       │            │           │    │
  │  ❌ fail?     ❌ fail?    ❌ fail? │
  │  ↓              ↓             ↓     │
  │  Deterministic fallback rewrite     │
  └──────────────┬──────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │  STAGE 4: INJECT VARIABLES          │
  │  Append {{input_variables}} block   │
  │  in provider-appropriate format     │
  └──────────────┬──────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │  STAGE 5: QUALITY GATE              │
  │  Internal judge model critiques     │
  │  each of the 3 variants             │
  │                                     │
  │  Modes:                             │
  │  • full: critique + enhance all 3   │
  │  • sample_one: enhance 1 variant    │
  │  • critique_only: score, no enhance │
  │  • off: skip gate entirely          │
  └──────────────┬──────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │  OUTPUT                             │
  │  OptimizationResponse               │
  │  • 3 PromptVariant objects          │
  │  • PromptQualityEvaluation          │
  │  • OptimizationRunMetadata          │
  └─────────────────────────────────────┘
```

### Pseudo-code

```python
def kernel_optimize(request):
    # Stage 1: Enrich with gap interview answers
    enriched = integrate_gap_answers(
        request.raw_prompt, 
        request.answers, 
        request.gap_data
    )

    # Stage 2: Parse into stable blueprint anchors
    blueprint = llm_parse_json(enriched, schema=KERNEL_SCHEMA)
    # If parse fails → blueprint uses conservative defaults

    # Stage 3: Three tiered rewrite passes
    variants = {}
    for tier in ["conservative", "structured", "advanced"]:
        try:
            variants[tier] = llm_rewrite(
                raw_prompt=enriched,
                blueprint=blueprint,
                objective=TIER_OBJECTIVES[tier],
            )
        except Exception:
            # Deterministic fallback guarantees a result
            variants[tier] = deterministic_fallback(blueprint, tier=tier)

    # Stage 4: Inject variable contract
    for tier in variants:
        variants[tier] = inject_input_variables(
            variants[tier], 
            request.input_variables, 
            request.provider
        )

    # Stage 5: Quality gate (shared across all frameworks)
    response = build_response(variants)
    return quality_gate(response, request)
```

### The Deterministic Fallback

One of KERNEL's most important engineering decisions is the **fallback guarantee**. If an LLM call fails — malformed JSON, empty response, network error — the pipeline does not crash. Instead, it reassembles the blueprint deterministically into a structured prompt using string templates.

This guarantee means KERNEL can be deployed in production without special-casing LLM failures. The worst-case output is still a coherent, structured prompt. The API always returns three variants.

```
┌─────────────────────────────────────────────────┐
│  FALLBACK BEHAVIOR                              │
│                                                 │
│  Blueprint parsed ──────────────────► Normal   │
│  successfully                          rewrite  │
│                                                 │
│  Blueprint parse fails ─────────────► Use      │
│                                        defaults │
│                                                 │
│  Rewrite LLM call fails ────────────► Template  │
│                                        assembly  │
│                                                 │
│  Both fail ─────────────────────────► Minimal   │
│                                        structured│
│                                        reformat  │
└─────────────────────────────────────────────────┘

  In all cases: 3 PromptVariants are returned.
  The API never returns an empty or error response.
```

---

## 6. The Blueprint: KERNEL's Decomposition Schema

Before rewriting, KERNEL parses the raw prompt into a structured set of "anchors." These anchors are the stable intermediate representation that all three tier rewrites are built from.

### Blueprint Fields

| Field | KERNEL Pillar | What It Captures | Failure Prevented |
|---|---|---|---|
| `task` | Keep it Simple + Narrow | Single, bounded objective | Multiple competing goals |
| `context` | Keep it Simple | Background the model needs | Model making wrong assumptions |
| `positive_constraints` | Explicit | MUST rules (what must be true) | Ignored soft requirements |
| `negative_constraints` | Explicit | MUST NOT rules (what must not occur) | Scope creep, hallucination |
| `success_criteria` | Known Success | Verifiable pass/fail conditions | "Looks plausible" outputs |
| `output_format` | Logical Order | Schema / structure of response | Format inconsistency |

### How the Blueprint Is Extracted

The extraction is a single LLM call with a strict JSON schema. The model is instructed to decompose the enriched prompt into these fields — not summarize it, not paraphrase it, but categorize its existing content into the appropriate slots.

If the extraction returns malformed JSON, `json_extractor` applies strict coercion. If coercion fails, KERNEL proceeds with conservative defaults (empty constraints, inferred task).

> **Why not just use the raw prompt?** The blueprint extraction step serves two purposes: (1) it surfaces implicit structure that was hidden in prose — making it visible so the rewrite passes can enforce it — and (2) it provides a stable intermediate that all three tier rewrites share, ensuring the variants are all solving the same problem despite having different optimization objectives.

---

## 7. The Three Optimization Tiers

KERNEL produces three variants of the optimized prompt, each rewritten with a different objective. This is not cosmetic — each tier produces a meaningfully different prompt that trades different properties.

```
┌──────────────────────────────────────────────────────────┐
│  THE THREE TIERS: WHAT EACH OPTIMIZES FOR               │
└──────────────────────────────────────────────────────────┘

  CONSERVATIVE ──────────────────────────────────────────
  
  Goal: Minimal viable improvement
  
  Technique:
  • Simplify language (remove jargon, hedge words)
  • Narrow to one objective
  • Remove redundant or contradictory sentences
  
  Best for: Prompts where the current structure is mostly 
  correct but needs polish; low-risk production systems
  
  Trade-off: Less defensive, but more readable
  
  ─────────────────────────────────────────────────────────

  STRUCTURED ─────────────────────────────────────────────
  
  Goal: Explicit contract enforcement
  
  Technique:
  • Convert all rules to MUST / MUST NOT statements
  • Impose canonical KERNEL ordering
  • Make output schema explicit
  
  Best for: Prompts where constraint adherence is the 
  primary failure mode; tool-use / extraction tasks
  
  Trade-off: Slightly more tokens, much higher reliability
  
  ─────────────────────────────────────────────────────────

  ADVANCED ───────────────────────────────────────────────
  
  Goal: Failure resistance and hallucination prevention
  
  Technique:
  • All of STRUCTURED, plus:
  • Explicit validation checks ("Before responding, verify...")
  • Anti-hallucination guards ("MUST NOT state anything 
    not in the provided source")
  • Self-check instructions embedded in prompt
  
  Best for: High-stakes outputs, customer-facing content,
  factual accuracy requirements
  
  Trade-off: Most tokens, most defensive
  
  ─────────────────────────────────────────────────────────
```

### Why Three Full Rewrites, Not One Prompt with Three Tones?

A common shortcut is to take one base prompt and prepend "be concise" vs. "be thorough" to create "variants." KERNEL explicitly avoids this anti-pattern because it produces **superficially different but substantively identical** prompts.

Each KERNEL tier is a full end-to-end rewrite from the blueprint. The conservative tier may not include validation checks at all. The advanced tier may restructure the entire prompt to put self-verification steps before output generation. These are genuinely different instruction architectures, not the same prompt with different adjectives.

---

## 8. The Quality Gate

After the three tier variants are generated, KERNEL applies a shared quality gate that is framework-agnostic (it runs after KERNEL, OPRO, TextGrad, etc.).

### What the Quality Gate Does

```
┌────────────────────────────────────────────────────────┐
│  QUALITY GATE PIPELINE                                 │
└────────────────────────────────────────────────────────┘

  3 PromptVariants
        │
        ▼
  ┌─────────────────────────────────────┐
  │  CRITIQUE PHASE                     │
  │  Internal judge model evaluates     │
  │  each variant on:                   │
  │  • Constraint completeness          │
  │  • Format clarity                   │
  │  • Instruction specificity          │
  │  • Risk of scope drift              │
  └──────────────┬──────────────────────┘
                 │
                 ▼
         Passes threshold?
           /            \
         YES              NO
          │                │
          ▼                ▼
    Keep variant     ENHANCEMENT PHASE
    as-is            LLM rewrites variant
                     targeting flagged issues
                          │
                          ▼
                    Updated variant
                          │
                          ▼
  ┌─────────────────────────────────────┐
  │  SCORING + METADATA                 │
  │  PromptQualityEvaluation attached   │
  │  OptimizationRunMetadata recorded   │
  └─────────────────────────────────────┘
```

### Quality Gate Modes

| Mode | What Happens | When to Use |
|---|---|---|
| `full` | Critique + enhance all 3 variants | Production-grade output |
| `sample_one_variant` | Enhance only 1 variant | Cost-sensitive, still want one gated result |
| `critique_only` | Score all, enhance none | Auditing / benchmarking |
| `off` | Skip entirely | Early development iteration loops |

> **Practical advice:** Use `off` during development when you're iterating on the raw prompt and just want to see KERNEL's first-pass output. Switch to `sample_one_variant` for staging and `full` for production. The quality gate adds latency and cost proportional to the number of variants enhanced.

---

## 9. Implementation Architecture

### Codebase Map

```
┌──────────────────────────────────────────────────────────────┐
│  CODEBASE INTEGRATION                                        │
└──────────────────────────────────────────────────────────────┘

  HTTP Request
  POST /api/optimize  OR  POST /api/optimize/jobs
       │
       ▼
  optimization_pipeline.py
  execute_optimization_request()
       │
       ├── framework_selector.py (if framework="auto")
       │   select_framework()  →  may return "kernel"
       │
       ▼
  base.py
  OptimizerFactory.get_optimizer("kernel")
       │
       ▼
  kernel_optimizer.py  ◄─── Core KERNEL logic lives here
  KernelOptimizer
       │
       ├── _parse_kernel_components()   ──► LLMClient
       │                                ──► json_extractor
       │
       ├── _rewrite_with_kernel_objective()  ──► LLMClient
       │
       ├── _fallback_rewrite()  (deterministic, no LLM)
       │
       ├── shared_prompt_techniques (gap answers, variables)
       │
       └── _refine_variants_with_quality_critique()
           [inherited from BaseOptimizerStrategy]
                │
                └──► LLMClient (judge model)
```

### Key Files

| File | Role |
|---|---|
| `kernel_optimizer.py` | Core strategy: parse, rewrite, fallback |
| `base.py` | OptimizerFactory registry + quality gate base class |
| `framework_selector.py` | Auto-router that selects KERNEL for simple tasks |
| `optimization_pipeline.py` | Orchestration: request → variants → response |
| `optimizer_configuration.py` | Token budget constants |
| `optimization.py` (routes) | Synchronous `POST /api/optimize` |
| `optimization_jobs.py` (routes) | Async job queue endpoint |

### API Invocation

**Synchronous (for short prompts, testing):**
```http
POST /api/optimize
{
  "framework": "kernel",
  "raw_prompt": "Summarize the document for me",
  "provider": "anthropic",
  "model_id": "claude-3-5-sonnet-20241022",
  "quality_gate_mode": "full"
}
```

**Auto-select (let the router decide):**
```http
POST /api/optimize
{
  "framework": "auto",
  "raw_prompt": "Classify this support ticket into one of: billing, technical, account",
  ...
}
```
For classification, extraction, and routing tasks, the auto-router is likely to select KERNEL as the default lower-cost framework.

**Async (for long-running optimization jobs):**
```http
POST /api/optimize/jobs   →   returns job_id
GET  /api/optimize/jobs/{job_id}   →   poll for result
```

---

## 10. Configuration and Tuning

### Parameter Reference

| Parameter | Where Set | What It Controls | Tuning Advice |
|---|---|---|---|
| `MAX_TOKENS_COMPONENT_EXTRACTION` | `optimizer_configuration.py` | Token budget for blueprint JSON parse | Lower if blueprint extraction is too verbose |
| `MAX_TOKENS_KERNEL_REWRITE` | `optimizer_configuration.py` | Token budget per tier rewrite | Lower to prevent verbosity drift; raise if rewrites are truncating |
| `quality_gate_mode` | `OptimizationRequest` | How many variants get judged and enhanced | See quality gate modes table above |
| `provider` | `OptimizationRequest` | Which LLM provider runs parse + rewrites | Match to your production model |
| `model_id` | `OptimizationRequest` | Specific model for optimization | Use the same model you'll deploy with |

### The Verbosity Drift Problem

One subtle failure mode: KERNEL rewrites can become *longer* than the original prompt, adding hedges and caveats that reduce reliability. If you observe this, lower `MAX_TOKENS_KERNEL_REWRITE`. The goal is reliability per token, not completeness per rewrite.

---

## 11. When to Use KERNEL (and When Not To)

### KERNEL Is a Strong Default For:

```
✅  Classification tasks (route this ticket to: A, B, or C)
✅  Extraction tasks (pull these fields from this document)
✅  Format-sensitive tasks (generate JSON matching this schema)
✅  Short-to-medium prompts without an evaluation dataset
✅  Production prompts where consistency matters more than creativity
✅  Early-stage optimization before empirical testing infrastructure exists
```

### Consider Alternatives When:

```
⚠️  You have a labeled evaluation dataset → OPRO may give better 
    empirically-validated improvements

⚠️  The task requires open-ended creativity → KERNEL's narrowing 
    may reduce output diversity in ways you don't want

⚠️  The prompt is already highly optimized → diminishing returns; 
    empirical methods that test against real outputs add more value

⚠️  You need iterative gradient-like optimization → TextGrad 
    (though KERNEL is much cheaper and faster per iteration)
```

### KERNEL vs. Other Frameworks

| Dimension | KERNEL | OPRO | TextGrad |
|---|---|---|---|
| Requires eval dataset | No | Yes | Yes |
| Cost per optimization | Low | Medium–High | High |
| Latency | Low | Medium | High |
| Best for | Reliability, format tasks | Accuracy on measurable metrics | Complex multi-turn tasks |
| Output count | 3 variants | Variable | 1 optimized prompt |
| Deterministic fallback | Yes | No | No |

---

## 12. Diagnosing Common Failures

| Symptom | Most Likely Cause | Where to Investigate |
|---|---|---|
| `502` JSON parse error on component extraction | Model returned malformed JSON during blueprint parse | `json_extractor.py`, `_parse_kernel_components()` |
| All 3 variants look nearly identical | Tier rewrite objectives not enforcing differentiation | `_KERNEL_REWRITE_PROMPT`, tier objective strings |
| High cost and latency | Quality gate on `full` mode with large token budgets | `quality_gate_mode` setting, token budget constants |
| Prompt ignores `{{input_variables}}` | Missing `input_variables` field or provider formatting mismatch | `inject_input_variables_block()`, provider format spec |
| Variants are longer than original prompt | Verbosity drift in rewrite pass | Lower `MAX_TOKENS_KERNEL_REWRITE` |
| Fallback used for all 3 tiers | Model returning empty or malformed rewrites | LLM client logs, rewrite prompt formatting |

### How to Use the Local Test Script

For manual end-to-end verification without unit test overhead:

```bash
# Exercises full pipeline: LLM parse → rewrite → quality gate
python backend/test_optimizers_locally.py
```

This is useful when you've changed a rewrite prompt and want to see the actual model output before committing.

---

## 13. Performance Playbook

### Recommended Settings by Environment

| Environment | `quality_gate_mode` | `MAX_TOKENS_KERNEL_REWRITE` | Notes |
|---|---|---|---|
| **Development** | `off` | Default | Fast iteration; skip gate overhead |
| **Staging** | `sample_one_variant` | Default | One gated result for QA |
| **Production** | `full` | Tuned down | All 3 gated; lower tokens if verbosity drift observed |
| **Budget-constrained prod** | `sample_one_variant` | Lower | Balance quality vs. cost |

### Key Performance Tips

**Tip 1: Match `model_id` to your deployment model.** KERNEL rewrites are model-aware — a prompt optimized for GPT-4o may not perform identically on Claude Sonnet. Use the same provider and model you'll deploy with.

**Tip 2: Use `sample_one_variant` as your everyday default.** The advanced tier is typically the highest-quality variant. Sampling just that one for quality gating preserves most of the benefit at one-third the judge cost.

**Tip 3: Reduce `MAX_TOKENS_KERNEL_REWRITE` before raising it.** Most verbosity drift is caused by the rewrite model padding output. Lowering the budget forces the model to be concise — which is the goal. Only raise it if rewrites are visibly truncating important instructions.

**Tip 4: Prefer KERNEL over OPRO when you don't have an eval dataset.** OPRO is empirically superior *when you have labeled test cases to score against*. Without that, OPRO's optimization signal is noise. KERNEL's structural improvements are always valid regardless of whether you have evaluation data.

---

## 14. Future Directions

The following extensions preserve KERNEL's core principle of reliability per token:

### Hybrid KERNEL + Empirical Selection

Run KERNEL to generate the three candidate variants, then select the best one by scoring against a small set of labeled test cases (OPRO-style evaluation). This gives you KERNEL's structural improvements plus empirical validation, at lower cost than pure OPRO (since KERNEL narrows the candidate space before expensive evaluation).

### Constraint Canonicalization

Normalize MUST/MUST NOT constraints into a reusable policy format that can be applied across frameworks. This would allow constraints learned in one context (e.g., "never output PII") to be automatically injected into prompts across the system.

### Prompt Compression Pass

After KERNEL produces its output, apply a learned or heuristic compression method to reduce tokens without losing constraints. This addresses the tension between completeness (more instructions = more reliable) and the KISS principle (fewer tokens = lower drift risk).

### Deterministic Linting

Add static analysis to flag prompts before they enter KERNEL:
- Missing MUST/MUST NOT despite having implicit constraints
- Missing output schema
- Conflicting constraints (MUST be concise AND MUST include all details)
- Objectives that are actually multiple objectives disguised as one

---

## 15. References

1. **Liu, N. F., et al. (2023).** "Lost in the Middle: How Language Models Use Long Contexts." *arXiv:2307.03172.* — The primary empirical basis for KERNEL's constraint-first ordering strategy.

2. **Ouyang, L., et al. (2022).** "Training language models to follow instructions with human feedback." *NeurIPS 2022.* (InstructGPT) — Demonstrates that explicit rule statements dramatically improve adherence in instruction-tuned models.

3. **Mishra, S., et al. (2022).** "Cross-Task Generalization via Natural Language Crowdsourcing Instructions." *ACL 2022.* — Shows that constraint clarity in natural language instructions generalizes across task types.

4. **Wei, J., et al. (2022).** "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." *NeurIPS 2022.* — Supports KERNEL's logical ordering principle: sequenced steps improve structured output.

5. **Ye, X., et al. (2023).** "Prompt Engineering a Prompt Engineer." *arXiv:2311.05661.* — Documents how structured prompt decomposition (similar to KERNEL's blueprint) improves downstream task performance.

6. **APOST Internal Documentation:** `APOST_v4_Documentation.md` and `backend/app/services/optimization/frameworks/OPTIMIZERS.md`.

---

*KERNEL is part of the APOST prompt optimization suite. For framework selection guidance, see the auto-router documentation in `framework_selector.py`. For quality gate configuration details, see `BaseOptimizerStrategy` in `base.py`.*