# XML Structured Bounding: A Technical Guide to Hierarchical Prompt Architecture

## Overview

Most production prompt failures are not failures of the underlying model. They are failures of structure. When a prompt mixes task instructions, user data, output rules, and safety requirements into one undivided block of text, the model is left to infer which sentences are authoritative and which are merely context. That inference is fragile, especially as prompts grow longer or incorporate untrusted external content.

XML Structured Bounding is an approach to prompt engineering that addresses this by reorganizing a prompt into a layered system of explicitly labeled sections. Each section tells the model what role its contents play — what must be obeyed, what can be analyzed, what defines a valid response, and what should be ignored when it conflicts with the rules. The result is a prompt architecture that behaves less like a paragraph and more like a small system design.

This guide explains the problem the approach solves, the concepts behind it, the end-to-end workflow, the architecture of a structured prompt, the trade-offs between optimization tiers, known failure modes, and when to use or avoid the technique. It is grounded in published research on long-context attention, prompt injection, and output format adherence.

---

## 1. The Problem: Boundary Confusion in Production Prompts

As prompts grow to include multiple instruction types — task definitions, retrieved documents, user queries, output schemas, and safety rules — they accumulate a structural problem that is separate from the quality of any individual sentence. The model cannot reliably distinguish which text has authority over its behavior and which text is material to be processed.

This produces five distinct failure modes that XML Structured Bounding is specifically designed to reduce.

**Format drift** occurs when the model begins a response in the requested output format — say, JSON — and then slips into prose, adds unrequested fields, or omits required ones. The root cause is usually that the output schema was described as one sentence within the task paragraph instead of isolated as a dedicated contract.

**Constraint loss** occurs when the model follows most of a long prompt correctly but weakens or ignores a mandatory rule. Long-context models are not uniformly attentive across their input. Research by Liu et al. found that performance on information retrieval tasks degrades significantly when relevant content appears in the middle of the context window rather than near the beginning or end [1]. Constraints buried midway through a long prompt are at genuine risk of underuse.

**Prompt injection susceptibility** occurs when untrusted content — a retrieved document, a user message, or a tool output — contains text that looks like an instruction and causes the model to follow it. Perez and Ribeiro demonstrated that models can be manipulated into ignoring prior instructions or revealing system prompts when adversarial strings are embedded in user input [2]. Greshake et al. extended this to indirect injection, showing that malicious instructions embedded in web pages and external documents retrieved by language model systems can achieve similar effects without any cooperation from the user [3].

**Debuggability collapse** occurs when a flat prompt fails silently and the engineering team cannot determine which part of the prompt caused the failure. There is no section to inspect, no boundary to check, and no stable surface for structured diagnosis.

**Long-context under-attention** occurs when critical instructions are placed in the middle of a long context. The "lost in the middle" effect documented by Liu et al. is a practical reason to place the most important constraints early and, for high-stakes prompts, to repeat them near the end [1].

XML Structured Bounding addresses all five of these by converting the prompt from a flat prose block into a layered architecture with explicit role-bearing sections.

---

## 2. Core Concepts

### Semantic Boundaries

A semantic boundary is a visible label that wraps a section of the prompt and tells the model what kind of content is inside. The label is named for its role, not its content.

For example, a section named `<output_contract>` tells the model that the enclosed text defines the shape of a valid response. A section named `<constraint_graph>` tells the model that the enclosed text contains rules it must not break. A section named `<input_variables>` tells the model that the enclosed text is runtime data to be processed, not directives to be followed.

Anthropic's official prompting guidance specifically recommends XML tags for complex prompts that mix instructions, context, examples, and variable inputs, citing improved structure and parsing reliability [4]. The key principle is consistent, descriptive naming: tags should say what role the content plays, not what the content happens to be.

Semantic boundaries do not provide absolute security. The model still processes everything as tokens. Their function is to reduce ambiguity and create a reliable review surface for both the model and the engineering team.

### The Directive-Data Separation

The most foundational principle of XML Structured Bounding is separating directives from data.

