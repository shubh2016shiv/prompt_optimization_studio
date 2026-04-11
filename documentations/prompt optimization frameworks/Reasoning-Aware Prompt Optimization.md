# Reasoning-Aware Prompt Optimization: Declarative Prompting for Test-Time Compute Models

## Overview

For most of the history of large language model (LLM) prompting, the standard way to improve output quality on complex tasks was to tell the model how to think: "reason step by step," "first analyze X, then consider Y," "use a scratchpad," "show your work before answering." These instructions helped because most LLMs are next-token predictors that benefit from the additional context that visible intermediate steps provide.

A newer class of models — known as test-time compute models or inference-time reasoning models, including OpenAI's o1 and o3 series and DeepSeek R1 — operates on a fundamentally different architecture. These models perform their own internal chain-of-thought reasoning before generating output, trained through reinforcement learning to develop search and verification strategies rather than being given explicit step-by-step instructions [1][2]. When a prompt tells one of these models how to reason, it does not help — it interferes. The explicit instructions collide with the model's internally trained reasoning policy, degrading output quality and producing a second failure mode: the model's hidden thought process leaks into the final response as visible prose before the actual output.

Reasoning-Aware Optimization is a prompt engineering framework that addresses this by transforming procedural prompts — those that describe how the model should think — into declarative prompts that describe only what must be produced, what rules must be respected, and what the output must look like. The model's reasoning is left entirely to the model. The prompt defines only the game's rules and the shape of the winning condition.

This guide explains why reasoning models require a different prompting approach, how the transformation pipeline works, what the three output tiers produce, and when this technique applies versus when it would harm performance.

---

## 1. The Problem: What Goes Wrong When You Over-Steer a Reasoning Model

### How Test-Time Compute Models Work

Standard LLMs — GPT-4o, Claude 3.5, Gemini Pro, and similar models — generate responses by predicting the most likely next token given all preceding context. Their accuracy on multi-step reasoning tasks improves substantially when prompted to produce visible intermediate steps, because those steps extend the context the model can condition on. This is why chain-of-thought prompting [3] and "let's think step by step" instructions [4] produce measurable accuracy gains on these models.

Test-time compute models are trained differently. OpenAI's o-series models and DeepSeek R1 are trained with reinforcement learning to generate an internal reasoning trace — a chain of hidden deliberation tokens — before producing any visible output [1][2]. Through this training, they develop their own search and verification strategies: self-reflection, path exploration, backtracking when a line of reasoning fails. These strategies emerge from the reinforcement learning process and are tuned to the model's internal representations, not to human-designed step sequences [2].

OpenAI's official developer guidance for reasoning models states this directly: prompting them to "think step by step" or "explain your reasoning" is unnecessary, since reasoning is performed internally [1]. The recommendation is to keep prompts simple and direct, and to specify constraints and output format rather than reasoning procedures.

### The Two Failure Modes

When a prompt designed for a standard LLM is sent to a reasoning model unchanged, two specific failure modes occur.

**Negative interference** happens when the prompt's explicit procedural instructions force the model to abandon or truncate its internal search policy in order to follow the human-specified steps. The human's reasoning template is rarely as sophisticated as the model's trained policy. The result is a response that is more constrained and less accurate than the model would have produced without the instructions. A model that would have naturally explored multiple paths, caught its own errors, and verified its answer is instead locked into a prescribed sequence that may miss edge cases.

**Explanation bleed** happens when the prompt asks the model to "show your work" or "explain your logic." A reasoning model interprets this as an instruction to emit its internal deliberation into the visible output. The response then begins with several paragraphs of reasoning exposition before the actual answer or JSON payload. For automated pipelines that parse the response programmatically, this extra text breaks the parser. The model was not hallucinating or misunderstanding the task — it was following the instruction to explain itself, and that instruction was wrong for this model class.

These two failure modes — degraded reasoning quality and unparseable output format — both have the same root cause: the prompt is prescribing a reasoning process that the model should be doing on its own, without instruction.

### The Distinction in Practice

The contrast between the two approaches can be seen directly in how the same task is expressed:

