# RAL-Writer: Retrieve-and-Restate Prompt Optimization for Constraint-Heavy Tasks

## Overview

Language models do not read a prompt the way a human reads a document — from top to bottom, with equal attention throughout. Attention is not uniform across the input. Empirical research shows that models give the strongest weight to content near the beginning and near the end of their context window, and are measurably less reliable with content buried in the middle [1]. This is not a bug to be fixed; it is a property of how transformer-based architectures process long sequences, and it has direct consequences for how prompts should be written.

The consequence that matters most in production is **constraint dilution**: when formatting rules, output requirements, and behavioral constraints are scattered throughout a long prompt — mixed into task descriptions, embedded in background context, or mentioned once midway through a document — they fall into the low-attention middle of the context. The model follows the task correctly but ignores the rules. The output is right in content and wrong in form, or violates a requirement that was stated but not reinforced.

RAL-Writer (Retrieve-and-Restate Writer) is a prompt optimization framework designed to eliminate this class of failure. It does so by extracting every constraint from a raw prompt, rewriting the task description as clean narrative with no embedded rules, placing all constraints in a dedicated block positioned to benefit from the model's primacy attention, and then repeating the most critical constraints at the very end of the prompt where recency attention is strongest.

This guide explains the failure mode the framework addresses, the research behind why the solution works, the concepts required to understand it, the end-to-end pipeline, the three optimization tiers it produces, known failure modes, and when to use or avoid it.

---

## 1. The Problem: Constraint Dilution in Long Prompts

Consider a realistic production prompt for a document summarization task:

> *"You are a historian analyzing this document. Make sure to use British spelling. The document is about the fall of Rome. Summarize the key economic factors, but do not use bullet points. Make sure the output is under 300 words. Describe the trade routes in detail."*

The actual task — summarize economic factors and describe trade routes — is straightforward. But three formatting constraints are woven directly into the task description: use British spelling, no bullet points, output under 300 words. If the document being analyzed is several pages long, those constraints will be surrounded on both sides by historical content. The model processes the document, generates a response, and by that point the formatting rules have been effectively washed out by the surrounding context.

Liu et al. documented this pattern rigorously in their "Lost in the Middle" study, showing that language models perform significantly worse when relevant information appears in the middle of the context rather than near the beginning or end [1]. This was demonstrated across multiple retrieval and reasoning tasks, and the effect grows stronger as context length increases. A constraint stated once in the middle of a 4,000-token prompt is at genuine risk of being ignored regardless of how clearly it was written.

The failure modes this produces are specific and reproducible:

A model asked to produce output without bullet points produces a bulleted list. A model asked for British spelling produces American spelling. A model given a 300-word limit returns 500 words. A model told to use only the provided document introduces facts from its training data. In each case, the instruction was in the prompt. The prompt was the problem.

RAL-Writer addresses this by treating constraints not as part of the task narrative but as a separate layer of the prompt architecture — one that is explicitly positioned to survive the model's non-uniform attention pattern.

---

## 2. The Research Foundation

The framework's design follows directly from two empirical findings about how language models process long contexts.

Liu et al. found that model performance on multi-document question answering degrades systematically when the relevant passage is placed in the middle of the context window, and improves when it is placed near the beginning or end [1]. They described this as a U-shaped performance curve across position: primacy (the beginning of the prompt) and recency (the end of the prompt, just before the model generates output) are the two reliable high-attention zones. The middle is a lower-reliability zone for instruction adherence.

This finding has a direct design implication: instructions that must be followed reliably should not be placed in the middle of a long context. They should appear early, appear late, or ideally both.

RAL-Writer is built around this implication. The constraint block is placed early, immediately after the task directive and before any long background context, so it benefits from primacy attention. The most critical constraints are then repeated at the very end of the prompt, immediately before the model begins generating its response, so they benefit from recency attention. This dual placement — early and late — is the core structural innovation.

---

## 3. Core Concepts

### Constraint Dilution

