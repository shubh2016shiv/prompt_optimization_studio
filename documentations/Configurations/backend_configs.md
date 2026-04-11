# APOST Backend Configuration Architecture and Tuning Guide

This document explains the backend configuration model for prompt optimization in APOST, with a focus on why each default value exists and what happens when you tune it.

It is written for three audiences at once:
- engineers implementing or debugging the optimization pipeline
- prompt engineers tuning quality, latency, and cost
- reviewers evaluating whether configuration choices are technically justified

## 1) What Problem This Configuration Solves

APOST runs multiple optimization frameworks (for example TextGrad, OPRO, CoRe, SAMMO) and each framework makes many language-model calls with different goals: extraction, critique, rewriting, scoring, and structural analysis.

Without centralized configuration, teams usually hit four failure modes:
- hidden magic numbers spread across modules
- unstable quality after ad-hoc tuning
- runaway token cost from unbounded sub-calls
- unclear ownership of trade-offs (quality vs latency vs cost)

The config system in `backend/app/config.py` addresses this by making runtime behavior explicit, validated, and environment-overridable via Pydantic Settings [1].

## 2) Configuration Loading Model

APOST uses `BaseSettings` from `pydantic-settings`, which reads values from environment variables and `.env` and validates them at startup [1].

```text
+---------------------+
| Runtime environment |
| (ENV vars, secrets) |
+----------+----------+
           |
           v
+---------------------+
| .env file           |
+----------+----------+
           |
           v
+---------------------+
| Settings defaults   |
| in app/config.py    |
+----------+----------+
           |
           v
+---------------------+
| Pydantic validation |
| (range and invariants) |
+----------+----------+
           |
           v
+---------------------+
| Optimizer constants |
| consumed by services|
+---------------------+
```

How to read this flow:
- Environment values are first-class overrides.
- Code defaults are fallback behavior, not production truth.
- Validation is a hard gate: invalid combinations fail fast during startup.

## 3) Why the Main Design Choices Make Sense

### 3.1 Deterministic scoring settings

For rubric-style evaluation, low randomness is usually preferred because score variance can hide real regressions. OpenAI guidance also notes lower temperature for factual/extraction tasks [2][3].

### 3.2 Position-sensitive long-context safeguards

CoRe settings are motivated by long-context behavior: models often use beginning/end context more reliably than middle sections in many setups [4]. That is why repetition bounds are conservative and capped.

### 3.3 OPRO trajectory controls

OPRO is trajectory-based prompt optimization: generate candidates from prior prompt-score history, evaluate, and iterate [5]. Candidate and iteration caps are essential because evaluation cost grows quickly with branching.

### 3.4 TextGrad iteration controls

TextGrad treats textual critique as a gradient-like optimization signal and iterates evaluate -> localize -> rewrite [6]. Iteration count and temperatures directly control exploration depth and rewrite stability.

### 3.5 Prefill and provider formatting

Anthropic documents prefill as a mechanism for stronger output-format control (for example forcing JSON starts) [7]. Provider-specific formatting controls exist because formatting conventions materially affect parsing reliability and compliance.

## 4) Full Variable Coverage: Rationale and Tuning Impact

The table below covers every variable you listed.

## 4.1 TCRTE scorer settings

| Variable | Default | Why this value is reasonable | If you increase it | If you decrease it |
|---|---:|---|---|---|
| `tcrte_score_max_tokens` | `350` | A scorer should return concise structured judgments, not long essays. This cap limits cost and drift. | More detailed scorer output, but more latency/cost and higher chance of verbose, less consistent rationales. | Faster/cheaper, but risk of truncated score payloads or missing explanation fields. |
| `tcrte_score_timeout_seconds` | `20.0` | Balances API tail latency tolerance with service responsiveness. | Fewer timeout failures on slow calls, but slower request failure detection and degraded p95 latency. | Faster failure detection, but more false timeouts under transient provider slowness. |
| `tcrte_score_max_prompt_chars` | `2000` | Keeps scoring prompts bounded and comparable; reduces context noise and cost. | Better coverage for long prompts, but scoring cost and variance increase. | Better throughput and lower cost, but scorer may miss context needed for fair evaluation. |