```
┌──────────────────────────────────────────────────────────────────┐
│  PROCEDURAL PROMPT  (designed for standard LLMs)                 │
│                                                                  │
│  "Analyze the attached code. First review the imports,           │
│  then check the syntax. Think step by step about the             │
│  security profile. Show your logic before answering.             │
│  Return a JSON with your findings."                              │
│                                                                  │
│  What goes wrong: The model emits its reasoning steps            │
│  as visible text, then emits JSON. The parser sees               │
│  prose before the payload and fails. Internal search             │
│  is constrained by the prescribed review order.                  │
├──────────────────────────────────────────────────────────────────┤
│  DECLARATIVE PROMPT  (designed for reasoning models)             │
│                                                                  │
│  TASK: Audit the attached code for security vulnerabilities.     │
│                                                                  │
│  OUTPUT FORMAT:                                                  │
│  { "flaws": [string], "severity_score": integer }                │
│                                                                  │
│  CONSTRAINTS:                                                    │
│  - severity_score MUST be between 1 and 10                       │
│  - MUST reference only CWE-defined vulnerability classes         │
│  - Emit ONLY the JSON object. No preamble, no explanation.       │
│                                                                  │
│  What the model receives: a clear task, binding rules,           │
│  and a precise output contract. How to audit the code            │
│  is the model's responsibility, not the prompt's.                │
└──────────────────────────────────────────────────────────────────┘
```

The declarative version trusts the model to determine how to perform the audit. It specifies only the boundaries within which the answer must fall and the exact shape of the output. This is the prompting philosophy that Reasoning-Aware Optimization operationalizes.

---

## 2. The Core Concept: Declarative Execution Contracts

A declarative prompt is structured around three and only three components:

**The absolute task** is a single imperative statement of what must be accomplished. It describes the goal without prescribing the path. "Audit the code for security vulnerabilities" is declarative. "First read the imports, then check the syntax, then evaluate the security profile" is procedural. The absolute task provides direction; the reasoning model determines the route.

**Hard constraints** are non-negotiable rules about what the output may or may not contain or reference. They are stated in the affirmative ("severity score MUST be between 1 and 10") or in the negative ("MUST NOT reference vulnerabilities not defined in the CWE standard"). Constraints define the boundaries of acceptable output. They do not describe how to reach acceptable output.

**The output format** is the exact structure the response must take. For structured data tasks, this is a JSON schema. For text tasks, it may be a field specification or a format template. The output format is stated as a binding contract, not as a suggestion. In Reasoning-Aware prompts, the output contract is treated as the most important structural element, because format failure — a valid answer in the wrong shape — is the most common production failure on reasoning models.

These three components are intentionally lean. Reasoning models use available context window tokens as thinking space. A verbose system prompt with extensive elaboration, worked examples, and procedural commentary reduces the space available for the model's internal reasoning process. The design goal is the minimum information required to define the task unambiguously, no more.

---

## 3. End-to-End Pipeline

The optimization process follows four sequential stages, transforming a raw prompt into three declarative variants.

```
Raw prompt (procedural — mixed task, reasoning
instructions, format requirements, context)
                    │
                    ▼
┌──────────────────────────────────────────────┐
│  Stage 1: Strip and Extract                  │
│                                              │
│  Single LLM call with provider-specific      │
│  structured output enforcement               │
│                                              │
│  Extracts three fields:                      │
│  • absolute_task  (string)                   │
│  • hard_constraints  (list of strings)       │
│  • output_format  (string)                   │
│                                              │
│  Explicitly removes:                         │
│  • "think step by step" instructions         │
│  • "show your reasoning" instructions        │
│  • Scratchpad directives                     │
│  • "act as a reasoning agent" language       │
│  • Procedural step sequences                 │
│                                              │
│  ❌ Parse fails → one repair retry call      │
└────────────────────┬─────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────┐
│  Stage 2: Normalize                          │
│                                              │
│  Deterministic Python normalization:         │
│  • Coerce absolute_task to string            │
│  • Coerce hard_constraints to list[str]      │
│  • Coerce output_format to string            │
│                                              │
│  No LLM call. Ensures predictable types      │
│  before assembly regardless of extraction   │
│  response variance.                          │
└────────────────────┬─────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────┐
│  Stage 3: Assemble Three Tiers               │
│                                              │
│  Deterministic Python assembly.              │
│  Same extracted fields, different ordering   │
│  and additional instructions per tier.       │
│                                              │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │Conserv.   │ │Structured │ │Advanced   │  │
│  │           │ │           │ │           │  │
│  │Task       │ │Task       │ │Task       │  │
│  │Constraints│ │Format     │ │Format     │  │
│  │Format     │ │Constraints│ │Constraints│  │
│  │           │ │           │ │+ Suppressor│ │
│  └───────────┘ └───────────┘ └───────────┘  │
└────────────────────┬─────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────┐
│  Stage 4: Quality Gate                       │
│                                              │
│  Reasoning-model-specific critique:          │
│  • Does any CoT language remain?             │
│  • Is the output format isolated and clear?  │
│  • Are constraints stated without procedure? │
│                                              │
│  If quality_gate_mode is enabled: strips     │
│  any surviving procedural language from      │
│  assembled variants before returning.        │
└────────────────────┬─────────────────────────┘
                     │
                     ▼
         Three declarative prompt variants
         + quality scores and metadata
```