Constraint dilution is the failure mode where formatting rules, style requirements, and behavioral constraints are present in the prompt but are effectively ignored because they are embedded within longer task or context text. The constraints are not ambiguous; they are simply positioned where they receive insufficient attention relative to the surrounding content.

The defining characteristic of constraint dilution is that the model's output is wrong in form but not in content. The task is executed correctly; the rules were not. This is distinct from misunderstanding the task, and it requires a different fix: not better task description, but better constraint placement.

### Disentanglement

Disentanglement is the process of separating a raw prompt into two clean components: the task narrative — what the model should do — and the constraint set — how the model should do it.

In a well-disentangled prompt, the task narrative contains no formatting instructions, no style rules, and no output requirements. It describes the job to be done. All "how to do it" content lives in a dedicated constraint section that is separate, clearly labeled, and positioned deliberately.

Disentanglement matters because task narrative and constraints require different types of attention from the model. The task sets the direction; the constraints govern execution. Mixing them forces the model to extract rules from prose while simultaneously building its understanding of the task, which increases the chance that rules are processed as context rather than as instructions.

### Forensic Extraction

Forensic extraction is the analysis pass that scans a raw prompt and identifies every constraint it contains: explicit rules that are clearly stated, implicit rules that are logically required by the task but not written down, and contradictions where two stated rules conflict with each other.

The term "forensic" reflects that this pass is looking for things that may not be obvious. A prompt that says "return a CSV" implies "escape commas inside field values" — that second rule is an implicit constraint. A prompt that says "summarize deeply" and "keep it under 10 words" contains a contradiction. A forensic extraction pass surfaces both, producing a complete inventory before any rewriting begins.

Implicit constraints are the more valuable output of this stage. Explicit rules the user already knows about; the extraction just relocates them. Implicit rules are requirements the user may not have thought to state, and failing to follow them would produce outputs that violate the task even though no rule was technically broken.

### Primacy and Recency

Primacy refers to the elevated attention a language model gives to content near the beginning of its input. Recency refers to the elevated attention it gives to content near the end, immediately before it generates output. Both are consequences of how transformer attention and position-encoding interact across long sequences [1].

RAL-Writer exploits both effects deliberately. The constraint block benefits from primacy because it is placed early. The recency echo benefits from recency because it is placed last. The long background context — the part most likely to dilute rules if they were embedded in it — sits between these two high-attention placements without containing any constraints.

### The Recency Echo

The recency echo is a short block appended at the very end of the prompt that restates the most critical constraints one more time, just before the model begins generating its response. It is not a summary of the full prompt. It contains only the highest-priority rules — the ones where a violation would make the output unusable regardless of how well the task was executed.

The echo is not about redundancy for its own sake. It exists because the model's attention at generation time is highest for the content it saw most recently. Placing the most consequential rules at that position is a deliberate use of the model's attention architecture rather than a fight against it.

---

## 4. System Architecture

A RAL-Writer prompt is a layered structure where each layer serves a distinct purpose and is positioned deliberately relative to the model's attention curve.

```
┌─────────────────────────────────────────────────────────┐
│  TASK DIRECTIVE                                         │
│  (Pure instruction — what the model should do)          │
│  Contains: task definition, role, output goal           │
│  Contains no formatting rules or style constraints      │
│                    ↕ PRIMACY ZONE                       │
├─────────────────────────────────────────────────────────┤
│  CONSTRAINT BLOCK                                       │
│  (All rules — how the model should do it)               │
│  Contains: explicit rules, implicit rules               │
│  Grouped by: hard constraints / soft preferences        │
│  Labeled: criticality (high / medium / low)             │
│                    ↕ PRIMACY ZONE                       │
├─────────────────────────────────────────────────────────┤
│  BACKGROUND CONTEXT                                     │
│  (Long reference material — documents, data, history)   │
│  Contains: content to be analyzed or processed          │
│  Contains no rule language                              │
│                    ↕ LOW-ATTENTION MIDDLE               │
├─────────────────────────────────────────────────────────┤
│  RECENCY ECHO                                           │
│  (Critical rules restated — the model sees these last)  │
│  Contains: high-criticality constraints only            │
│  Typically top 3 most important rules                   │
│                    ↕ RECENCY ZONE                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
                  Model generates response
```