## 4.2 TCRTE dimension weights

| Variable | Default | Why this value is reasonable | If you increase it | If you decrease it |
|---|---:|---|---|---|
| `tcrte_weight_task` | `0.25` | Task clarity is foundational for downstream success. | More scoring emphasis on explicit objective definition. | Less penalty for ambiguous task phrasing. |
| `tcrte_weight_context` | `0.15` | Context matters but should not overpower execution constraints. | Better reward for richer constraints/background. | Model may overvalue terse prompts with weak context. |
| `tcrte_weight_role` | `0.15` | Role framing helps but is usually secondary to task+execution. | Stronger pressure for persona/professional framing. | Less pressure for role specificity. |
| `tcrte_weight_tone` | `0.15` | Tone influences output quality but is rarely the primary failure mode. | More consistency for voice/audience-sensitive use cases. | Tone defects become less visible in aggregate score. |
| `tcrte_weight_execution` | `0.30` | Execution constraints (format, limits, disallowed behavior) directly affect reliability and parsability. | More weight on schema/format adherence and guardrails. | Higher risk of accepting prompts that are clear but operationally underspecified. |

Note: These weights are product-policy choices inside APOST, not universal standards. The sum-to-1.0 validator enforces scoring consistency.

## 4.3 Prompt optimization runtime controls

### Shared sub-task model and provider

| Variable | Default | Why this value is reasonable | If you increase/change | If you decrease/change |
|---|---:|---|---|---|
| `optimization_llm_sub_task_provider` | `openai` | Single default provider keeps infra and behavior predictable. | Multi-provider migration flexibility, but behavior parity testing is required. | N/A (categorical); less portability if hard-pinned forever. |

### Token budgets by sub-task

| Variable | Default | Why this value is reasonable | If increased | If decreased |
|---|---:|---|---|---|
| `optimization_max_tokens_component_extraction` | `2048` | Complex prompt decomposition can need moderate structured output. | Better extraction completeness on long prompts. | More truncation risk in extracted component JSON. |
| `optimization_max_tokens_synthetic_example_generation` | `1500` | Few-shot synthesis should be detailed but bounded. | Richer examples; higher cost and latency. | Cheaper/faster, but examples may become shallow. |
| `optimization_max_tokens_textgrad_evaluation` | `1200` | Enough room for per-dimension critique while keeping loop cost controlled. | More nuance in critique; slower loop. | Critique may miss edge-case diagnostics. |
| `optimization_max_tokens_textgrad_gradient` | `800` | Localized edit plans should stay concise and targeted. | More verbose edit plans, possible over-specification. | Under-specified edits; weaker rewrite quality. |
| `optimization_max_tokens_textgrad_update` | `2048` | Rewrite step may need to emit full improved prompt. | Better support for long rewritten prompts. | Risk of clipped rewritten prompts. |
| `optimization_max_tokens_tcrte_dimension_fill` | `1500` | Filling weak rubric dimensions needs room, but not full rewrite budget. | Higher completion of missing dimensions. | Underfilled dimensions and weaker coverage gains. |
| `optimization_max_tokens_variant_score_estimation` | `350` | Score-estimation response should be compact and bounded. | Longer analysis, higher cost. | Truncated score explanation risk. |
| `optimization_max_tokens_failure_mode_analysis` | `1500` | Failure analysis can require multi-point reasoning. | Deeper risk analysis. | Superficial failure-mode coverage. |
| `optimization_max_tokens_core_criticality_analysis` | `1200` | CoRe analysis needs concise identification of critical spans. | More detailed span diagnostics. | Missed critical spans in long prompts. |
| `optimization_max_tokens_ral_constraint_extraction` | `1000` | Constraint extraction is narrower than full rewrite. | More complete extraction in complex prompts. | Partial constraint capture. |
| `optimization_max_tokens_opro_proposal` | `2500` | OPRO may propose multiple full prompt candidates in one call. | Richer candidate diversity. | Fewer/shorter candidates, weaker exploration. |
| `optimization_max_tokens_sammo_structural_parse` | `1500` | Structural parse should be descriptive but not expansive. | Better structure detail in complex prompts. | Reduced parse fidelity. |
| `optimization_max_tokens_kernel_rewrite` | `2200` | Full framework rewrites often need large output budget. | Better support for long final prompts. | Higher truncation risk. |
| `optimization_max_tokens_xml_rewrite` | `2200` | XML-structured prompts can be token-heavy. | More robust complete XML output. | Broken/incomplete XML structures risk. |
| `optimization_max_tokens_create_rewrite` | `2200` | CREATE-style deep rewrites need full prompt regeneration room. | More complete transformed prompts. | Incomplete output or clipped sections. |
| `optimization_max_tokens_progressive_rewrite` | `2200` | Progressive prompts include layered instructions and guards. | Better final completeness. | Layer truncation and degraded instruction hierarchy. |