Stages 1 is the only stage that calls an LLM. Stages 2 and 3 are fully deterministic Python operations. This design is intentional: the transformation from procedural to declarative should be predictable and reproducible. An LLM rewrite loop — where a model generates and iteratively revises the output prompt — introduces variability that is particularly undesirable here, because the goal is a structurally lean, precisely controlled prompt.

---

## 4. Provider-Aware JSON Extraction

The extraction stage must reliably produce valid JSON containing exactly three keys. Because Stage 3 assembly is deterministic, a malformed or incomplete extraction produces a cascading failure through all three variants. The extraction call therefore uses provider-specific mechanisms to enforce structured output.

```
Extraction call with raw prompt
           │
           ├── Provider: OpenAI
           │   Uses native JSON schema enforcement:
           │   response_format = {
           │     type: "json_schema",
           │     strict: true,
           │     schema: {absolute_task, hard_constraints, output_format}
           │   }
           │   Forces exactly the required keys in the response.
           │
           ├── Provider: Google (Gemini)
           │   Uses Gemini JSON schema response format:
           │   response_format = { type: "json_schema" }
           │   Schema-constrained but with looser key enforcement.
           │
           └── Provider: Anthropic and others
               No native structured output enforcement.
               Falls back to regex and AST parsing:
               • Extracts JSON block from response text
               • Validates required keys are present
               • Retries once with a repair prompt if parsing fails
```

The retry mechanism on parse failure is a single additional call with a repair-focused prompt. If the second attempt also fails, the framework surfaces the error rather than silently assembling variants from partial data. This is a more useful failure mode than producing three plausible-looking but incorrect prompts.

---

## 5. The Three Optimization Tiers

All three variants are assembled from the same three extracted fields. The differences between tiers are ordering, visual formatting, and the presence of an explanation suppressor in the Advanced tier.

### Conservative

The Conservative variant presents the extracted components in their natural logical order: task first, then hard constraints, then output format. It does not reorder components for strategic effect, and it does not add the explanation suppressor.

```
[Conservative variant structure]

TASK:
{absolute_task}

CONSTRAINTS:
{hard_constraints as list}

OUTPUT FORMAT:
{output_format}
```

This tier is appropriate when the prompt's primary problem was procedural language embedded in the task description, and the fix is simply to extract and separate the three components cleanly. It is the lowest-overhead tier and suitable for tasks where the model is not exhibiting explanation bleed — where the output format compliance is already reasonable but the prompt needed structural cleanup.

### Structured

The Structured variant reorders the components to place the output format immediately after the task, before the constraints. This is called **format primacy**: because reasoning models can "overthink" schema requirements and drift from the specified structure [1], placing the output contract high in the prompt — in the primacy attention zone — makes format compliance the most immediate instruction after the task itself.

```
[Structured variant structure]

TASK:
{absolute_task}

OUTPUT FORMAT:         ← moved up before constraints
{output_format}

CONSTRAINTS:
{hard_constraints as list}
```

Research on long-context attention distribution shows that information near the beginning of a prompt receives stronger attention than information in the middle [5]. Format primacy applies this to the most common failure mode of reasoning models on production tasks: schema drift, where the model produces the right answer in the wrong shape. By placing the format contract immediately after the task, the Structured tier treats format compliance as the second most important instruction after "what to do."