This layout is the direct application of the U-shaped attention curve. Rules appear in both high-attention zones. The long, attention-diluting background context is sandwiched between them, where it belongs — as material to be processed, not as the frame that defines what the model must do.

Each layer has a single responsibility. The task directive sets direction. The constraint block defines execution requirements. The background context provides the material. The recency echo reinforces what cannot be forgotten.

---

## 5. End-to-End Pipeline

RAL-Writer processes a raw prompt through four sequential stages to produce three optimized output variants.

```
Raw prompt (mixed task + rules + context)
                  │
                  ▼
┌──────────────────────────────────────────┐
│  Stage 1: Forensic Extraction            │
│                                          │
│  LLM analyser reads the raw prompt       │
│  and returns structured JSON:            │
│                                          │
│  • explicit_constraints[]                │
│  • implicit_constraints[]                │
│  • soft_preferences[]                    │
│  • detected_contradictions[]             │
│  • criticality labels (high/med/low)     │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│  Stage 2: Disentanglement                │
│                                          │
│  Second LLM call rewrites the prompt:    │
│                                          │
│  Input:  raw prompt + extracted rules    │
│  Output: task_directive (rule-free)      │
│          background_context (rule-free)  │
│                                          │
│  All rule language is removed from       │
│  narrative — moved to constraint block   │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│  Stage 3: Assembly (deterministic)       │
│                                          │
│  Python logic assembles three variants   │
│  from the same extracted parts:          │
│                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Conserv.  │ │Structured│ │Advanced  │  │
│  │Task      │ │Task      │ │Task      │  │
│  │Context   │ │Context   │ │Context   │  │
│  │Constraint│ │Constraint│ │Constraint│  │
│  │No echo   │ │Top 3 echo│ │Full echo │  │
│  │          │ │+Markdown │ │+Borders  │  │
│  │          │ │ headers  │ │+Grouping │  │
│  └──────────┘ └──────────┘ └──────────┘  │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│  Stage 4: Quality Gate                   │
│                                          │
│  Checks for data loss in disentanglement │
│  Flags any remaining contradictions      │
│  Adds constraint metadata to response    │
│  Scores variants for quality             │
└────────────────────┬─────────────────────┘
                     │
                     ▼
         Three optimized prompt variants
         + contradiction alerts
         + implicit constraint log
         + quality scores
```

**Stage 1 — Forensic Extraction** uses a dedicated LLM call to analyze the raw prompt and produce a complete structured inventory of its constraints. The analyser is instructed to find not just what is written but what is logically implied. If the prompt says "return a Markdown table," the analyser should also infer "align column headers" and "escape pipe characters inside cells." The output is a JSON object with categorized constraints and criticality labels. Contradictions found at this stage are flagged in the response metadata for the user to resolve — the framework surfaces them but does not attempt to resolve them automatically, since any resolution requires a judgment call about the user's actual intent.

**Stage 2 — Disentanglement** uses a second LLM call to produce a rule-free version of the task narrative. The rewriter receives both the original prompt and the extracted constraint list, and is instructed to rewrite the task directive and background context so that they contain no formatting rules, style requirements, or output specifications. Those have already been extracted; the rewriter's job is to produce clean narrative. The quality gate in Stage 4 checks that this rewriting did not accidentally remove task-relevant content — only rule language should have been removed.

**Stage 3 — Assembly** is fully deterministic. No LLM is called. Python logic takes the extracted constraints and the disentangled narrative and constructs three prompt variants according to tier-specific formatting rules. This determinism is intentional: variant structure should be predictable and reproducible, independent of LLM behavior in any given call.

**Stage 4 — Quality Gate** verifies that the assembled prompts are complete and that the response metadata accurately reports any contradictions found. The gate also applies shared quality scoring to the variants, producing the quality metadata that is returned alongside the prompts.