### TextGrad controls

| Variable | Default | Why this value is reasonable | If increased | If decreased |
|---|---:|---|---|---|
| `optimization_textgrad_default_iteration_count` | `3` | Three passes usually captures major defects without runaway cost. | Better quality on weak prompts; linear cost/latency growth. | Faster/cheaper but under-optimized prompts. |
| `optimization_textgrad_evaluation_temperature` | `0.0` | Encourages reproducible critique for rubric workflows [2][3]. | More critique diversity but less consistency. | Already minimum practical bound for determinism. |
| `optimization_textgrad_update_temperature` | `0.3` | Small creativity for rewrites while keeping structure stable. | More exploration and novelty, but higher drift risk. | Safer rewrites, but can become too conservative. |

### OPRO controls

| Variable | Default | Why this value is reasonable | If increased | If decreased |
|---|---:|---|---|---|
| `optimization_opro_default_iteration_count` | `3` | Keeps trajectory optimization effective but bounded [5]. | Better search depth; higher eval cost and latency. | Faster but may stop before good candidates emerge. |
| `optimization_opro_candidates_per_iteration` | `2` | Small branch factor prevents combinatorial cost growth. | More exploration and potentially better best prompt; cost grows quickly. | Cheaper but poorer exploration. |
| `optimization_opro_trajectory_keep_top` | `20` | Enough history for signal without excessively long meta-prompts. | More context for proposal model; larger prompt cost and dilution risk. | Less history; may forget useful prior patterns. |
| `optimization_opro_exemplars_in_meta_prompt` | `3` | Few-shot guidance without overwhelming optimization context. | Better grounding for complex tasks; larger prompt and slower proposals. | Cheaper, but proposals may become generic. |
| `optimization_opro_max_training_cases` | `12` | Caps evaluator spend while keeping dataset signal breadth. | Better robustness estimates; much higher scoring cost. | Lower cost; risk of overfitting to tiny sample. |
| `optimization_opro_proposal_temperature` | `0.8` | Encourages exploratory candidate generation in search loops. | More diversity, more noise/outliers. | More conservative candidates, less innovation. |

### SAMMO controls

| Variable | Default | Why this value is reasonable | If increased | If decreased |
|---|---:|---|---|---|
| `optimization_sammo_min_tcrte_threshold` | `60` | Filters very weak candidates before expensive downstream use. | Stricter quality gate, fewer accepted candidates. | More permissive gate, more low-quality candidates pass through. |
| `optimization_sammo_token_weight` | `0.30` | Keeps brevity pressure present but secondary. | Shorter prompts favored more strongly. | Length matters less; prompts may bloat. |
| `optimization_sammo_tcrte_weight` | `0.70` | Prioritizes quality/compliance over compactness. | Stronger quality preference. | Higher chance to prefer shorter but weaker prompts. |

