# SAMMO for Structure-Aware Prompt Optimization

## Abstract

SAMMO is a prompt-optimization approach that treats a prompt as a structured program instead of a single block of text. That shift matters when prompts become long, repetitive, and expensive to run. Rather than only paraphrasing wording, SAMMO-style optimization changes the arrangement of prompt sections, compresses lower-value context, preserves high-value constraints, and evaluates trade-offs between prompt quality and token cost. The original SAMMO research frames this as **symbolic prompt program search** for **compile-time optimization** of prompt programs, meaning the prompt is improved before repeated production use rather than rewritten separately for every request [1][2].

The implementation described here applies that idea to an internal optimization pipeline that parses a prompt into a graph, mutates the graph, assembles multiple candidate prompts, scores them on quality and token efficiency, keeps non-dominated candidates, and returns variants tuned for different deployment priorities [5]. This document explains that pipeline from first principles, then shows how the pieces fit together in practice.

## 1. Introduction

As large language model systems mature, prompts stop being short instructions and start behaving like programs. They include task definitions, background context, rules, examples, output schemas, and runtime variables. That makes them more reliable, but it also creates a new engineering problem: the prompt may work well only because it has become long, redundant, and costly.

Traditional prompt editing is usually too coarse for this setting. A human editor or a generic rewriting model may shorten the prompt, but without knowing which parts are safe to compress and which parts carry the task logic. SAMMO addresses that problem by making structure explicit. In the research literature, the method is described as structure-aware search over prompt programs [1]. In the open-source SAMMO project, prompts are represented as symbolic or program-like objects that can be modified and optimized systematically [2][3].

The result is a better mental model for serious prompt engineering: do not ask only whether a prompt is “good.” Ask whether it is **good enough for the task, cheap enough to run repeatedly, and transparent enough to debug**.

## 2. The Problem This Framework Solves

A structure-aware optimizer exists because long prompts fail in predictable ways.

The first failure is **token bloat**. Teams keep adding rules, examples, reminders, and formatting instructions until the prompt becomes slow and expensive. Prompt compression work such as LLMLingua exists for exactly this reason: long prompts increase inference cost, and not every token contributes equal value [4].

The second failure is **unsafe compression**. Shortening a prompt blindly can remove the very text that stabilizes model behavior. A background paragraph can often be compressed more aggressively than a safety rule or a required output schema. If the optimizer does not know the difference, it is likely to save tokens in the wrong place.

The third failure is **single-axis selection**. Optimizing only for quality tends to produce oversized prompts. Optimizing only for brevity tends to produce brittle prompts. Multi-objective optimization addresses this by keeping solutions that represent meaningful trade-offs rather than forcing one objective to dominate the other [6].

The fourth failure is **opaque editing**. When prompts are edited as plain text, it becomes hard to tell what changed. Did the instruction change? Did a rule disappear? Did an example move? A structured representation makes these changes visible and testable.

## 3. Preconditions, Inputs, and System Boundary

This optimizer is useful only when the prompt already has meaningful internal structure. A one-line prompt rarely benefits from a graph parser and a candidate-selection stage. A long production prompt often does.

At minimum, the system expects a base prompt containing most of the following elements:

- a core instruction
- one or more context blocks
- rules or constraints
- optional examples or few-shot demonstrations
- an expected output format

The implementation described in the provided source material also assumes that the system may have extra clarification gathered earlier in the workflow, called gap-interview answers, which are merged into the base prompt before structural analysis [5]. That means SAMMO is not the first stage in the pipeline. It assumes the prompt has already been clarified enough to be worth optimizing.

A useful way to define the system boundary is this:

```text
input:   a clarified prompt program
process: parse -> mutate -> assemble -> score -> select -> quality-check
output:  a small set of prompt variants with different quality/cost trade-offs
```

This is a compile-time optimization loop, not a conversational agent loop. The goal is to improve the prompt template before it is reused at runtime [1].

## 4. Core Concepts in Plain Language

### 4.1 Prompt as program

The key idea behind SAMMO is that a prompt is not just text. It is a composition of components that play different roles. The research paper explicitly frames prompts as structured programs that can be transformed symbolically rather than only paraphrased sentence by sentence [1].