---

## 6. The Three Optimization Tiers

All three variants are assembled from the same extracted constraints and disentangled narrative. They differ in how aggressively they format, group, and echo the constraints.

### Conservative

The Conservative variant places the task directive, background context, and constraint block in order, with no recency echo at the end. This is appropriate for shorter prompts where the constraint block benefits sufficiently from primacy alone — where the distance between the constraint block and the generation point is small enough that the model is unlikely to have lost attention on the rules by the time it begins writing.

This tier has the lowest token overhead. It adds structure without adding repetition.

### Structured

The Structured variant uses Markdown headers to label each section clearly — task, context, constraints — and appends a recency echo containing the top three highest-criticality constraints. The echo is formatted with a clear header such as "CRITICAL REMINDERS" to signal to the model that this content is a deliberate reinforcement, not a new instruction.

This is the recommended production default for most constraint-heavy prompts. The Markdown headers improve section legibility for both the model and the human reviewing the prompt. The top-three echo covers the most important rules without creating noise.

### Advanced

The Advanced variant applies high-contrast visual boundaries — using repeated characters such as `====` or `####` — to make the constraint block and recency echo unmissable even in very long prompts. Constraints are grouped by type: hard constraints (rules that must be followed), implicit constraints (inferred requirements), and soft preferences (desirable but lower-authority guidance). The recency echo repeats all high-criticality constraints, not just the top three.

This tier is appropriate for prompts with very long background context — multi-document retrieval-augmented generation with thousands of tokens of reference material — or for prompts with high rule density where even a single violated constraint would make the output unusable.

The trade-off is token cost and potential rigidity. Very heavy formatting can make simple tasks feel over-specified and can inflate prompt length significantly.

| Property | Conservative | Structured | Advanced |
|---|---|---|---|
| Section labels | Minimal | Markdown headers | High-contrast borders |
| Constraint grouping | None | None | Hard / Implicit / Soft |
| Recency echo | None | Top 3 critical | All high-criticality |
| Token overhead | Lowest | Moderate | Highest |
| Best for | Short prompts, few rules | Standard production use | Long context, high rule density |

---

## 7. The Standalone Framework vs. the Shared Utility

RAL-Writer exists in two distinct forms that serve different purposes, and confusing them leads to misuse.

The **standalone framework** is the full intelligent pipeline described in this guide: forensic extraction, disentanglement, tiered assembly, and quality gate. It takes a raw prompt and returns three optimized variants. It requires two LLM calls and typically adds a few seconds of latency. It is the appropriate choice when optimizing a new or problematic prompt that mixes rules and narrative.

The **shared utility** is a simple function that appends a given block of text to the end of an existing prompt. It applies no analysis, performs no rewriting, and makes no LLM calls. It is used by other prompt optimization frameworks to add a recency echo to their own output without running the full RAL-Writer pipeline. This utility is what other frameworks use when they want to borrow the recency echo mechanism for their own assembled prompts.

When choosing between these, the decision is straightforward: if the input is a raw user prompt that needs analysis and restructuring, use the standalone framework. If the input is an already-assembled optimized prompt that just needs a constraint reminder appended to its end, use the shared utility.

---

## 8. Implicit Constraint Inference

One of the more practically valuable outputs of the forensic extraction stage is the implicit constraint list. These are requirements that are logically necessary for correct execution of the task but were not stated in the original prompt.

For example: a prompt that asks the model to return JSON does not need to say "ensure the output is valid JSON" — that is implied. But it may not say "do not include trailing commas" or "wrap string values in double quotes, not single quotes," both of which are implied by JSON specification. A model that produces technically malformed JSON has violated requirements that were never written down.

Similarly, a prompt that says "translate this document to French" implies "preserve paragraph structure" and "do not translate proper nouns." A prompt that says "sort this list alphabetically" implies "treat uppercase and lowercase as equivalent unless otherwise specified."

The extraction analyser is instructed to surface these implied requirements as explicit rules in the constraint block. This has two effects: it makes the constraints more complete, and it often reveals requirements the user had not consciously thought about but would certainly have wanted enforced.