This is the recommended production default for data extraction, structured output generation, and any task where output parsability is a constraint.

### Advanced

The Advanced variant includes everything in the Structured tier and adds an **explanation suppressor**: an explicit instruction that the model must emit only the specified output format, with no conversational preamble, no visible reasoning steps, and no explanatory text before or after the payload.

```
[Advanced variant structure]

TASK:
{absolute_task}

OUTPUT FORMAT:
{output_format}

CONSTRAINTS:
{hard_constraints as list}

CRITICAL OUTPUT REQUIREMENT:
Emit ONLY the output format specified above.
Do NOT include any preamble.
Do NOT show reasoning steps.
Do NOT include explanatory text before or after the output.
```

The explanation suppressor directly addresses explanation bleed. When a reasoning model is deployed in an automated pipeline that parses its response — expecting JSON, or a structured record, or a specific field — any text that appears before or after the payload breaks the parser. The suppressor tells the model that even though it reasons internally, none of that reasoning should appear in the visible output.

This tier is the appropriate choice for high-throughput API pipelines, agentic workflows that process the model's output programmatically, and any scenario where explanation bleed has been observed in production.

The three tiers compared:

| Property | Conservative | Structured | Advanced |
|---|---|---|---|
| Component order | Task → Constraints → Format | Task → Format → Constraints | Task → Format → Constraints + Suppressor |
| Format primacy | No | Yes | Yes |
| Explanation suppressor | No | No | Yes |
| Token overhead | Lowest | Low | Moderate |
| Best for | Prompt cleanup, low bleed risk | Production default, schema-critical tasks | High-throughput pipelines, parser-dependent systems |

---

## 6. The Quality Gate

After assembly, a quality gate evaluates the three variants against criteria specific to reasoning models. These criteria differ from the quality checks applied to prompts for standard LLMs.

The primary check is whether any chain-of-thought language survived the extraction stage. If a constraint or task description still contains phrases like "first analyze X, then consider Y" or "work through the problem systematically," the gate identifies and removes them. These phrases are harmful for reasoning models even when they appear in the constraints section rather than in explicit reasoning instructions.

The secondary check is whether the output format is clearly isolated and unambiguous. An output contract buried in a sentence rather than displayed as a clear schema is a format definition that reasoning models may partially follow or reinterpret.

When the quality gate is configured to enhance rather than only critique, it actively rewrites surviving procedural language and restructures unclear format definitions before returning the variants. For production deployments, the `sample_one_variant` quality gate mode is a practical default: it applies full enhancement to the Advanced tier — the most critical for parser-dependent systems — and applies only scoring to the others.

---

## 7. Auto-Routing: When the Framework Is Selected Automatically

When a prompt optimization system has information about which model family will receive the prompt, Reasoning-Aware Optimization should be selected automatically whenever the target is a test-time compute model — regardless of task type. The model family is the deciding factor, not the task domain.

This precedence is important. Other framework selection rules typically look at task type: multi-document retrieval gets one framework, structured extraction gets another, complex reasoning gets a third. For reasoning models, those task-level rules are overridden. A code audit task, a multi-document QA task, and a mathematical reasoning task all receive Reasoning-Aware prompts when the target model performs internal chain-of-thought.

The inverse rule is equally important: Reasoning-Aware Optimization should not be applied to standard LLMs. Removing chain-of-thought instructions from a prompt sent to GPT-4o, Claude, or Gemini Pro will actively degrade performance on complex tasks, because these models rely on visible reasoning context that the declarative format deliberately excludes.

---

## 8. Applying Constraints as Tests, Not Instructions

One of the more counterintuitive aspects of working with reasoning models is how to respond when outputs are wrong. The instinct — trained by years of prompting standard LLMs — is to add reasoning guidance: tell the model where it went wrong and how to approach it differently.

For reasoning models, this instinct is counterproductive. Adding more procedural instructions restricts the model's internal search policy further. The correct response to a wrong answer from a reasoning model is to add **verifiable constraints** that define what a correct answer must satisfy, rather than instructions about how to reach a correct answer.