### CoRe bounds

| Variable | Default | Why this value is reasonable | If increased | If decreased |
|---|---:|---|---|---|
| `optimization_core_minimum_repetition_count` | `2` | Guarantees at least primacy and recency reinforcement for critical context [4]. | More baseline repetition, but higher token overhead by default. | Lower than 2 undermines boundary reinforcement strategy. |
| `optimization_core_maximum_repetition_count` | `5` | Caps repetition to avoid excessive prompt inflation and fixation risk. | Better redundancy for very long prompts, but token/cost inflation rises. | Cheaper prompts but weaker mitigation of middle-context loss. |

## 5) Practical Tuning Strategy

Use this sequence in production tuning:

1. Lock a fixed evaluation set.
2. Tune one family at a time (for example TextGrad only).
3. Measure all four outputs: quality, latency, token usage, error rate.
4. Keep 10-20% step changes, not large jumps.
5. Keep rollback-ready env snapshots.

```text
Quality up?  yes --> Keep change --> Canary --> Promote
   |
   no
   v
Rollback and adjust one adjacent parameter only
```

## 6) Fast Diagnostic Guide

- Symptoms: truncated JSON or malformed structures
  - First check: relevant `max_tokens_*` too low

- Symptoms: scoring instability between similar runs
  - First check: temperature too high for scoring/evaluation paths

- Symptoms: very high latency and cost spike
  - First check: OPRO candidates/iterations/training-cases and rewrite token caps

- Symptoms: long-context prompts still miss critical constraints
  - First check: CoRe max repetition too low for your average prompt length

## 7) Example Safe Profiles

```env
# Balanced (default-like)
OPTIMIZATION_TEXTGRAD_DEFAULT_ITERATION_COUNT=3
OPTIMIZATION_OPRO_CANDIDATES_PER_ITERATION=2
OPTIMIZATION_OPRO_MAX_TRAINING_CASES=12
OPTIMIZATION_CORE_MAXIMUM_REPETITION_COUNT=5

# Cost-sensitive
OPTIMIZATION_TEXTGRAD_DEFAULT_ITERATION_COUNT=2
OPTIMIZATION_OPRO_CANDIDATES_PER_ITERATION=1
OPTIMIZATION_OPRO_MAX_TRAINING_CASES=8
OPTIMIZATION_MAX_TOKENS_OPRO_PROPOSAL=1800

# Quality-first (careful with cost)
OPTIMIZATION_TEXTGRAD_DEFAULT_ITERATION_COUNT=4
OPTIMIZATION_OPRO_CANDIDATES_PER_ITERATION=3
OPTIMIZATION_OPRO_MAX_TRAINING_CASES=16
OPTIMIZATION_MAX_TOKENS_TEXTGRAD_UPDATE=2400
```

## 8) Final Checks Before Shipping Config Changes

- Verify startup validation passes.
- Run a regression suite on representative prompts.
- Compare p50/p95 latency and cost per request.
- Confirm parser success rate (JSON/XML compliance) did not regress.
- Confirm no hidden dependency on provider-specific prompt formatting changed unexpectedly.

## References

[1] Pydantic Settings documentation: https://docs.pydantic.dev/2.0/usage/pydantic_settings/

[2] OpenAI parameter details (temperature, token behavior): https://platform.openai.com/docs/guides/text-generation/parameter-details

[3] OpenAI API reference (chat/completions parameters): https://platform.openai.com/docs/api-reference/chat/create

[4] Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" (TACL, 2024): https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00638/119630/Lost-in-the-Middle-How-Language-Models-Use-Long

[5] Yang et al., "Large Language Models as Optimizers (OPRO)" (arXiv:2309.03409): https://arxiv.org/abs/2309.03409

[6] Yuksekgonul et al., "TextGrad: Automatic Differentiation via Text" (arXiv:2406.07496): https://arxiv.org/abs/2406.07496

[7] Anthropic docs, "Prefill Claude's response for greater output control": https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prefill-claudes-response
