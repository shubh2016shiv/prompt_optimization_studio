# OPRO: Optimization by PROmpting
### *Empirical, Trajectory-Based Prompt Search*

> **Who this guide is for:** Advanced developers and researchers who need machine-learned prompts rather than heuristic rewrites. This guide explains how APOST executes DeepMind's OPRO algorithm—treating prompt engineering as a black-box machine learning search problem. Read top-to-bottom for the full mental model.

---

## Table of Contents

1. [What Problem Does OPRO Solve?](#1-what-problem-does-opro-solve)
2. [The Research Foundations](#2-the-research-foundations)
3. [The Core Mental Model](#3-the-core-mental-model)
4. [The Data Requirement](#4-the-data-requirement)
5. [How It Works: The Algorithm](#5-how-it-works-the-algorithm)
6. [The Three Optimization Tiers](#6-the-three-optimization-tiers)
7. [The Quality Gate](#7-the-quality-gate)
8. [Implementation Architecture](#8-implementation-architecture)
9. [Configuration and Tuning](#9-configuration-and-tuning)
10. [When to Use OPRO (and When Not To)](#10-when-to-use-opro-and-when-not-to)
11. [Diagnosing Common Failures](#11-diagnosing-common-failures)
12. [Performance Playbook](#12-performance-playbook)
13. [Future Directions](#13-future-directions)
14. [References](#14-references)

---

## 1. What Problem Does OPRO Solve?

### The Intuition Failure Problem

Structural frameworks like KERNEL or XML Structured Bounding are built on **human intuition**. We *assume* that separating constraints from context makes a prompt better. We *assume* that adding XML tags improves format adherence. Most of the time, this intuition is correct. 

But for highly complex reasoning tasks, math problems, or specific classification edges, human intuition fails. A prompt that looks "ugly" or "poorly structured" to a human might unexpectedly score 95% on an evaluation dataset, while a pristine, structured prompt scores 70%.

When a task requires maximum mathematical performance on a rigid test set, you should not rely on structural heuristics. You must treat the prompt as a hyperparameter and optimize it empirically.

> **Mental Model — The Linting Tool vs. Gradient Descent:** KERNEL is a code linter. It makes your code clean, readable, and structurally sound. OPRO is gradient descent. It doesn't care if the prompt is beautiful or intuitive; it only cares that it minimizes the loss function over a training dataset.

### What OPRO Produces
Rather than parsing your prompt into a blueprint and rewriting it once, OPRO runs a multi-iteration loop. A "meta-prompter" generates multiple candidate prompts, tests them against a dataset of actual test cases, records their scores, and uses that history (the trajectory) to generate the next batch of prompts. It emits the empirical winners.

---

## 2. The Research Foundations

**The finding:** LLMs can optimize their own prompts if they are fed a trajectory of past attempts and their corresponding empirical scores. The model learns to identify which phrases correlate with high task scores and iteratively climbs the discovery gradient.
**The source:** Yang et al. (2023), "Large Language Models as Optimizers" (DeepMind). 
**How APOST operationalizes this:** The `OproTrajectoryOptimizer` maintains a list of `OproTrajectoryEntry` objects (Prompt + Empirical Score). It embeds the top-scoring historical prompts into a massive Meta-Prompt, asking the target LLM to find the hidden pattern and propose 10 new variations. Following the DeepMind paper, it evaluates these proposals recursively.

---

## 3. The Core Mental Model

### The Meta-Prompt

The engine behind OPRO is the Meta-Prompt. The Meta-Prompt is a huge system instruction sent to the LLM during the optimization loop that looks conceptually like this:

```text
You are an optimizer. Your goal is to maximize the score on a task. 
Here are some examples of the task (Input -> Expected Output).

Here is the history of prompts you have tried, sorted by score:
- Score 40%: "Solve this problem."
- Score 65%: "Think step by step and solve this problem."
- Score 85%: "Let's work this out logically, verify your answer, and output JSON."

Notice that adding verification and JSON formatting improved the score.
Generate 10 NEW prompts that explore this direction to achieve a higher score.
```

The LLM acts as the search algorithm, extrapolating from the trajectory to find the global maximum.

---

## 4. The Data Requirement

### The Strict Contract

Because OPRO relies on empirical scoring, **it cannot run without data**.

Unlike KERNEL, which can optimize a prompt in a vacuum, a request to the OPRO framework **MUST** include an `evaluation_dataset` inside the `OptimizationRequest`.

An evaluation dataset is a list of `{input, expected_output, evaluation_criteria}` objects. When OPRO proposes a candidate prompt, it runs the candidate against this dataset (using the `TaskLevelEvaluationService`) to generate the integer score that drives the trajectory.

| What happens if you run OPRO without a dataset? | 
|---|
| The framework will immediately abort and fallback to a default prompt. Empirical optimization requires an evaluation metric. |

---

## 5. How It Works: The Algorithm

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                           OPRO ALGORITHM LOOP                   │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │  INITIALIZATION                      │
  │  Subset eval dataset for speed;      │
  │  Score raw prompt to seed trajectory │
  └───────────────┬──────────────────────┘
                  │
  ┌───────────────▼──────────────────────┐◄───────┐
  │  PROPOSAL PHASE                      │        │
  │  Meta-prompter generates 10 new      │        │
  │  candidate prompts based on the      │        │
  │  current trajectory history.         │        │
  └───────────────┬──────────────────────┘        │
                  │                               │
  ┌───────────────▼──────────────────────┐        │
  │  EVALUATION PHASE                    │        │
  │  For each candidate:                 │        │
  │  Run against Eval Dataset.           │        │
  │  Calculate success coverage (0-100)  │        │
  └───────────────┬──────────────────────┘        │
                  │                               │
  ┌───────────────▼──────────────────────┐        │
  │  UPDATE PHASE                        │        │
  │  Add candidates and scores to the    │        │
  │  trajectory. Sort by score.          │        │
  └───────────────┬──────────────────────┘        │
                  │                               │
                  ├───────────────────────────────┘
          (Loop N Iterations)

                  ▼
  ┌──────────────────────────────────────┐
  │  SELECTION                           │
  │  Extract bottom, median, and peak    │
  │  scorers for the 3 final variants.   │
  └──────────────────────────────────────┘
```

---

## 6. The Three Optimization Tiers

Because OPRO searches an empirical space, it maps the required 3 output variants differently than structural frameworks. Instead of varying by "rigidity," the variants represent different points on the discovery curve.

```
┌──────────────────────────────────────────────────────────────┐
│  THE THREE TIERS (OPRO MAPPING)                              │
└──────────────────────────────────────────────────────────────┘

  CONSERVATIVE (The Baseline) ──────────────────────────────────
  
  Selection: The highest scoring candidate from the *first* 
  iteration of the loop.
  
  Meaning: The easiest low-hanging fruit. Provides a safe 
  improvement without overfitting to the small training subset.
  
  ──────────────────────────────────────────────────────────────

  STRUCTURED (The Stable Median) ───────────────────────────────
  
  Selection: The median-scoring candidate among the top quartile 
  of all generated prompts.
  
  Meaning: A highly successful prompt that avoids the extreme 
  edge-case overfitting sometimes seen in the absolute peak.
  
  ──────────────────────────────────────────────────────────────

  ADVANCED (The Absolute Peak) ─────────────────────────────────
  
  Selection: The highest scoring prompt discovered across the 
  entire trajectory history.
  
  Meaning: The mathematical champion. Often contains bizarre, 
  unintuitive phrases that empirically coerce the best alignment 
  from the target model.
  
  ──────────────────────────────────────────────────────────────
```

---

## 7. The Quality Gate

For OPRO, the APOST Quality Gate behaves slightly differently. 

Since OPRO prompts are mathematically derived and evaluated against ground truth, running a secondary LLM as a "Judge" to rewrite the prompt for structural aesthetics is counter-productive (this would risk breaking the prompt's empirical calibration).

When OPRO returns variants, the `_refine_variants_with_quality_critique` layer:
- **WILL** critique the prompt and append the analysis metadata.
- **WILL NOT** rewrite the prompt, regardless of the `quality_gate_mode`. The mathematical trajectory score is preserved.

---

## 8. Implementation Architecture

### Codebase Map

```
┌────────────────────────────────────────────────────────────────┐
│  CODEBASE INTEGRATION                                          │
└────────────────────────────────────────────────────────────────┘

  OptimizationRequest (must contain evaluation_dataset)
        │
        ├── framework_selector.py
        │   → selects opro when:
        │     task_type == "math" OR "classification"
        │     AND eval_dataset is present & large enough
        │
        ▼
  opro_trajectory_optimizer.py 
  OproTrajectoryOptimizer
        │
        ├── _format_trajectory_for_meta_prompt()
        │
        ├── _propose_candidate_prompts() ◄── LLM Call (Proposer)
        │
        └── _score_candidate_prompt()    ◄── TaskLevelEvalService
                  │
                  └── (Uses internal LLM evaluator or exact match)
```

---

## 9. Configuration and Tuning

### Parameter Reference

OPRO is highly compute-intensive. Its parameters live in `optimizer_configuration.py` and dictate the cost ceiling of the search loop.

| Parameter | Default | Tuning Advice |
|---|---|---|
| `OPRO_DEFAULT_ITERATION_COUNT` | 5 | The number of search loops. Raise to 10 for massive, complex tasks, but expect a huge latency/cost penalty. |
| `OPRO_CANDIDATES_PER_ITERATION`| 8 | How many prompts the meta-prompter proposes per loop. |
| `OPRO_MAX_TRAINING_CASES` | 10 | To prevent evaluating 8 candidates against 1,000 dataset rows per loop (8,000 LLM calls), APOST limits the training batch. |
| `OPRO_PROPOSAL_TEMPERATURE` | `0.8` | Must be high. The meta-prompter needs high entropy to explore the search space. |

---

## 10. When to Use OPRO (and When Not To)

### Strong Default For:

```
✅  Rigid classification tasks (e.g., Sentiment Analysis, 
    PII redaction) with clear right/wrong answers.
✅  Mathematical or algorithmic reasoning chains.
✅  Tasks with a large, high-quality test dataset available.
✅  When human-engineered prompts have hit a performance plateau.
```

### Consider Alternatives When:

```
⚠️  There is no evaluation dataset (OPRO cannot run).
⚠️  The task relies on stylistic creativity or tone (Subjective 
    metrics break empirical scoring).
⚠️  Low-latency optimizations (OPRO search loops can take minutes).
⚠️  Cost is highly constrained (1 loop = 1 meta-call + N eval calls).
```

---

## 11. Diagnosing Common Failures

| Symptom | Most Likely Cause | Where to Investigate |
|---|---|---|
| Trajectory scores stay flat | The meta-prompter lacks enough dataset examples to infer the pattern. | Increase `OPRO_MAX_TRAINING_CASES` or check if the dataset is ambiguous. |
| Advanced variant looks bizarre | Overfitting to the small training subset. | This is an expected mathematical behavior. Choose the Structured variant if readability matters. |
| API Rate Limit Errors | The evaluation loop exceeds burst limits. | Implement backoff in `TaskLevelEvaluationService`. |

---

## 12. Performance Playbook

**Tip 1: Curate "Hard" Evaluation Cases.**
Your optimization is only as good as the dataset driving it. If your training subset only includes "easy" cases, OPRO will quickly score 100% and the search will stagnate. Manually select edge-cases for your `evaluation_dataset`.

**Tip 2: Isolate the Search Model from the Eval Model.**
In `OptimizationRequest`, you can specify a cheaper model (like Claude Haiku) for the `TaskLevelEvaluationService` but use a powerful model (like Claude Sonnet 3.5) for the Meta-Prompter proposing the candidates. This reduces the cost of the evaluation loop without damaging the logic of the search.

---

## 13. Future Directions

1. **Batched Evaluations:** Transition `_score_candidate_prompt` to use Provider-native batching (like the OpenAI Batch API) for massively parallel, low-cost trajectory scoring.
2. **Multi-Objective Trajectory:** Currently OPRO scores purely on task success. Extend the trajectory space into a Pareto front balancing `score` vs `token_length` to penalize the meta-prompter for creating 5,000-token system prompts.
3. **Cross-Model Distillation:** Let GPT-4 act as the meta-prompter proposing candidates, but evaluate the trajectory by running the candidates against an open-source 8B model. The result is an optimized prompt that forces a weak model to act like a strong system.

---

## 14. References

1. **Yang, C., et al. (2023).** "Large Language Models as Optimizers." *DeepMind, arXiv:2309.03409.* — Foundational paper defining the OPRO algorithm and the meta-prompt structure.
2. **Pryzant, R., et al. (2023).** "Automatic Prompt Optimization with 'Gradient Descent' and Beam Search." *arXiv:2305.03495.* — Supports the necessity of iterative scoring using small evaluation subsets.
3. **APOST Internal Code:** `backend/app/services/optimization/frameworks/opro_trajectory_optimizer.py`.

---

*OPRO is part of the APOST prompt optimization suite. For prompt engineering tasks lacking strict evaluation data, consider structural frameworks like KERNEL or CREATE.*