A **directive** is text the model should obey: task instructions, mandatory constraints, output contracts, safety rules. A **data block** is text the model should analyze, summarize, classify, or retrieve from: user questions, retrieved documents, conversation history, uploaded files.

When these two types appear in the same unmarked text, the model can treat data as directives or treat directives as data. Explicit section boundaries reduce both risks. System instructions live in authoritative sections. Runtime content lives in named data containers.

### Priority and the Instruction Hierarchy

Not all instructions carry the same weight. A mandatory rule such as "never invent facts not present in the source documents" should not be overridden by a style preference such as "use a friendly tone." Without explicit separation, a model may treat both as comparable guidance.

XML Structured Bounding separates instructions into a hierarchy:

- **Hard constraints** are non-negotiable rules stated using MUST and MUST NOT language.
- **Soft preferences** are desirable but lower-authority guidance such as tone, verbosity, or writing style.
- **Output contracts** define the response format as a binding specification rather than a suggestion.

Higher-priority instructions are placed earlier in the prompt. The hierarchy makes execution order explicit and makes the prompt reviewable: if a constraint fails, there is an identifiable section to inspect.

### The Output Contract

Treating the output format as a contract rather than a passing description is central to this approach. An output contract is a dedicated section that specifies exactly what a valid response looks like — which fields are required, which are forbidden, what the data types are, and what the model should do if it cannot produce a compliant response.

In practice, a schema note such as "Return JSON with `answer`, `citations`, and `confidence` fields" belongs in its own labeled section. A model following this section has a clear target. Downstream systems parsing the response have a known specification to validate against.

### The Ontology Blueprint

Rather than rewriting a prompt directly from raw prose to a structured format, the approach benefits from an intermediate step: extracting a structured summary of the prompt's meaning before performing the rewrite.

This intermediate representation — an ontology blueprint — captures the prompt's objective, its instruction hierarchy, its hard constraints, its soft preferences, its required output format, and its safety behavior. The blueprint serves three purposes: it makes the rewrite more consistent, it provides a fallback path if the rewrite fails, and it creates a reviewable artifact that separates "understanding the prompt" from "rewriting the prompt."

### Recency Echo

Because long-context attention is not uniform, the most critical constraints deserve two placements: early in the prompt, where they establish authority, and again near the end, where they are more salient at generation time. This second placement is called a recency echo. It is a short reminder block containing only the hard constraints, positioned after the main system content and before the model begins its response.

The practical principle behind the recency echo is drawn directly from Liu et al.'s findings: relevant information placed near the end of the context is used more reliably than information placed in the middle [1]. The echo should contain only critical rules, not a full repetition of the prompt, to avoid token bloat and noise.

---

## 3. System Architecture

A fully structured prompt is organized into layered sections, each with a defined role. The diagram below shows the hierarchy.

```
┌─────────────────────────────────────────────────────┐
│                  <system_directives>                │
│  (Authoritative rule container - highest authority) │
│                                                     │
│   ┌──────────────────────────────────────────────┐  │
│   │           <task_objective>                   │  │
│   │     Single, bounded description of the task  │  │
│   └──────────────────────────────────────────────┘  │
│                                                     │
│   ┌──────────────────────────────────────────────┐  │
│   │        <instruction_hierarchy>               │  │
│   │     Priority ordering and dependencies       │  │
│   └──────────────────────────────────────────────┘  │
│                                                     │
│   ┌──────────────────────────────────────────────┐  │
│   │          <constraint_graph>                  │  │
│   │     MUST / MUST NOT mandatory rules          │  │
│   └──────────────────────────────────────────────┘  │
│                                                     │
│   ┌──────────────────────────────────────────────┐  │
│   │          <preference_layer>                  │  │
│   │     Soft guidance - lower authority          │  │
│   └──────────────────────────────────────────────┘  │
│                                                     │
│   ┌──────────────────────────────────────────────┐  │
│   │          <output_contract>                   │  │
│   │     Response format and schema               │  │
│   └──────────────────────────────────────────────┘  │
│                                                     │
│   ┌──────────────────────────────────────────────┐  │
│   │           <safety_bounds>                    │  │
│   │     Behavior under uncertainty or gaps       │  │
│   └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              <input_variables>                      │
│   Runtime data (documents, user query, records)     │
│   Intentionally separate from system authority      │
└─────────────────────────────────────────────────────┘

                          ↓  (Advanced tier only)

┌─────────────────────────────────────────────────────┐
│              <restate_critical>                     │
│   Recency echo — hard constraints repeated          │
│   near end of prompt for long-context salience      │
└─────────────────────────────────────────────────────┘
```