### 4.2 Prompt graph

In this implementation, the prompt is normalized into a graph-like object with named fields such as `instruction`, `context_blocks`, `rules`, `few_shot`, and `output_format` [5]. Calling it a “graph” matters because the optimizer is allowed to operate on sections rather than raw characters.

```text
+------------------- Prompt Graph -------------------+
| instruction   -> what the model must do            |
| context       -> background needed for the task    |
| rules         -> constraints that must hold        |
| few_shot      -> demonstrations or examples        |
| output_format -> required response shape           |
+----------------------------------------------------+
```

This diagram is intentionally simple. It shows the minimum structure the optimizer needs in order to treat each section differently. The instruction and rules are usually high-value control components. Context is often the main compression target. Few-shot examples are powerful but expensive. Output format is small, but breaking it can break downstream parsing.

### 4.3 Mutation operator

A mutation operator is a controlled transformation over the prompt graph. In the described implementation there are three main operators: `compression`, `restructure`, and `syntactical` [5].

- **Compression** shortens context while trying to preserve the facts the task depends on.
- **Restructure** changes ordering and may simplify the prompt layout.
- **Syntactical mutation** rewrites the task wording for clarity without changing intent.

The important detail is that these are not random edits. They are targeted edits with known intent.

### 4.4 Multi-objective scoring

SAMMO does not assume that the shortest prompt is best or that the most detailed prompt is best. It scores candidates on more than one axis. In the implementation described here, those axes are prompt quality and token efficiency [5]. In multi-objective optimization terms, the system is looking for candidates that are not clearly worse than another candidate on both objectives at the same time [6].

### 4.5 Pareto front

A candidate is on the Pareto front if no other candidate beats it on both quality and efficiency. This is a standard way to keep trade-offs visible in multi-objective optimization [6].

```text
quality ↑
        |
   high |           B  (better quality, more tokens)
        |        *
        |
        |   A  *        C *
        |
        +----------------------------------------→ efficiency
             lower                           higher
```

In this sketch, no single point is automatically “the winner.” Candidate B may be better for a sensitive workflow. Candidate C may be better for a high-throughput service. Candidate A may still be useful if it offers a balanced middle ground. The point of the Pareto front is to preserve these options instead of collapsing them too early.

## 5. End-to-End Workflow

The implementation described in the supplied documentation follows a clean eight-stage flow [5].

```text
raw/clarified prompt
        |
        v
[1] enrich with prior clarifications
        |
        v
[2] parse into structured prompt graph
        |
        v
[3] run graph mutations in parallel
        |
        v
[4] fall back to deterministic edits if a mutation fails
        |
        v
[5] assemble mutated graphs into runnable prompts
        |
        v
[6] score each prompt on quality and token efficiency
        |
        v
[7] keep non-dominated candidates and assign final variants
        |
        v
[8] inject runtime variables and run a final quality gate
```

Each box has a separate responsibility. That separation is what makes the pipeline debuggable.

### Stage 1: Enrich the prompt

Before optimization, the system merges any clarification already gathered upstream. This step matters because structural parsing is only as good as the prompt it receives. If important constraints are still outside the prompt, the optimizer cannot preserve them [5].

### Stage 2: Parse into a prompt graph

The parser asks a model to map the prompt into a structured representation with fixed fields such as instruction, context, rules, examples, and output format [5]. This is the moment where raw text becomes an editable program-like object.

### Stage 3: Run mutations in parallel

The implementation launches three mutations asynchronously: compression, restructuring, and syntactic sharpening [5]. Parallel execution does not change the logic, but it reduces wall-clock time versus running each mutation serially.

### Stage 4: Deterministic fallback

If a model-based mutation fails, the system does not stop. It uses rule-based fallback behavior, such as truncating context, reordering sections, or appending a clearer execution hint [5]. This matters operationally. A production optimizer must degrade gracefully when a sub-call returns malformed output.

### Stage 5: Reassemble candidate prompts

Every mutated graph is serialized back into a runnable system prompt. The implementation uses explicit sections such as instruction, context, rules, few-shot hints, and output format [5]. Duplicate candidates are removed so the selector is comparing genuinely different options.