Consider a code audit that is missing a specific vulnerability class. Rather than adding "Make sure to check all import statements for known-vulnerable packages," the more effective prompt change is: "CONSTRAINT: The analysis MUST identify all third-party dependencies and check each against known CVE records." The first is a procedural instruction. The second is a verifiable boundary that the model's internal reasoning can optimize toward.

This constraint-as-test pattern is analogous to writing unit tests for code: the test specifies what a correct output must satisfy, not how the code should be written. The model, like a competent engineer, determines how to satisfy the specification.

---

## 9. Trade-offs and Practical Constraints

**Applicability is model-class-specific.** Reasoning-Aware Optimization is beneficial for test-time compute models and harmful for standard LLMs. Applying it to the wrong model class degrades performance. Any system that uses this framework must know which model family the prompt is targeting, and must route accordingly.

**The extraction must be reliable.** Because assembly is deterministic and depends entirely on the extraction output, a bad extraction produces bad variants with no self-correction mechanism downstream. The provider-specific structured output enforcement and the single retry loop address this, but the extraction stage remains the primary point of failure. In environments where provider APIs change their JSON schema enforcement behavior, the extraction failure rate should be monitored.

**Verbosity is genuinely harmful here, not just wasteful.** For most prompt engineering frameworks, a more verbose prompt is suboptimal but not actively damaging. For reasoning models, verbose prompts reduce the available context window for the model's internal reasoning tokens. The design principle of minimum necessary information is not stylistic — it reflects how these models use their available context [1].

**The explanation suppressor is probabilistic, not absolute.** The Advanced tier's suppressor instruction significantly reduces explanation bleed but does not eliminate it entirely. Some models, on some tasks, will still emit a brief explanation before the output despite the instruction. For truly parser-critical systems, the application layer should include a response extraction step that locates and parses the expected output format rather than assuming the entire response is the payload.

**Reasoning model behavior continues to evolve.** OpenAI has modified how o-series models handle system messages, prefill, and structured output enforcement across versions. DeepSeek R1's prompting characteristics differ from o1's in specific ways. The declarative contract principle is stable, but specific implementation details — which provider supports which JSON enforcement mode, how aggressively the explanation suppressor needs to be worded — should be verified against the current model version in use.

---

## 10. Common Failure Modes and Diagnostics

| Symptom | Likely cause | Where to look | Correction |
|---|---|---|---|
| Output still includes visible reasoning steps | Explanation suppressor language is too weak or missing | Check whether Advanced tier was selected; inspect suppressor clause wording | Strengthen suppressor language; confirm Advanced tier routing for parser-dependent systems |
| Model hallucinates or drifts from task | Raw prompt relied heavily on procedural instructions that defined the task implicitly; removing them lost the specification | Inspect `hard_constraints` in extracted output; compare to original task intent | Add explicit verifiable constraints that define correct output; do not re-add procedural steps |
| Extraction fails with a JSON parse error | Provider did not honor structured output format, or model returned partial JSON | Check whether provider-specific JSON enforcement is correctly configured; inspect extraction response | Verify provider JSON schema support; adjust extraction prompt and retry behavior |
| Extracted constraints still contain procedural language | Extraction LLM did not strip step-by-step instructions from constraints | Inspect extracted `hard_constraints` list | Strengthen extraction prompt to explicitly identify and remove procedural language from constraints |
| All three variants look nearly identical | Extraction produced very sparse output with only task and format | Inspect extracted fields; check for implicit constraints not surfaced | Add more explicit constraints to the source prompt; re-run extraction |
| Format contract not honored | Output format is ambiguous in the extraction output | Inspect `output_format` field | Rewrite output format as a precise schema rather than a prose description |

The fastest diagnostic pattern is to inspect the extracted fields directly. If the model is producing wrong output, the question is whether the right task, constraints, and format were extracted — and whether any procedural language survived extraction into the constraints list. Failures almost always trace to one of these two sources.

---

## 11. When to Use Reasoning-Aware Optimization — and When Not To

### Strong Fits

Use Reasoning-Aware Optimization whenever the target model is a test-time compute model: OpenAI's o1, o1-mini, o3, o3-mini, DeepSeek R1, QwQ, or any other model trained with reinforcement learning to perform internal chain-of-thought. The framework is appropriate regardless of task type — code analysis, mathematical reasoning, multi-step planning, data extraction, structured output generation — as long as the model family is correct.