Each section answers a different engineering question. `<task_objective>` answers: what is the task? `<constraint_graph>` answers: what must never happen? `<output_contract>` answers: what format is required? `<safety_bounds>` answers: what should the model do when the provided context is insufficient? `<input_variables>` answers: what data will be provided at runtime?

The separation between `<system_directives>` and `<input_variables>` is the most important structural boundary. System directives are stable, authored by the engineer, and define authority. Input variables are dynamic, may originate from users or external systems, and must be processed as data, not followed as instructions.

---

## 4. End-to-End Workflow

The complete workflow from raw prompt to optimized structured output follows nine steps.

```
Raw prompt + gap answers
         │
         ▼
┌─────────────────────┐
│  1. Gap enrichment  │  Add any missing task information
└────────┬────────────┘
         │
         ▼
┌──────────────────────────┐
│  2. Ontology blueprint   │  Parse: objective, hierarchy,
│     extraction           │  constraints, outputs, safety
└────────┬─────────────────┘
         │          │
    success         failure
         │          │
         │    ┌─────▼──────────────┐
         │    │  Default blueprint  │  Anti-hallucination defaults,
         │    │  (fallback)         │  basic task/output/constraint nodes
         │    └─────┬──────────────┘
         │          │
         └──────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────┐
│  3. Three-tier LLM rewrite                           │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Conservative│  │  Structured │  │  Advanced   │  │
│  │ Clear       │  │  Hierarchy  │  │  Max safety │  │
│  │ structure,  │  │  MUST/NOT   │  │  Anti-inject│  │
│  │ minimal     │  │  validation │  │  schema     │  │
│  │ overhead    │  │  fidelity   │  │  fidelity   │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │
└─────────┼────────────────┼────────────────┼──────────┘
          │                │                │
          │    rewrite failure on any tier  │
          │           ┌────▼────┐           │
          │           │Fallback │           │
          │           │template │           │
          │           └─────────┘           │
          └────────────────┬────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │  4. Input variable      │
              │     injection           │
              │  {{documents}},         │
              │  {{question}}, etc.     │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │  5. Advanced recency    │  (Advanced variant only)
              │     echo appended       │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │  6. Quality gate        │
              │  Critique / enhance     │
              │  (configurable)         │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │  Three prompt variants  │
              │  ready for use          │
              └─────────────────────────┘
```

**Step 1 — Gap enrichment** incorporates any missing task information that was identified before optimization. The parser should reflect the best available specification, not only the original incomplete prompt.

**Step 2 — Ontology blueprint extraction** uses an LLM call to produce a structured JSON summary containing the objective, instruction hierarchy, hard constraints, soft preferences, required outputs, and safety bounds. If this parse fails — due to a malformed or empty LLM response — the system generates a default blueprint containing anti-hallucination constraints and a basic task/output/constraint structure. The pipeline continues regardless.

**Step 3 — Three-tier rewrite** sends the raw prompt, blueprint JSON, and a tier-specific objective to the LLM. Each tier optimizes for a different production trade-off: minimum overhead (Conservative), reliable constraint enforcement (Structured), or maximum safety and injection resistance (Advanced). If any tier's rewrite fails, a deterministic fallback template builds a usable prompt directly from the blueprint fields.

**Step 4 — Input variable injection** appends runtime data placeholders in a clearly labeled section. For XML-compatible providers, this uses `<input_variables>` tags. For Markdown-style providers, the equivalent heading structure is used. The goal in both cases is the same: runtime data is visible to the final prompt but visually and semantically distinct from the system directives.