### Stage 6: Score candidates

Each candidate receives a quality estimate and an efficiency estimate. The provided implementation uses a local rubric called TCRTE for quality, then computes token efficiency relative to the baseline prompt [5]. This is an implementation detail rather than a universal SAMMO requirement, but the broader pattern is fully aligned with the multi-objective philosophy in the SAMMO paper [1].

### Stage 7: Select final variants

The source material describes three final slots [5]:

- **Conservative**: the most efficient candidate that still clears a minimum quality bar
- **Structured**: the strongest candidate on the quality axis
- **Advanced**: the strongest weighted compromise among Pareto-front candidates

This is a practical selection policy. It gives downstream users a cheap option, a quality-first option, and a balanced option.

### Stage 8: Inject variables and run a final quality gate

Only after candidate selection does the system append runtime variables and run a final critique-and-enhancement pass [5]. This sequencing is sensible: first optimize the prompt structure, then perform final review on the shortlisted candidates.

## 6. Architecture and Control Flow

The whole system becomes easier to understand when shown as components.

```text
+--------------------+
| Prompt source      |
| + prior clarifiers |
+---------+----------+
          |
          v
+--------------------+
| Graph parser       |
| prompt -> sections |
+---------+----------+
          |
          v
+-----------------------------+
| Mutation layer              |
| - compression               |
| - restructure               |
| - syntactical rewrite       |
+---------+---------+---------+
          |         |
          |   fallback path
          v         v
+-----------------------------+
| Candidate assembler         |
| graph -> runnable prompt    |
+-------------+---------------+
              |
              v
+-----------------------------+
| Scoring layer               |
| quality + token efficiency  |
+-------------+---------------+
              |
              v
+-----------------------------+
| Pareto + tier selector      |
| Conservative / Structured / |
| Advanced                    |
+-------------+---------------+
              |
              v
+-----------------------------+
| Variable injection + gate   |
+-------------+---------------+
              |
              v
+-----------------------------+
| Final prompt variants       |
+-----------------------------+
```

The most important architectural choice here is the separation between **representation**, **transformation**, and **selection**. The parser gives the system structure. The mutators explore alternatives. The selector decides which alternatives deserve to survive. If these responsibilities are mixed together, debugging becomes much harder.

## 7. Data Flow, State, and Interfaces

Three internal data states matter most in this design.

The first is the **base prompt state**. This is still ordinary text, although it may already contain merged clarifications.

The second is the **structured graph state**. At this point the prompt is decomposed into editable fields. This is the key state for interpretability because engineers can compare “before” and “after” by section rather than by raw diff.

The third is the **candidate state**. Each candidate contains the reassembled prompt plus metadata such as mutation label and scores [5]. That metadata turns prompt optimization from guesswork into an inspectable search process.

The open-source SAMMO project makes a similar point in a more general way: prompts can be represented as symbolic prompt programs and manipulated with reusable components, mutators, parsers, and search procedures [2][3]. The implementation described here applies the same philosophy to a narrower topological optimizer.

## 8. Evaluation and Selection Logic

The quality of the optimizer depends on the quality of its selection policy. This is where many prompt systems fail.

In the provided implementation, quality is estimated using a rubric-based score and efficiency is computed relative to the baseline prompt [5]. A weighted blend is used for one of the final variants, with source documentation noting a default split of 70 percent quality and 30 percent token efficiency [5]. That weighting is a business decision, not a law of nature.

A reliable way to think about selection is:

```text
candidate merit = not one score, but a profile
profile = {quality, efficiency, mutation provenance}
selection = thresholding + non-dominated filtering + tier policy
```

This is superior to a naive “top one wins” approach because it preserves interpretability. You know whether a candidate survived because it was cheaper, more faithful, or a better overall compromise.

There is one important caveat. The source document itself notes that heuristic or rubric-based scoring is not a substitute for task-level evaluation on representative examples [5]. That warning is correct. Compile-time prompt optimization is best treated as a search-and-triage mechanism, not as proof that the chosen prompt is production-safe.

## 9. Cost, Latency, and Scaling Trade-offs

A SAMMO-style optimizer spends extra compute up front to save cost later.