Detected contradictions — where two stated rules are logically incompatible — are reported in the response metadata but not resolved automatically. The framework's position is that any resolution requires the user's intent, and guessing wrong would be worse than flagging. The user is expected to edit the source prompt before rerunning.

---

## 9. Trade-offs and Production Considerations

**Two LLM calls per optimization.** Unlike frameworks that assemble prompts deterministically or use a single generation pass, RAL-Writer requires two LLM calls: one for forensic extraction and one for disentanglement. This adds latency — typically a few seconds total — and incurs API cost for both calls. For prompts that are optimized once and reused many times, this cost is a one-time investment. For systems that re-optimize prompts dynamically per request, the cost needs to be weighed against the reliability benefit.

**Disentanglement data loss risk.** The rewriting step that produces a rule-free task narrative can, in edge cases, accidentally remove task-relevant content along with the rule language. The quality gate checks for this, but the check is imperfect. In production, the disentangled narrative should be reviewed before deployment, particularly for prompts where the task description and the constraint language are heavily interleaved and difficult to separate cleanly.

**Recency echo scope.** The echo is effective when it contains only the most critical constraints. An echo that tries to repeat everything becomes noise — a long block of text at the end of the prompt that the model processes as context rather than as a targeted reminder. The Advanced tier mitigates this by grouping constraints, but the fundamental principle is selectivity: only rules whose violation would make the output unacceptable belong in the echo.

**Not a reasoning framework.** RAL-Writer does not add reasoning demonstrations, multi-step thinking instructions, or verification steps. It is a constraint placement and reinforcement framework. For tasks where the primary failure mode is reasoning errors — wrong intermediate steps, logical mistakes, misunderstood relationships — a different approach is more appropriate.

**Not a security boundary.** Like any prompt-level technique, the constraint block and recency echo are instructions to the model, not enforced boundaries. A model that is manipulated through adversarial input or that encounters a constraint-violating pattern it was not trained to resist can still violate the rules. For high-stakes systems, application-layer output validation is required in addition to prompt-level constraint reinforcement.

---

## 10. Common Failure Modes and Diagnostics

| Symptom | Likely cause | Diagnostic approach | Correction |
|---|---|---|---|
| Rule still ignored after optimization | Rule was extracted but not marked high criticality; not included in echo | Inspect extracted constraint list and criticality labels in response metadata | Rephrase rule as an explicit, unambiguous requirement; rerun extraction |
| Contradiction alerts in response metadata | Two constraints in the source prompt are logically incompatible | Read the detected contradictions list; identify which instruction wins | Edit the source prompt to resolve the conflict; do not rely on the model to resolve it |
| Disentangled narrative is missing task content | Rewriter over-stripped during Stage 2 | Compare original prompt to disentangled narrative field in response | Strengthen the rewriter instruction to preserve all non-rule content; report as a quality issue |
| Recency echo is too long and noisy | All constraints were marked high criticality | Inspect criticality assignments | Reduce high-criticality designations to only the rules where violation makes the output unusable |
| Variants across tiers look nearly identical | Tier-specific formatting differences are not applied | Compare Conservative, Structured, and Advanced assembled prompts | Review assembly logic for the Advanced tier's grouping and border formatting |
| Implicit constraints are empty | Extraction analyser did not infer implied rules | Inspect raw extraction output | Strengthen the extraction prompt to explicitly instruct inference of domain-specific implied requirements |

The fastest diagnostic in most cases is to inspect the extraction metadata. If a rule was ignored in the model's output, the first question is whether it appeared in the extracted constraint list, and the second is what criticality level it was assigned. Rules not in the extracted list were not included in the constraint block. Rules assigned low criticality were not included in the recency echo.

---

## 11. When to Use RAL-Writer — and When Not To

### Strong Fits

RAL-Writer is most valuable when the prompt contains multiple specific rules that must all be followed reliably, when the background context is long enough that constraints placed within it are at risk of being lost, and when violations of the rules would make the output unusable regardless of how well the task was executed.