**Step 5 — Advanced recency echo** appends the hard constraints a second time, near the end of the Advanced variant. This is grounded in the placement strategy suggested by long-context attention research [1].

**Step 6 — Quality gate** critiques and optionally improves all three variants. The gate checks for weak boundaries, missing output contracts, fragile constraints, and insufficient hallucination resistance.

---

## 5. Constraint Placement Strategy

The diagram below shows where different instruction types should appear in the final prompt, and why position matters for long-context reliability.

```
Prompt start (highest attention)
─────────────────────────────────
│  <task_objective>              │  ← Establish task first
│  <constraint_graph> (MUST/NOT) │  ← Hard constraints early
─────────────────────────────────
│  <instruction_hierarchy>       │  ← Ordering and dependencies
│  <preference_layer>            │  ← Lower authority, lower position
│  <output_contract>             │  ← Format contract before data
│  <safety_bounds>               │  ← Uncertainty behavior defined
─────────────────────────────────
│  <input_variables>             │  ← Runtime data, clearly separate
│  {{documents}}, {{question}}   │
─────────────────────────────────
│  <restate_critical>            │  ← Advanced tier: echo hard rules
│  (hard constraints repeated)   │  ← Near end = high recency salience
─────────────────────────────────
Prompt end (high recency attention)
```

The placement follows a principle derived from empirical observation of long-context model behavior: both the beginning and end of the input receive more reliable attention than the middle [1]. Critical rules go early to establish authority. The recency echo uses the end of the prompt to reinforce only the most important rules before generation begins.

The middle of the prompt — where retrieved documents, examples, and context typically appear — is treated as a lower-reliability zone for constraint placement. Instructions that must be followed should not be first introduced there.

---

## 6. The Three Optimization Tiers

XML Structured Bounding always produces three variants because production prompt optimization rarely has a single correct answer. The three tiers represent different points on the cost-reliability spectrum.

### Conservative

The Conservative tier adds clear XML boundaries with minimal structural overhead. It is the lowest-cost variant, appropriate for low-to-medium complexity tasks where the original prompt is substantially correct but lacks explicit separation. It may not include the strongest anti-injection or validation language, making it less suitable when untrusted external content is involved.

### Structured

The Structured tier strengthens the instruction hierarchy, enforces MUST and MUST NOT constraint language, adds a validation self-check, and explicitly enforces schema fidelity. It carries a moderate token cost and represents a sensible production default for question-answering, extraction, and structured-output workflows where reliability matters.

### Advanced

The Advanced tier maximizes safety, schema fidelity, and injection resistance. It adds explicit anti-injection language, stronger safety behavior, and the recency echo of hard constraints. It is the highest-cost variant and is appropriate for high-stakes workflows, untrusted document sources, multi-document QA, and contexts where a single violated constraint can cause meaningful downstream harm.

The relationship between tiers can be summarized as follows:

| Property | Conservative | Structured | Advanced |
|---|---|---|---|
| Token cost | Lowest | Moderate | Highest |
| Constraint enforcement | Basic | Strong (MUST/NOT) | Strong + recency echo |
| Anti-injection language | Minimal | Moderate | Explicit |
| Validation self-check | No | Yes | Yes |
| Recency echo | No | No | Yes |
| Best for | Simple tasks, readable structure | Production QA and extraction | High-stakes, untrusted content |

### Quality Gate Modes

Separate from the tier selection, a quality gate runs after all three variants are generated. The gate is configurable:

| Mode | Behavior | Use case |
|---|---|---|
| `full` | Critiques and conditionally enhances all three variants | Production-grade optimization |
| `sample_one_variant` | Fully evaluates one variant, initial estimates for the others | Cost-sensitive review |
| `critique_only` | Scores variants without rewriting | Auditing and benchmarking |
| `off` | Skips critique and enhancement entirely | Fast development loops |