That is the central economic trade-off. The pipeline performs at least one structural parse plus multiple mutation calls, then scoring and selection. The provided implementation uses one parse and three mutation calls, with mutations running concurrently [5]. That makes the optimizer heavier than a one-pass rewrite, but it can be worthwhile when the resulting prompt is reused many times.

This matches the broader SAMMO framing in the literature. The research emphasizes **compile-time optimization** of prompts that will be run repeatedly, including instruction tuning, retrieval-augmented generation pipeline tuning, and prompt compression [1]. The open-source repository also positions SAMMO as a library for prompt prototyping, instruction optimization, prompt compression, and large-scale prompt execution rather than as a framework for interactive agent applications [2][3].

A reasonable deployment rule is simple: the more often a prompt template is reused, the easier it is to justify a more expensive optimization pass.

## 10. Failure Modes and Diagnostics

This kind of optimizer usually fails in a small number of ways.

**Parse failure** happens when the original prompt is too ambiguous or the parser returns malformed structure. Inspect the graph first. If the graph is wrong, everything downstream will be wrong.

**Over-compression** happens when important facts were stored in context instead of rules or instruction. This is a design smell in the prompt itself, not only in the optimizer.

**Weak diversity** happens when multiple mutations produce nearly identical prompts. That usually means the source prompt is too under-structured to give the operators room to explore meaningful alternatives.

**Misleading selection** happens when heuristic quality estimates drift away from real task performance. The fix is not to trust the selector more. The fix is to run task-level evaluation.

**Latency disappointment** happens when the optimization pass costs more than the savings justify. This is common when prompts are already short or rarely reused.

A practical debugging sequence looks like this:

```text
1. inspect parsed graph
2. compare mutated graphs section by section
3. inspect assembled prompts
4. inspect score profile per candidate
5. run task-level evaluation on shortlisted variants
```

That order matters. If the graph is broken, do not start by tweaking weights. If the scores are odd, do not assume the prompt is wrong before checking the scorer.

## 11. When to Use This Approach, and When Not To

Use this approach when the prompt is already complex enough to deserve structural treatment. Good fits include long prompts, retrieval-heavy prompts, prompts with multiple policy constraints, and high-volume systems where prompt cost matters over many repeated calls [1][2][5].

Avoid it when the prompt is tiny, the task is still poorly specified, or the application is dominated by interactive agent behavior rather than reusable prompt programs [2][3]. In those cases, a lighter optimization strategy is usually better.

Also avoid over-reading the method. Structure-aware mutation can improve the odds of finding a better prompt, but it does not eliminate the need for real evaluation, careful monitoring, or domain-specific review.

## 12. Conclusion

SAMMO is best understood as a disciplined answer to a real production problem: prompts become programs, and programs need optimization that respects structure. The research literature contributes the underlying idea of symbolic prompt program search [1]. The open-source project shows how that idea can be turned into practical tooling for prompt engineering, optimization, and compression [2][3]. The implementation described in the provided source material applies the same principle to an internal topological optimizer that parses prompts into structured graphs, mutates them, scores the results, and returns variants tuned for different quality/cost priorities [5].

The strongest practical lesson is not that every prompt needs SAMMO. It is that once prompts become operational assets, plain-text editing is no longer enough. At that point, structure, search, and explicit trade-off management become engineering requirements rather than prompt-writing preferences.

## References

[1] Tobias Schnabel and Jennifer Neville, *Symbolic Prompt Program Search: A Structure-Aware Approach to Efficient Compile-Time Prompt Optimization*, Findings of EMNLP 2024 / arXiv 2404.02319.  
[2] Microsoft, *SAMMO GitHub Repository*.  
[3] Microsoft, *SAMMO User Guide and Documentation*.  
[4] Huiqiang Jiang, Qianhui Wu, Chin-Yew Lin, Yuqing Yang, and Lili Qiu, *LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models*, arXiv 2310.05736.  
[5] Provided implementation notes and framework documentation for the SAMMO topological optimizer.  
[6] Kalyanmoy Deb, Amrit Pratap, Sameer Agarwal, and T. Meyarivan, *A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II*, IEEE Transactions on Evolutionary Computation, 2002.