It is especially valuable when explanation bleed has been observed in production outputs, when the existing prompt contains explicit reasoning instructions that were designed for a standard LLM, or when a prompt that works well on GPT-4o is being migrated to an o-series model.

### Poor Fits

Do not apply Reasoning-Aware Optimization to standard LLMs. Removing chain-of-thought instructions from prompts for models that rely on visible reasoning context will degrade performance on complex tasks. The framework's extraction stage is specifically designed to purge exactly the instructions that make standard LLMs work well.

Do not apply it when the goal is to capture the model's reasoning trace for audit, debugging, or interpretability purposes. If a visible reasoning chain is the desired output — for example, in a system that logs the model's intermediate steps for human review — the explanation suppressor works against that goal. A chain-of-thought framework is more appropriate in that case.

Do not apply it to simple, low-complexity tasks where procedural guidance genuinely helps with framing rather than reasoning. A task simple enough that the model does not need extended internal reasoning does not benefit from this framework and may perform equivalently with a simpler prompt.

### Relationship to Other Approaches

Chain-of-thought prompting [3] and its self-consistency variants [6] are designed for standard LLMs where visible reasoning context improves accuracy. Reasoning-Aware Optimization is the inverse: it removes that reasoning scaffolding because the target model provides it internally. The two approaches address the same underlying challenge — reliable multi-step reasoning — but for different model classes.

RAL-Writer and XML Structured Bounding are constraint placement and authority-layering frameworks. They are complementary to Reasoning-Aware: a Reasoning-Aware prompt can apply constraint-grouping discipline borrowed from those frameworks within its `hard_constraints` section. The frameworks address different dimensions of prompt quality and can be combined for a model that is both a reasoning model and requires strict output schema compliance.

---

## 12. Conclusion

Reasoning-Aware Optimization reflects a specific and important fact about how a growing class of language models operates: they reason internally, through a process trained by reinforcement learning rather than prescribed by the prompt [1][2]. Prompting these models with explicit reasoning instructions does not guide them — it interferes with them.

The framework's response to this is structural: extract the absolute task, the hard constraints, and the output format from the raw prompt, discard all procedural scaffolding, and assemble a declarative prompt that defines what must be produced and leaves the how to the model. The three tiers vary in how they order and reinforce the output contract, with the Advanced tier adding an explicit suppressor for systems where the model's internal reasoning must not appear in the visible output.

The practical guidance follows from the framework's design. Use it exclusively on test-time compute models — applying it to standard LLMs actively harms performance. Use the Structured tier as the production default for most structured-output tasks. Use the Advanced tier for any system that parses the model's response programmatically. When outputs are wrong, add verifiable constraints that define what correct output must satisfy rather than adding reasoning instructions about how to reach correct output. And verify the extraction output directly when diagnosing failures — the extracted fields are where almost all downstream problems begin.

---

## References

[1] OpenAI. *Reasoning Best Practices — Reasoning Models.* OpenAI Platform Documentation, 2024. https://platform.openai.com/docs/guides/reasoning-best-practices

[2] DeepSeek-AI, Daya Guo, Dejian Yang, et al. *DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning.* arXiv:2501.12948, 2025. https://arxiv.org/abs/2501.12948

[3] Wei, Jason, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Brian Ichter, Fei Xia, Ed H. Chi, Quoc V. Le, and Denny Zhou. *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.* NeurIPS 2022. https://arxiv.org/abs/2201.11903

[4] Kojima, Takeshi, Shixiang Shane Gu, Machel Reid, Yutaka Matsuo, and Yusuke Iwasawa. *Large Language Models are Zero-Shot Reasoners.* NeurIPS 2022. https://arxiv.org/abs/2205.11916

[5] Liu, Nelson F., Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, and Percy Liang. *Lost in the Middle: How Language Models Use Long Contexts.* Transactions of the Association for Computational Linguistics, 2024. https://arxiv.org/abs/2307.03172

[6] Wang, Xuezhi, Jason Wei, Dale Schuurmans, Quoc Le, Ed Chi, Sharan Narang, Aakanksha Chowdhery, and Denny Zhou. *Self-Consistency Improves Chain of Thought Reasoning in Language Models.* ICLR 2023. https://arxiv.org/abs/2203.11171