The quality gate checks for problems that the XML tier definitions themselves cannot detect: sections that are too vague to be useful, output contracts that omit required fields, and safety bounds that are too generic to prevent hallucination.

---

## 7. Provider Formatting Adaptation

The semantic structure of XML Structured Bounding — the concept of role-bearing sections — is provider-independent. The specific delimiter syntax adapts to each provider's conventions.

| Provider | Delimiter style | Effect |
|---|---|---|
| Anthropic (Claude) | XML tags | Full XML sections, optional prefill suggestion for first response token |
| Google (Gemini) | XML tags | XML sections without Claude-specific prefill |
| OpenAI | Markdown headings | Markdown-style sections preserve the same semantic separation |

The practical takeaway is that XML Structured Bounding is a semantics-first approach, not a syntax-first approach. The goal is explicit role separation; the exact delimiter format is an implementation detail that follows provider best practices.

Prefill suggestions — a proposed opening token or phrase for the assistant's response, such as `{` to encourage immediate JSON output — are generated as metadata for Anthropic providers. Teams should verify current provider support before relying on this feature, as support for prefilled final assistant turns varies by model version.

---

## 8. Implementation Considerations

### Token Budget

Blueprint extraction and tiered LLM rewrites add token cost above a plain prompt. The Advanced tier and the quality gate in `full` mode add the most overhead. For workflows where the prompt is stable and changes infrequently, this cost is a one-time optimization investment. For workflows where prompts are dynamically generated per request, it is a recurring operational cost and should be weighed against the reliability gain.

Concrete configuration points are the token budget for blueprint parsing — which determines how much JSON detail the blueprint can contain — and the token budget per tier rewrite — which determines how verbose and complete each variant can be. Setting these too low can produce truncated blueprints or incomplete rewrites; setting them too high creates unnecessary cost.

### Fallback Reliability

The pipeline is designed to remain resilient if any LLM call in the optimization process fails. If the blueprint parse returns invalid JSON or an empty response, a default blueprint is constructed. If a tier rewrite returns empty text, a deterministic fallback template builds a usable XML-style prompt from the blueprint fields.

This fallback chain means the framework should always return a valid, structured prompt — not a partial failure. Production deployments should verify that fallback paths are exercised in testing.

### Runtime Data vs. Configuration

The distinction between system configuration (authored by engineers, stable across requests) and runtime data (user-provided, dynamic, potentially untrusted) must be maintained in deployment, not just in the optimized prompt template. If the final prompt template has `{{documents}}` and `{{question}}` as placeholders, the system filling those placeholders must ensure the content is inserted into the designated data sections and not concatenated into the directive sections.

---

## 9. Security Limits

XML Structured Bounding meaningfully reduces several classes of prompt failure related to boundary confusion. It does not eliminate prompt injection risk. XML tags are instructions to a language model, not cryptographic controls or sandboxes. A sufficiently constructed adversarial string can still influence model behavior regardless of surrounding structural labels, particularly if the model being used has not been fine-tuned with strong instruction following for the specific tag schema in use.

OpenAI's security guidance on prompt injections notes that robust mitigation of these attacks requires layered defenses beyond prompting, including tool-level permissions, output validation, and system-level controls [5].

For high-risk systems — particularly agentic workflows where the model can take real-world actions — XML Structured Bounding should be one layer in a defense-in-depth strategy. Other layers include tool permission allowlists, explicit confirmation steps before consequential actions, output schema validation at the application layer, monitoring and logging, and least-privilege data access.

Prompt-level contracts improve adherence; runtime validation remains necessary. If the system expects JSON, parse it and reject invalid responses programmatically. If the system expects specific fields, check for them explicitly. Do not depend on the model's compliance with `<output_contract>` as the sole guarantor of response validity.

---

## 10. Common Failure Modes and Diagnostics

The fastest diagnostic strategy is to trace a failure to its responsible section.

