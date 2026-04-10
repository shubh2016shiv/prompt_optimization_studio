# TextGrad: Iterative Prompt Optimization
### *Automatic Differentiation via Text*

> **Who this guide is for:** Advanced users wanting to watch an LLM progressively debug its own prompt over multiple iterations. This guide explains how APOST replaces heuristic static-rules with a "gradient descent" loop—treating text critiques as mathematical gradients to iteratively repair a prompt. Read top-to-bottom for the full mental model.

---

## Table of Contents

1. [What Problem Does TextGrad Solve?](#1-what-problem-does-textgrad-solve)
2. [The Research Foundations](#2-the-research-foundations)
3. [The Core Mental Model](#3-the-core-mental-model)
4. [How It Works: The Iterative Loop](#4-how-it-works-the-iterative-loop)
5. [The Three Optimization Tiers](#5-the-three-optimization-tiers)
6. [Implementation Architecture](#6-implementation-architecture)
7. [Configuration and Tuning](#7-configuration-and-tuning)
8. [When to Use TextGrad (and When Not To)](#8-when-to-use-textgrad-and-when-not-to)
9. [Diagnosing Common Failures](#9-diagnosing-common-failures)
10. [Performance Playbook](#10-performance-playbook)
11. [References](#11-references)

---

## 1. What Problem Does TextGrad Solve?

### The Monolithic Rewrite Failure

Most prompt optimizers (like CREATE or KERNEL) operate using a **single-pass rewrite**. They parse the prompt, figure out what's wrong, and re-write the entire thing from scratch in a single LLM API call.

This runs into two major problems:
1. **The "Oops" Effect:** The LLM fixes the structure but accidentally deletes an essential fact from the original context because generating 1,000 perfect tokens in one pass is difficult.
2. **Local Maxima:** The prompt gets a little better, but because the LLM cannot test or "reflect" on the new version, it stops optimizing long before hitting peak performance.

### What TextGrad Produces

TextGrad abandons the single-pass rewrite. Instead, it places the prompt inside a multi-iteration refinement loop. Just like training a neural network, it calculates a "loss" (a textual critique), localises the "gradient" (finding exactly which lines need fixing), and performs an "update step" (rewriting *only* the broken lines). It repeats this loop multiple times, saving the checkpoint at each step.

---

## 2. The Research Foundations

**The finding:** LLMs are incredibly good at finding flaws in text, but terrible at rewriting huge documents without losing information. By treating text optimizations analogously to backpropagation in PyTorch—passing textual gradients (critiques) backwards to update specific parameters (text spans)—you can achieve SOTA performance on reasoning tasks without needing an empirical training dataset (like OPRO requires).
**The source:** Yuksekgonul et al. (Stanford, 2024), "TextGrad: Automatic Differentiation via Text."
**How APOST operationalizes this:** `textgrad_iterative_optimizer.py` implements a pure-Python, 3-iteration version of the Stanford algorithm. It avoids the heavy external library dependency of the official `textgrad` package, relying entirely on the target provider API key to run the Evaluate → Localise → Rewrite loop. 

---

## 3. The Core Mental Model

### Textual Backpropagation

> **Mental Model — Gradient Descent for Words:** In a neural network, if an image is misclassified, the mathematical "loss" flows backward through the network, tweaking the exact weights that caused the error. TextGrad does this with words. 

1. **Forward Pass:** The prompt is run through an internal Critic. The Critic generates the "Loss" (e.g., *"The tone rule on Line 4 is contradictory"*).
2. **Gradient Localization:** The loss is mathematically mapped to a specific parameter. (*"Target Line 4 for update"*).
3. **Update Step:** The specific parameter is altered. (*Line 4 is fixed. Rest of prompt untouched.*)

This surgical precision means your original context remains perfectly intact, completely eliminating the "Oops" deletion effect of single-pass frameworks.

---

## 4. How It Works: The Iterative Loop

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│     TEXTGRAD ITERATIVE OPTIMIZATION LOOP                        │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │  INITIALIZATION                      │
  │  Prompt_v0 = User Raw Prompt         │
  └───────────────┬──────────────────────┘
                  │
  ┌───────────────▼──────────────────────┐◄───────┐
  │  FORWARD PASS (Calculate Loss)       │        │
  │  LLM evaluates Prompt_v{n} against   │        │
  │  the TCRTE structural rubric.        │        │
  └───────────────┬──────────────────────┘        │
                  │                               │
  ┌───────────────▼──────────────────────┐        │
  │  BACKWARD PASS (Gradient Localise)   │        │
  │  LLM isolates the EXACT text spans   │        │
  │  that caused the loss logic.         │        │
  └───────────────┬──────────────────────┘        │
                  │                               │
  ┌───────────────▼──────────────────────┐        │
  │  UPDATE STEP (Parameter Rewrite)     │        │
  │  LLM rewrites ONLY the targeted      │        │
  │  spans. Leaves rest of text alone.   │        │
  │                                      │        │
  │  Prompt_v{n+1} is saved as checkpoint│        │
  └───────────────┬──────────────────────┘        │
                  │                               │
                  ├───────────────────────────────┘
            (Loop N Iterations)

                  ▼
  ┌──────────────────────────────────────┐
  │  CHECKPOINT MAPPING                  │
  │  Return history of updates.          │
  └──────────────────────────────────────┘
```

---

## 5. The Three Optimization Tiers

Because TextGrad outputs a historical trajectory of checkpoints, APOST naturally maps the 3 Required Variants to the chronological steps of the loop:

```
┌──────────────────────────────────────────────────────────────┐
│  THE THREE TIERS (CHECKPOINT MAPPING)                        │
└──────────────────────────────────────────────────────────────┘

  CONSERVATIVE ─────────────────────────────────────────────────
  
  Mapping: Result of Iteration 1 (Checkpoint 1).
  
  Meaning: The prompt has had the most glaring, obvious logical 
  failures surgically repaired, but is otherwise functionally 
  identical to your original input.
  
  ──────────────────────────────────────────────────────────────

  STRUCTURED ───────────────────────────────────────────────────
  
  Mapping: Result of Iteration 2 (Checkpoint 2).
  
  Meaning: The prompt has undergone secondary reflection. After 
  fixing the obvious errors, the Critic noticed deeper issues 
  (e.g., missing schema bindings) and applied a second layer 
  of polish. 
  
  ──────────────────────────────────────────────────────────────

  ADVANCED ─────────────────────────────────────────────────────
  
  Mapping: Result of Iteration N (Checkpoint 3).
  
  Meaning: The final Output. The Prompt has survived 3 full 
  evaluations and surgical rewrites. This represents the absolute 
  best the target LLM is capable of structurally engineering 
  without an empirical dataset.
  
  ──────────────────────────────────────────────────────────────
```

---

## 6. Implementation Architecture

### Codebase Map

```
┌────────────────────────────────────────────────────────────────┐
│  CODEBASE INTEGRATION                                          │
└────────────────────────────────────────────────────────────────┘

  execute_optimization_request()
        │
        ├── framework_selector.py
        │   → selects textgrad when:
        │     task_type is creative/reasoning AND the user 
        │     selects high-quality mode OR requests reflection.
        │
        ▼
  textgrad_iterative_optimizer.py 
  TextGradIterativeOptimizer
        │
        ├── LOOP START
        │   ├── _evaluate_prompt_against_tcrte_rubric() ◄── LLM Call
        │   │
        │   ├── _localise_gradient_to_text_spans()      ◄── LLM Call
        │   │
        │   └── _rewrite_targeted_spans()               ◄── LLM Call
        │
        └── _refine_variants_with_quality_critique()
```

---

## 7. Configuration and Tuning

### Parameter Reference

Configuration values located in `optimizer_configuration.py`:

| Parameter | Default | Tuning Advice |
|---|---|---|
| `TEXTGRAD_DEFAULT_ITERATION_COUNT` | 3 | Controls how many loops occur. Increasing this to 5 makes the Advanced tier slightly more polished but massively spikes latency (15 total sequence LLM calls). Do not raise above 5, as the gradients begin to plateau. |
| `MAX_TOKENS_TEXTGRAD_EVALUATION` | 1000 | The token budget for the Critic producing the Loss function. |

---

## 8. When to Use TextGrad (and When Not To)

### Strong Default For:

```
✅  Massive, context-heavy prompts where you are terrified that 
    an aggressive optimizer (like SAMMO or Progressive) will 
    accidentally delete your crucial knowledge base.
✅  Tasks where human intuition has failed and you want the LLM 
    to figure out what is wrong via programmatic reflection.
```

### Consider Alternatives When:

```
⚠️  Low Latency environments. (TextGrad requires 9 synchronous 
    LLM calls by default. It can take ~30-60 seconds to return).
⚠️  You have a rigid Evaluation Dataset. If you have ground-truth 
    test cases, use OPRO instead. TextGrad guesses at improvements; 
    OPRO proves them mathematically.
```

---

## 9. Diagnosing Common Failures

| Symptom | Most Likely Cause | Where to Investigate |
|---|---|---|
| The 3 variants are identical. | The Critic did not flag any violations during Iteration 1. | The raw prompt was already incredibly strong against the TCRTE rubric, resulting in $0$ gradient loss. Use KERNEL instead. |
| The prompt changed entirely. | Gradient localization failed. | In Step 3, the LLM was supposed to target specific lines, but instead rewrote the whole string. Review `MAX_TOKENS_TEXTGRAD_UPDATE`. |
| Timeout Error. | The 9 LLM calls exceeded the HTTP timeout threshold. | Lower the `TEXTGRAD_DEFAULT_ITERATION_COUNT` or use a faster Provider. |

---

## 10. Performance Playbook

**Tip 1: Use TextGrad as an Educational Tool.**
When TextGrad finishes, it attaches an `iteration_history` to the metadata (or viewable in backend logs). This history explicitly states what the Critic found wrong at each step. Reading the TextGrad loss gradient is one of the fastest ways to level-up your own prompt engineering skills, because the LLM is telling you exactly what human logic it couldn't understand.

**Tip 2: Pair with Fast Models.**
Because TextGrad relies on iterative reflection, you do not need extremely smart models to run it. A cheap, incredibly fast model (like Claude 3.5 Haiku) running a 3-iteration TextGrad loop will almost always produce a better system prompt than an expensive model (like Claude 3.5 Sonnet) running a single 1-shot KERNEL pass.

---

## 11. References

1. **Yuksekgonul, M., et al. (Stanford, 2024).** "TextGrad: Automatic Differentiation via Text." *arXiv:2406.07496.* — Extablishes the conceptual algorithm for mapping PyTorch backpropagation to text spans.
2. **APOST Internal Code:** `backend/app/services/optimization/frameworks/textgrad_iterative_optimizer.py`.

---

*TextGrad is part of the APOST prompt optimization suite. For topological optimizations focusing on token efficiency, see SAMMO.*