Concrete use cases include long-document question answering with strict output format requirements, multi-document retrieval-augmented generation where the model must follow source-only citation rules, structured data extraction where output schema compliance is mandatory, and any production pipeline where consistent, auditable constraint adherence is required.

RAL-Writer is also the right choice when negative constraints — rules of the form "never do X" or "do not include Y" — need to be reliably enforced. Negative constraints are particularly vulnerable to dilution because they state what not to do rather than what to do, which makes them easier for the model to overlook when they appear once in a long context.

### Poor Fits

Avoid RAL-Writer for prompts with no explicit constraints, where there is nothing to extract or reinforce. A prompt that simply asks for a creative piece of writing has no constraint block to build and would not benefit from the framework.

Avoid it for tasks where the primary failure mode is reasoning error rather than constraint violation. If the model produces wrong answers because its reasoning steps are incorrect, adding constraint reinforcement does not address the root cause. A framework that adds worked reasoning examples or multi-path verification is more appropriate.

Avoid it for very short prompts where the distance between the constraint and the generation point is small. When a prompt is 200 tokens, primacy and recency are approximately the same location — the constraint block alone is sufficient, and the two-LLM-call overhead of the full framework is not justified.

### Comparison with Related Approaches

Compared with frameworks that use XML-tagged structure to separate directives and data, RAL-Writer focuses specifically on constraint placement and reinforcement rather than on the authority hierarchy of different prompt sections. The two approaches are complementary: a structured XML prompt can also incorporate a recency echo, and a RAL-Writer optimized prompt can use XML tags for its sections. They target different failure modes.

Compared with chain-of-thought frameworks that add reasoning demonstrations, RAL-Writer adds no examples and no reasoning instructions. It is a constraint placement technique, not a reasoning technique. For tasks that need both — reliable constraint adherence and reliable multi-step reasoning — the approaches can be combined by running chain-of-thought assembly within the task directive and then applying the RAL-Writer constraint structure around it.

---

## 12. Conclusion

RAL-Writer addresses a failure mode that is structural rather than semantic: a prompt can be well-written, clearly reasoned, and completely specified, and still produce non-compliant output if its constraints are positioned where the model's attention is weakest.

The framework's solution is direct: extract every constraint forensically, rewrite the task narrative to be entirely rule-free, place all constraints in a dedicated block in the high-attention opening zone, and repeat the most critical constraints in the high-attention closing zone. The structure leverages the empirically documented U-shaped attention curve [1] rather than fighting against it.

The practical guidance is straightforward. Use the Structured tier as the default for most constraint-heavy production prompts. Upgrade to Advanced for very long contexts with high rule density. Always review the extracted constraint list and the detected contradictions in the response metadata — these are the most useful diagnostic information the framework produces. And pair it with application-layer output validation for any system where constraint violations have downstream consequences.

The central principle is simple: rules the model must follow should not be placed where the model is least likely to pay attention to them.

---

## References

[1] Liu, Nelson F., Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, and Percy Liang. *Lost in the Middle: How Language Models Use Long Contexts.* Transactions of the Association for Computational Linguistics, 2024. https://arxiv.org/abs/2307.03172

[2] Wei, Jason, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Brian Ichter, Fei Xia, Ed H. Chi, Quoc V. Le, and Denny Zhou. *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.* NeurIPS 2022. https://arxiv.org/abs/2201.11903

[3] Vaswani, Ashish, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, and Illia Polosukhin. *Attention Is All You Need.* NeurIPS 2017. https://arxiv.org/abs/1706.03762

[4] Anthropic. *Claude Prompting Best Practices — Long Context Tips.* Anthropic Platform Documentation. https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/long-context-tips

[5] Perez, Fábio, and Ian Ribeiro. *Ignore Previous Prompt: Attack Techniques For Language Models.* Workshop on Trustworthy and Reliable Large-Scale Machine Learning Models, NeurIPS 2022. https://arxiv.org/abs/2211.09527