| Symptom | Likely cause | Where to look | Correction |
|---|---|---|---|
| Blueprint parse fails | LLM returned invalid or non-object JSON | Blueprint extraction call and JSON normalization | Use default blueprint fallback; tighten extraction prompt if recurring |
| All three variants look nearly identical | Tier objectives are not creating enough structural differentiation | Compare the rewrite prompts and objectives for each tier | Strengthen tier-specific rewrite instructions or add template checks |
| Output format still drifts | `<output_contract>` is weak or quality gate is off | Inspect the output contract section and quality gate mode | Add explicit schema notes; enable `full` quality gate mode |
| Constraints are ignored | Hard rules are vague, buried, or not echoed | Inspect `<constraint_graph>` and Advanced `<restate_critical>` | Convert rules to MUST/MUST NOT language; switch to Advanced tier |
| Prompt is too long | Advanced protocol or rewrite verbosity inflated token count | Compare token estimates across tiers | Use Structured tier; lower rewrite token budget; remove non-critical preferences |
| Injection-like behavior persists | Dynamic content is not clearly separated or model follows untrusted text | Inspect `<input_variables>` handling and anti-injection rules | Use Advanced tier; add system-level tool and data safeguards |
| Recency echo missing | Advanced path was not used or no hard constraints were available | Check that the Advanced variant path is selected and blueprint has hard constraints | Confirm blueprint contains hard constraints and Advanced variant is requested |
| Missing runtime variables | Input variable declarations are empty or malformed | Inspect the request payload and the generated variable block | Provide clear variable declarations such as `{{documents}} — source documents` |
| Quality gate changed the prompt unexpectedly | Critic enhancement rewrote weak sections | Check `quality_evaluation.was_enhanced` in the response | Use `critique_only` mode for audit, or improve the initial framework prompt |

Format failures typically point to `<output_contract>`. Hallucination failures point to `<safety_bounds>` and `<constraint_graph>`. Injection failures point to directive/data separation. Ordering failures point to `<instruction_hierarchy>`.

---

## 11. When to Use It — and When Not To

### Good Fits

XML Structured Bounding is well suited to multi-document question answering, retrieval-augmented generation (RAG), structured JSON or schema output tasks, workflows where the input includes untrusted user text or externally retrieved documents, prompts with many instruction layers, and systems where prompt failures need to be diagnosable and auditable.

It is also a strong fit when the prompt must draw a clear line between "the document says this" and "the model should do this." That distinction is the framework's most important and most well-supported use case.

### Poor Fits

Avoid it for very short prompts, simple classification, simple routing, casual creative writing, or cases where token budget is the dominant constraint. A lighter approach without tiered rewrites or explicit section architecture will be faster and cheaper with comparable results for simple tasks.

Delay it when the prompt lacks basic task information. If the prompt does not specify the task, context, role, tone, or execution format, those gaps should be filled before adding XML structure. Structure cannot compensate for a missing specification.

Avoid treating it as a complete security solution for agentic systems that can take real-world actions. Prompt boundaries must be paired with permissioning, confirmation steps, output validation, and tool-level constraints.

### Comparison with Alternative Approaches

A leaner prompt framework without tiered rewrites or explicit section architecture trades boundary management for lower token cost and simpler maintenance. XML Structured Bounding is stronger for long-context data separation but more expensive.

Chain-of-thought prompting (CoT) adds reasoning demonstrations and examples to improve step-by-step accuracy. XML Structured Bounding does not add examples or demonstrations — it structures authority and data. The two approaches can be combined: a structured prompt can include a `<reasoning_guidance>` section containing CoT-style instructions.

Automatic prompt optimization methods based on iterative search over a dataset — such as OPRO [6] — optimize prompts empirically by running candidates against labeled examples. XML Structured Bounding does not require a dataset; it applies structural best practices rather than empirical search. The two approaches are complementary: structural discipline can be applied to prompts before or after empirical optimization.

---

## 12. Research Foundation

XML Structured Bounding is grounded in four areas of published research and provider guidance.

**Provider guidance on structured prompting.** Anthropic's official prompting documentation recommends XML tags specifically for complex prompts that mix instructions, context, examples, and variable inputs, and emphasizes consistent, descriptive tag names and nested tags for hierarchical content [4]. This directly supports the approach's use of named role-bearing sections.

**Long-context attention distribution.** Liu et al. showed in their "Lost in the Middle" study that language models retrieve information more reliably when it appears at the beginning or end of a long context, and perform worse when the relevant information is in the middle [1]. This supports placing critical constraints early, avoiding instruction placement in the middle of long contexts, and using a recency echo in the Advanced tier.

**Direct prompt injection.** Perez and Ribeiro demonstrated that language models can be manipulated through user-supplied text into ignoring prior instructions, revealing hidden content, or taking unauthorized actions [2]. This motivates explicit directive/data separation and anti-injection language in the Advanced tier.

**Indirect prompt injection.** Greshake et al. extended the injection problem to externally retrieved content, showing that malicious instructions embedded in web pages, documents, and other retrieved data can influence model behavior without any malicious cooperation from the human user [3]. This directly motivates the practice of cordoning retrieved content in `<input_variables>` and separating it from system directives.

**OpenAI security framing.** OpenAI's published guidance on prompt injection frames the problem as a layered security challenge, noting that robust mitigation requires defenses beyond prompting alone [5]. This aligns with this framework's stated security limits: structure reduces confusion but does not replace application-layer validation and system-level controls.

The well-supported conclusion is specific and measured: explicit structure, clear authority boundaries, deliberate constraint placement, and layered security practices reduce several common classes of prompt failure. XML structure alone does not guarantee reliability, and no prompt architecture eliminates adversarial risk against a sufficiently capable attacker.

---

## 13. Conclusion

XML Structured Bounding turns a prompt from a flat paragraph into a bounded instruction architecture. Its core contribution is not cosmetic: labeled sections reduce the five most common failure modes in complex prompt systems — format drift, constraint loss, prompt injection susceptibility, debuggability collapse, and long-context under-attention — by making the roles of different content types explicit.

The framework operates in three tiers (Conservative, Structured, Advanced) and two fallback mechanisms (default blueprint, deterministic template) to remain resilient under LLM failure. It adapts its delimiter style to provider conventions while preserving the same semantic structure. It is grounded in published research on long-context attention, injection attacks, and format adherence, and its design limits are honestly stated: it reduces boundary confusion, but it is not a security sandbox.

The practical decision framework is straightforward. Use it when a prompt involves long context, multiple instruction types, dynamic or untrusted data, strict output schemas, or failure modes that need to be auditable. Use the Structured tier as the default production choice. Upgrade to Advanced for high-stakes or untrusted-data workflows. Pair it with application-layer validation, tool-level permissions, and monitoring for any system where the model can take consequential actions.

The central principle — that models handle complex prompts more reliably when each piece of text is told what it is allowed to mean — is both the framework's simplest summary and its strongest justification.

---

## References

[1] Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang. *Lost in the Middle: How Language Models Use Long Contexts.* Transactions of the Association for Computational Linguistics, 2024. https://arxiv.org/abs/2307.03172

[2] Fábio Perez, Ian Ribeiro. *Ignore Previous Prompt: Attack Techniques For Language Models.* Workshop on Trustworthy and Reliable Large-Scale Machine Learning Models, NeurIPS 2022. https://arxiv.org/abs/2211.09527

[3] Kai Greshake, Sahar Abdelnabi, Shailesh Mishra, Christoph Endres, Thorsten Holz, Mario Fritz. *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec Workshop, CCS 2023. https://arxiv.org/abs/2302.12173

[4] Anthropic. *Claude Prompting Best Practices — Structure Prompts with XML Tags.* Anthropic Platform Documentation. https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags

[5] OpenAI. *Understanding Prompt Injections.* OpenAI Platform Documentation. https://openai.com/index/prompt-injections/

[6] Chengrun Yang, Xuezhi Wang, Yifeng Lu, Hanxiao Liu, Quoc V. Le, Denny Zhou, Xinyun Chen. *Large Language Models as Optimizers.* ICLR 2024. https://arxiv.org/abs/2309.03409