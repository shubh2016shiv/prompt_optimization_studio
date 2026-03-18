# APOST v4 — Automated Prompt Optimisation & Structuring Tool
## Complete Technical Documentation

> **Author perspective:** This document is written from the point of view of a Senior Software Engineer and Generative AI Architect with deep experience in production LLM systems, context engineering, and enterprise prompt infrastructure. It is intended for developers, ML engineers, and AI architects who want to understand not just *how* to use APOST, but *why* every design decision was made, and what academic and industry research backs it.

---

## Table of Contents

1. [Introduction & The Problem Space](#1-introduction--the-problem-space)
   - 1.1 [Why Prompts Break at Scale](#11-why-prompts-break-at-scale)
   - 1.2 [The Communication Gap Between Human Intent and Machine Execution](#12-the-communication-gap-between-human-intent-and-machine-execution)
   - 1.3 [What APOST Solves](#13-what-apost-solves)
   - 1.4 [Who Should Use This Tool](#14-who-should-use-this-tool)

2. [Theoretical Foundations](#2-theoretical-foundations)
   - 2.1 [The Transformer Attention Mechanism](#21-the-transformer-attention-mechanism)
   - 2.2 [The Lost-in-the-Middle Phenomenon](#22-the-lost-in-the-middle-phenomenon)
   - 2.3 [Positional Bias and the U-Shaped Attention Curve](#23-positional-bias-and-the-u-shaped-attention-curve)
   - 2.4 [Overshoot and Undershoot: The Two Failure Modes](#24-overshoot-and-undershoot-the-two-failure-modes)
   - 2.5 [Cognitive Load and Contextual Interference](#25-cognitive-load-and-contextual-interference)
   - 2.6 [Instruction Coverage as a Measurable Metric](#26-instruction-coverage-as-a-measurable-metric)

3. [The TCRTE Framework — Coverage-Driven Prompt Design](#3-the-tcrte-framework--coverage-driven-prompt-design)
   - 3.1 [What TCRTE Is and Where It Comes From](#31-what-tcrte-is-and-where-it-comes-from)
   - 3.2 [The Five Dimensions Explained](#32-the-five-dimensions-explained)
   - 3.3 [TCRTE Scoring Methodology](#33-tcrte-scoring-methodology)
   - 3.4 [TCRTE vs. Other Frameworks: When to Use Which](#34-tcrte-vs-other-frameworks-when-to-use-which)

4. [Optimisation Frameworks Implemented in APOST](#4-optimisation-frameworks-implemented-in-apost)
   - 4.1 [KERNEL — The Minimalist Discipline](#41-kernel--the-minimalist-discipline)
   - 4.2 [XML Structured Bounding — Anthropic's Semantic Hierarchy](#42-xml-structured-bounding--anthropics-semantic-hierarchy)
   - 4.3 [Progressive Disclosure — The Agent Skills Architecture](#43-progressive-disclosure--the-agent-skills-architecture)
   - 4.4 [CoT Ensemble — The Medprompt Pattern](#44-cot-ensemble--the-medprompt-pattern)
   - 4.5 [TextGrad — Textual Backpropagation](#45-textgrad--textual-backpropagation)
   - 4.6 [Reasoning-Aware Mode — For o-series and Extended Thinking](#46-reasoning-aware-mode--for-o-series-and-extended-thinking)
   - 4.7 [CREATE — Sequential Instruction Architecture](#47-create--sequential-instruction-architecture)
   - 4.8 [Auto-Select — The Meta-Decision Layer](#48-auto-select--the-meta-decision-layer)

5. [Advanced Injection Techniques](#5-advanced-injection-techniques)
   - 5.1 [CoRe — Context Repetition for Multi-Hop Reasoning](#51-core--context-repetition-for-multi-hop-reasoning)
   - 5.2 [RAL-Writer Restate — Beating the Attention Blind Spot](#52-ral-writer-restate--beating-the-attention-blind-spot)
   - 5.3 [Claude Prefill — Locking Output Format at the Token Level](#53-claude-prefill--locking-output-format-at-the-token-level)

6. [Provider-Specific Engineering](#6-provider-specific-engineering)
   - 6.1 [Anthropic Claude — XML-First Architecture](#61-anthropic-claude--xml-first-architecture)
   - 6.2 [OpenAI GPT and o-series — Markdown and Reasoning Separation](#62-openai-gpt-and-o-series--markdown-and-reasoning-separation)
   - 6.3 [Google Gemini — Structured Data and System Instruction Separation](#63-google-gemini--structured-data-and-system-instruction-separation)
   - 6.4 [Reasoning Model Treatment Across All Providers](#64-reasoning-model-treatment-across-all-providers)

7. [APOST v4 Architecture — System Design Deep Dive](#7-apost-v4-architecture--system-design-deep-dive)
   - 7.1 [The Four-Phase State Machine](#71-the-four-phase-state-machine)
   - 7.2 [Phase 1 — Gap Analysis Engine](#72-phase-1--gap-analysis-engine)
   - 7.3 [Phase 2 — The Interview Layer](#73-phase-2--the-interview-layer)
   - 7.4 [Phase 3 — The Optimisation Engine](#74-phase-3--the-optimisation-engine)
   - 7.5 [Phase 4 — Results and the Three-Variant Strategy](#75-phase-4--results-and-the-three-variant-strategy)
   - 7.6 [The Conversational Refinement Layer](#76-the-conversational-refinement-layer)
   - 7.7 [Context Seeding — Why the Chat Knows Everything](#77-context-seeding--why-the-chat-knows-everything)

8. [The Three-Column UI — Architectural Rationale](#8-the-three-column-ui--architectural-rationale)
   - 8.1 [Left Panel — Stable Configuration](#81-left-panel--stable-configuration)
   - 8.2 [Middle Panel — Workflow Execution](#82-middle-panel--workflow-execution)
   - 8.3 [Right Panel — Conversational Intelligence](#83-right-panel--conversational-intelligence)

9. [User Guide — Step-by-Step Workflows](#9-user-guide--step-by-step-workflows)
   - 9.1 [Quickstart — Your First Optimisation in 5 Minutes](#91-quickstart--your-first-optimisation-in-5-minutes)
   - 9.2 [Full Workflow — With Gap Interview](#92-full-workflow--with-gap-interview)
   - 9.3 [Reading Your Coverage Report](#93-reading-your-coverage-report)
   - 9.4 [Understanding the Three Output Variants](#94-understanding-the-three-output-variants)
   - 9.5 [Using the Prefill Tab](#95-using-the-prefill-tab)
   - 9.6 [Refining with the AI Chat](#96-refining-with-the-ai-chat)
   - 9.7 [Quick Action Reference](#97-quick-action-reference)

10. [Task Type Selection Guide](#10-task-type-selection-guide)

11. [Framework Selection Decision Guide](#11-framework-selection-decision-guide)

12. [Real-World Examples](#12-real-world-examples)
    - 12.1 [Example A — RAG Pipeline Prompt for Financial Analysis](#121-example-a--rag-pipeline-prompt-for-financial-analysis)
    - 12.2 [Example B — Coding Agent System Prompt](#122-example-b--coding-agent-system-prompt)
    - 12.3 [Example C — Customer Support Routing](#123-example-c--customer-support-routing)

13. [Common Mistakes and Anti-Patterns](#13-common-mistakes-and-anti-patterns)

14. [Extending and Integrating APOST](#14-extending-and-integrating-apost)

15. [Glossary of Terms](#15-glossary-of-terms)

16. [References and Further Reading](#16-references-and-further-reading)

---

## 1. Introduction & The Problem Space

### 1.1 Why Prompts Break at Scale

When a developer first writes a prompt for a language model, the experience feels almost magical. You write a sentence, the model responds intelligently. You add a constraint, it follows it. You add a few more rules, it still works. Then somewhere between ten constraints and thirty, something breaks. The model starts ignoring specific rules. It hallucinates. It produces output that is *close* to what you wanted but missing critical structural requirements. You tune one thing and a different thing regresses.

This is not a bug in the model. It is an architectural reality of how transformer-based language models process information. **Prompts are not interpreted with uniform attention.** They are processed with a bias that favours the beginning and end of a sequence, and systematically neglects the middle. The prompt engineering market, valued at approximately $280 million in its early years, is projected to reach $2.5 billion by 2032 — not because writing prompts is glamorous, but because getting them right at production scale is genuinely hard.

The fundamental insight behind APOST is this: **the primary barrier to AI value in production systems is not model capability — it is the structural communication gap between human intent and machine execution.** This tool exists to close that gap systematically, using research-backed methods rather than intuition and trial and error.

### 1.2 The Communication Gap Between Human Intent and Machine Execution

A typical enterprise AI deployment involves prompts that must encode:

- Business logic and domain rules
- Safety and compliance constraints
- Output format specifications
- Persona and tone requirements
- Data ingestion and variable injection
- Error handling instructions
- Multi-step reasoning chains

Writing all of this into a single monolithic prompt — what the field calls a "mega-prompt" — is almost guaranteed to fail in production. The model will miss constraints buried in the middle. It will apply irrelevant rules to simple queries. It will hallucinate capabilities you never granted it. It will ignore format specifications when the context fills up.

The solution is not to write a better single prompt. The solution is to engineer the informational environment around the model's known architectural characteristics. This is what distinguishes **prompt engineering** (writing clever text) from **context engineering** (architecting the complete informational system the model operates within).

### 1.3 What APOST Solves

APOST — Automated Prompt Optimisation and Structuring Tool — is a practitioner-grade context engineering workstation. Concretely, it solves six problems:

**Problem 1 — You don't know what's missing from your prompt.**
APOST runs a TCRTE gap audit and scores your prompt across five coverage dimensions before generating anything. It tells you exactly what's weak or absent and asks targeted questions to fill those gaps.

**Problem 2 — You don't know which engineering technique to apply.**
APOST's Auto-Select meta-layer analyses your task type, model, and complexity and selects from nine optimisation frameworks (KERNEL, XML Structured, Progressive Disclosure, CoT Ensemble, TextGrad, Reasoning-Aware, TCRTE, CREATE, and Auto). You don't need to know these frameworks to benefit from them.

**Problem 3 — Critical instructions get lost in large contexts.**
APOST automatically applies CoRe (Context Repetition) for multi-hop tasks and RAL-Writer Restate for long-context tasks — both research-validated techniques for injecting critical information into positions the model actually attends to.

**Problem 4 — You're writing the same prompt for different models.**
APOST generates model-specific variants. The same raw intent becomes an XML-tagged Claude prompt, a Markdown-structured GPT prompt, or a system-instruction-separated Gemini prompt — with provider-specific nuances baked in.

**Problem 5 — You can't test three strategic angles at once.**
APOST always produces three variants: Conservative (clarity-first, minimal restructuring), Structured (full framework applied), and Advanced (all guards and auto-enrichments applied). You choose the right one for your context.

**Problem 6 — You lose context between prompt revisions.**
The embedded AI chat assistant holds the full optimisation context — all three variants, all gap interview answers, all TCRTE scores — in a persistent conversation. You iterate in natural language instead of editing raw text repeatedly.

### 1.4 Who Should Use This Tool

| Role | Primary Use Case |
|------|-----------------|
| **AI Engineer / ML Engineer** | Designing production system prompts for LLM-powered APIs |
| **Backend Developer (LLM-adjacent)** | Writing prompts for agent tools, RAG pipelines, routing layers |
| **Prompt Engineer** | Professionalising manual prompt work with structural rigour |
| **GenAI Architect** | Evaluating coverage and technique selection across a prompt portfolio |
| **Product Manager (Technical)** | Understanding why an AI feature behaves unexpectedly |
| **AI Researcher** | Prototyping and stress-testing prompt formulations |

You do not need to have read any of the research papers referenced in this document. APOST encodes the research into its workflow. However, reading this documentation will help you make better decisions about framework selection, task typing, and when to use which output variant.

---

## 2. Theoretical Foundations

This chapter covers the research that underpins every design decision in APOST. Understanding these concepts will help you interpret your coverage scores, choose frameworks intelligently, and explain to your team why certain engineering choices matter.

### 2.1 The Transformer Attention Mechanism

Modern large language models are built on the transformer architecture, whose core mechanism is **self-attention**. At every position in a sequence, the model calculates how much "weight" (attention) to assign to every other position. The output at each position is a weighted combination of all other positions' representations.

In theory, this gives the model access to every token in the context window equally. In practice, this is not what happens. The distribution of attention is shaped by:

- **Positional encodings** that encode proximity
- **Training data statistics** that bias the model toward patterns seen during pre-training
- **Causal masking** (in decoder-only models) that prevents future tokens from attending to past tokens during generation

The result is that attention is not uniformly distributed. Empirical research has consistently shown that certain regions of the context receive systematically higher attention than others, regardless of semantic importance.

### 2.2 The Lost-in-the-Middle Phenomenon

Research published in *Lost in the Middle: How Language Models Use Long Contexts* established a phenomenon that every prompt engineer needs to internalise: **model performance degrades significantly when critical information is positioned in the middle segments of a long input.**

The study showed that even frontier models, when given retrieval tasks with supporting information distributed across a long context, achieved dramatically lower accuracy when the relevant passage was in the middle compared to the beginning or end. The performance gap can exceed 20 percentage points on challenging tasks.

For prompt engineers, this means:

- **A constraint written at line 45 of a 90-line system prompt is statistically likely to be missed.**
- **A formatting rule buried between two large blocks of context data will frequently be ignored.**
- **The model does not read your prompt top to bottom with equal comprehension. It front-loads and back-loads its attention.**

This is not a model defect. It is a structural property of how transformers are trained and how their attention mechanism works at scale. Engineering must account for it explicitly.

### 2.3 Positional Bias and the U-Shaped Attention Curve

The lost-in-the-middle phenomenon creates what researchers describe as a **U-shaped performance curve** across the context window:

```
Attention
Quality
    │
100%│ ██                              ██
    │ ██                              ██
 70%│ ██                              ██
    │ ██   ██                    ██   ██
 40%│ ██   ██  ██            ██  ██   ██
    │ ██   ██  ██  ██    ██  ██  ██   ██
 10%│ ██   ██  ██  ██  ██ ██ ██  ██   ██
    └─────────────────────────────────────
      Start                          End
               Context Position
```

The primacy effect (high attention at the beginning) is driven by the model's need to establish a grounding schema for the document. The recency effect (high attention at the end) is driven by the proximity of the final tokens to the generation boundary.

**Practical implication:** Your most critical constraints, hard rules, and safety guardrails must appear at the beginning of the system prompt — and ideally be echoed at the end. APOST's optimiser enforces this placement strategy automatically for all three variants.

### 2.4 Overshoot and Undershoot: The Two Failure Modes

Every prompt failure in production is a variant of one of two failure modes:

**Overshoot** — The model does more than instructed, or applies instructions beyond their intended scope:
- Hallucinating information not present in the provided context
- Scope creep: expanding the task beyond what was requested
- Applying policies designed for one scenario to an unrelated query
- Generating excessive verbosity when conciseness was required
- Entering infinite reasoning loops in agentic contexts

**Undershoot** — The model does less than instructed, or ignores explicit requirements:
- Omitting required output sections
- Ignoring explicit format constraints
- Missing constraints buried in the middle of a long prompt
- Failing to use specified tools in agentic systems
- Prematurely terminating reasoning before reaching the correct answer

APOST generates explicit **overshoot guards** and **undershoot guards** for every variant. These are concrete prompt instructions — not generic advice — targeting the specific failure modes most likely given your task type and framework.

### 2.5 Cognitive Load and Contextual Interference

As prompts increase in token density, they introduce **noise** that interferes with the model's instruction recognition. This is particularly acute in RAG (Retrieval-Augmented Generation) systems, where retrieved documents that are semantically relevant but task-irrelevant can distract the model from its core instructions.

Research on contextual interference shows that high-quality noise — passages that are well-written and coherent but not task-relevant — can degrade reasoning accuracy by more than simple factual errors would. The model's attention mechanism cannot distinguish between "relevant document" and "distracting relevant-seeming document" without structural help.

This is why APOST enforces **structural separation** between system instructions and injected data. The XML Structured framework wraps instructions and data in different tag namespaces, and the Progressive Disclosure framework loads data only when a specific skill is activated — never injecting it into the base context unnecessarily.

### 2.6 Instruction Coverage as a Measurable Metric

In 2025, the field formalised the concept of **instruction coverage** — borrowed directly from software engineering's code coverage metrics. Just as code coverage measures the percentage of code paths exercised by tests, instruction coverage measures the percentage of explicit constraints in a prompt that the model actually satisfies in output.

The IFEval and IFEval-Extended benchmarks quantify this with two metrics:

- **Strict Accuracy:** Binary measure — did the model satisfy *every* constraint perfectly?
- **Loose Accuracy:** Did the model satisfy the intent of constraints, allowing for minor formatting variations?

APOST's TCRTE scoring system is designed as a *pre-generation* proxy for instruction coverage. A prompt that scores 80% on TCRTE coverage is predicted to achieve higher strict accuracy than one that scores 40%, because it has explicitly addressed the five dimensions that research shows are most commonly left underspecified.

---

## 3. The TCRTE Framework — Coverage-Driven Prompt Design

### 3.1 What TCRTE Is and Where It Comes From

TCRTE (Task · Context · Role · Tone · Execution) emerged from research on instruction adherence in 2024–2025. It is a five-pillar decomposition framework for ensuring that every structurally important component of a prompt is explicitly addressed before the model is asked to generate output.

TCRTE is related to earlier frameworks like CLEAR (Goal, List, Unpack, Examine) and CREATE (Context, Role, Instruction, Steps, Execution), but distinguishes itself by treating **Tone** and **Execution** as separate first-class citizens — a recognition that stylistic requirements and output format constraints are among the most commonly underspecified dimensions, and among the most likely to cause production failures.

Think of TCRTE as the **unit test suite for prompt structure**. If all five dimensions pass, your prompt has structural coverage. If any dimension fails, you have a predictable failure surface.

### 3.2 The Five Dimensions Explained

#### Task — The Core Objective (T)

**Definition:** The specific action or objective the model must execute.

**What good looks like:** "Extract all named entities from the provided document and classify each as PERSON, ORGANISATION, LOCATION, or DATE. Return a JSON array."

**What weak looks like:** "Analyse this document." (No specific action, no deliverable defined.)

**What missing looks like:** Providing context and a role but never stating what the model should actually do.

**Failure mode when absent:** The model will infer a task from surrounding context. Its inferred task may be sensible but rarely matches the exact intent. In production, this manifests as subtly wrong outputs that are hard to catch in automated testing.

#### Context — Background and Grounding (C)

**Definition:** Domain knowledge, background facts, reference data, or historical inputs the model needs to reason accurately.

**What good looks like:** "The following documents are SEC 10-K filings from Q3 2024. The company operates in the semiconductor sector. Regulatory context is the US SEC reporting framework."

**What weak looks like:** Injecting raw documents without framing their source, date, or domain.

**What missing looks like:** Asking the model to analyse, classify, or reason about data without providing any grounding for *what kind of data* it is.

**Failure mode when absent:** Hallucination. The model fills grounding gaps with its training priors, which may be outdated, domain-incorrect, or simply fabricated. This is the primary cause of factual errors in RAG pipelines.

#### Role — Model Persona and Expertise (R)

**Definition:** The persona, professional perspective, and expertise level the model should adopt.

**What good looks like:** "You are a senior compliance analyst with 15 years of experience in SEC regulatory reporting. You prioritise precision over completeness and flag uncertainty explicitly."

**What weak looks like:** "You are an AI assistant." (No domain, no expertise level, no behavioural calibration.)

**What missing looks like:** Providing a task and context with no role specification at all.

**Failure mode when absent:** The model defaults to a generic helpful-assistant persona. It will use lay vocabulary in technical contexts, hedging language in contexts requiring authority, and a neutral register in contexts requiring specific tone. The response is generically correct but professionally inadequate.

#### Tone — Style and Communication Register (T)

**Definition:** The stylistic requirements, emotional register, formality level, and audience alignment of the output.

**What good looks like:** "Write in formal, declarative English. Avoid hedging language (do not use 'might', 'could', 'possibly'). Assume the reader is a non-technical executive who requires conclusions, not methodology."

**What weak looks like:** "Be professional." (Undefined; different models interpret 'professional' differently.)

**What missing looks like:** Specifying what to write but not how to write it.

**Failure mode when absent:** Tone misalignment. The model produces correct content in the wrong voice. A legal summary sounds like a blog post. A customer-facing message sounds like an internal memo. In customer-facing applications, this directly impacts user trust and brand perception.

#### Execution — Format, Length, and Constraints (E)

**Definition:** Strict specifications for output format, length limits, structure, prohibited content, and verifiable success criteria.

**What good looks like:** "Output a JSON object with keys: `entities` (array), `summary` (string, max 150 words), `risk_flags` (array of strings). Do not include any preamble or postamble. Return only the JSON object."

**What weak looks like:** "Return a structured response." (Structure not defined.)

**What missing looks like:** Comprehensive task, context, role, and tone specification, but no output format definition.

**Failure mode when absent:** Inconsistent output structure. Even if the model produces correct content, downstream systems that parse the output will fail unpredictably. This is the most common cause of production pipeline failures in LLM-integrated systems.

### 3.3 TCRTE Scoring Methodology

APOST's gap analysis engine scores each TCRTE dimension on a 0–100 scale with three status classifications:

| Score Range | Status | Visual Indicator | Action Required |
|-------------|--------|-----------------|----------------|
| 70–100 | **GOOD** | Green bar | None — dimension adequately covered |
| 35–69 | **WEAK** | Amber bar | A clarifying question is generated |
| 0–34 | **MISSING** | Red bar | A critical question is generated |

The **Overall Score** is a weighted average of the five dimensions. Execution and Task receive higher weights because they are the dimensions most directly correlated with production reliability and testability.

A prompt with an overall score below 50 before optimisation and above 80 after gap interview responses is a typical improvement trajectory.

### 3.4 TCRTE vs. Other Frameworks: When to Use Which

TCRTE is primarily a **coverage audit framework** — it ensures all dimensions are present. The other frameworks in APOST (KERNEL, XML Structured, CoT Ensemble, etc.) are **structural assembly frameworks** — they determine how the covered dimensions are organised and delivered to the model.

In practice, TCRTE gap analysis runs first (answering *what's missing*), and then the structural framework is applied (answering *how to organise what's there*). They are complementary, not competing.

---

## 4. Optimisation Frameworks Implemented in APOST

### 4.1 KERNEL — The Minimalist Discipline

KERNEL is an acronym encoding six principles for prompt clarity. It is most appropriate for simple-to-medium complexity tasks where precision and conciseness are more valuable than structural depth.

| Letter | Principle | Engineering Implication |
|--------|-----------|------------------------|
| **K** | Keep it Simple | One clear objective per prompt. Any prompt that encodes two goals should be split into two prompts. |
| **E** | Explicit Constraints | State what the model must NOT do with equal specificity to what it must do. Negative constraints are as important as positive ones. |
| **R** | Narrow Scope | One job at a time. If the task requires summarisation AND classification, use two sequential prompts, not one. |
| **N** | Known Success Criteria | Define what a correct output looks like before writing the prompt. If you cannot define success, you cannot test the prompt. |
| **E** | Enforce Format | The output format is a contract. Specify it with a rigid schema or template that leaves no ambiguity. |
| **L** | Logical Structure | Always follow: Context → Task → Constraints → Format. Never place the task before the context. |

KERNEL is the first framework to reach for when a prompt feels "bloated" but you're not sure why. It enforces a discipline of removal over addition.

### 4.2 XML Structured Bounding — Anthropic's Semantic Hierarchy

XML Structured Bounding is the recommended framework for Claude models and is Anthropic's officially documented best practice for complex prompts.

**The core idea:** Transformer models were pre-trained on massive corpora of web documents and code, both of which make extensive use of XML and HTML-like tag syntax. This pre-training creates a strong prior that content within `<tag>` delimiters is semantically self-contained. By wrapping distinct prompt components in named tags, you exploit this prior to create hard semantic boundaries that the model cannot easily blur.

**Tag hierarchy used in APOST:**
```xml
<system_directives>
  <task>The specific action to execute</task>
  <constraints>
    <rule>Constraint 1 — stated positively and negatively</rule>
    <rule>Constraint 2 — with verifiable success criterion</rule>
  </constraints>
  <output_format>Rigid schema specification</output_format>
</system_directives>

<dynamic_context>
  <documents>
    <document index="1">
      <source>Source description</source>
      <content>{{document_1}}</content>
    </document>
  </documents>
  <input_variables>
    <variable name="threshold">{{threshold}}</variable>
  </input_variables>
</dynamic_context>
```

**Why this prevents context contamination:** When a user injects adversarial content (prompt injection attacks) or when retrieved documents contain instruction-like text, XML tags provide a clear delineation between "system commands" and "user data". The model has been trained to respect this distinction. Content inside `<dynamic_context>` is treated as data to reason about, not instructions to follow.

**Placement strategy:** Constraints always appear at the TOP of `<system_directives>`, exploiting the primacy effect. Critical constraints are echoed at the bottom of the block, exploiting the recency effect. Nothing critical appears only in the middle.

### 4.3 Progressive Disclosure — The Agent Skills Architecture

Progressive Disclosure addresses the **mega-prompt problem** directly. Instead of injecting all operational knowledge into a single system prompt, the Agent Skills architecture loads information in escalating layers of detail based on what the current task actually requires.

**The three layers:**

**Layer 1 — Discovery (Metadata):** The agent's base system prompt contains only a lightweight index of available capabilities. Each skill is represented by its name, a one-sentence description, and trigger conditions. This layer consumes approximately 100 tokens per capability.

```
Available Skills:
- financial_risk_analysis: Triggered when request involves risk assessment of financial documents
- compliance_checker: Triggered when request involves regulatory or policy verification
- data_extractor: Triggered when request involves structured data extraction from unstructured text
```

**Layer 2 — Activation (Instruction Injection):** When the agent's reasoning determines a skill is needed, the detailed SKILL.md file for that skill is loaded into context. This file contains precise operational logic, safety constraints, and output format specifications — but only for the activated skill.

**Layer 3 — Execution (Reference + Scripts):** Once a skill is active, deterministic execution scripts (Python, Bash) handle calculations and formatting tasks. This offloads to code what code does better than language models, preserving the model's context for reasoning.

**Why this matters at scale:** A 50,000-token mega-prompt with 200 operational procedures means every procedure competes for attention with every other procedure on every request. A Progressive Disclosure architecture means each request activates only the relevant 300-token skill, giving it maximum attention weight.

### 4.4 CoT Ensemble — The Medprompt Pattern

Chain-of-Thought Ensemble, based on Microsoft's Medprompt research, combines three techniques to maximise accuracy on high-stakes, high-ambiguity tasks:

**Technique 1 — Dynamic kNN Few-Shot Selection:** Instead of static few-shot examples, the system retrieves examples most semantically similar to the current input. This ensures that the model's reasoning is calibrated to the actual structure of the current problem, not a generic one.

**Technique 2 — Auto-generated Chain-of-Thought:** For each few-shot example, a full reasoning trace is included — not just the answer. The model learns the reasoning pattern, not just the answer pattern.

**Technique 3 — Multi-Path Reasoning + Ensemble:** The model is instructed to generate multiple independent reasoning paths before committing to a final answer, then synthesise across paths. This is mathematically equivalent to an ensemble of classifiers and significantly reduces the probability of hallucinated conclusions.

In the Medprompt benchmarks, this strategy enabled GPT-4 to match the accuracy of domain-specific models on medical challenge questions, improving base accuracy by 7.1%.

**When to use CoT Ensemble in APOST:** Select this for tasks where being wrong has high consequences — medical, legal, financial, or safety-critical domains — and where the task involves complex multi-step reasoning that benefits from explicit intermediate steps.

### 4.5 TextGrad — Textual Backpropagation

TextGrad adapts the mathematical concept of backpropagation from neural network training to prompt optimisation. In standard deep learning, backpropagation computes numerical gradients to indicate how model weights should change to reduce a loss. TextGrad replaces numerical gradients with **textual critiques** generated by an evaluator model.

**The TextGrad loop:**

```
Forward Pass:  System Prompt + Input → Model Output
               
Loss Function: Evaluator Model assesses output against success criteria
               → Generates "textual loss": "The constraint on output format 
                  was violated because..."

Gradient:      Gradient LLM localises the failure to specific prompt nodes
               → "The <constraints> block lacks an explicit prohibition on..."

Update:        Optimiser LLM rewrites the failing prompt node
               → Constraint is strengthened, repositioned, or rephrased
               
Next Pass:     Updated System Prompt + Input → Improved Model Output
```

In APOST, TextGrad-style constraint hardening is applied during variant generation. The optimiser:

1. Enumerates likely overshoot and undershoot failure modes for your specific task type
2. For each failure mode, generates an explicit counter-constraint
3. Places ANTI-HALLUCINATION guards: "Only use information explicitly provided in `<context>`. Do not infer from training knowledge."
4. Places COMPLETION guards: "Do not terminate output until all required sections are populated."
5. Locks output with a rigid schema template

### 4.6 Reasoning-Aware Mode — For o-series and Extended Thinking

This framework addresses a critical and counterintuitive finding from research on inference-optimised models (OpenAI o1, o3, o4-mini; Google Gemini Flash Thinking; Anthropic Claude with Extended Thinking).

**The counterintuitive finding:** Adding chain-of-thought instructions ("think step by step", "reason through this carefully", "first, consider each possibility") to reasoning models does *not* improve performance. It *degrades* it. These models were trained with reinforcement learning to generate their own internal reasoning traces. External CoT instructions interfere with the model's native reasoning policies, forcing it to produce redundant, shallow "thinking tokens" that increase latency and degrade output quality.

**What reasoning models need instead:**

- Absolute structural clarity in the system prompt
- Hard constraints and format requirements declared upfront
- Data clearly separated from instructions with delimiters
- No reasoning guidance whatsoever — the model determines its own path

APOST automatically detects reasoning models from the provider/model configuration and applies Reasoning-Aware mode, suppressing all CoT-forcing language in every generated variant.

**A rule of thumb:** If you're using a model with "Reasoning", "Thinking", "o1", "o3", or "R1" in its name, treat it as a reasoning model and let APOST configure the prompt accordingly.

### 4.7 CREATE — Sequential Instruction Architecture

CREATE (Context · Role · Instruction · Steps · Execution) is a sequential framework that emphasises *ordering* of prompt components as its primary mechanism.

The key insight: **Steps must precede Execution.** By forcing the model to see the reasoning path it should take *before* it sees the output format it must conform to, CREATE prevents the model from committing to a shallow answer before fully engaging with the reasoning process.

```
[Context]     Background and domain grounding
[Role]        Persona and expertise calibration  
[Instruction] The specific task
[Steps]       The reasoning path to follow (without prescribing conclusions)
[Execution]   The exact format and schema the output must conform to
```

This is particularly effective for analytical tasks where users want to see that the model's conclusion emerged from a demonstrated reasoning process, not a pattern-matched shortcut.

### 4.8 Auto-Select — The Meta-Decision Layer

Auto-Select is not a framework itself; it is a meta-decision system that chooses among the eight frameworks based on your inputs. The selection logic:

| Condition | Selected Framework |
|-----------|------------------|
| Reasoning model (any provider) | Reasoning-Aware |
| Multi-document, complex RAG task | XML Structured |
| Agentic system with multiple tools | Progressive Disclosure |
| High-stakes domain (medical, legal, finance) | CoT Ensemble |
| TCRTE score < 50, missing critical dimensions | TCRTE |
| Simple task, clarity issues | KERNEL |
| Sequential analysis with visible reasoning | CREATE |
| Complex constraints, known failure modes | TextGrad |

When in doubt as a new user, leave the framework on Auto-Select. As you gain experience with the output variants, you will develop intuition for which framework fits your domain best.

---

## 5. Advanced Injection Techniques

These three techniques are automatically applied by APOST when the gap analysis determines they are warranted. Understanding them helps you interpret the Advanced variant and decide when to request them explicitly via chat.

### 5.1 CoRe — Context Repetition for Multi-Hop Reasoning

**Problem it solves:** Multi-hop reasoning tasks require the model to connect information across multiple steps. Research has shown that misordered or poorly positioned context in multi-hop tasks can degrade accuracy by up to 26%.

**Mechanism:** CoRe repeats the most critical context segment at strategically chosen positions in the prompt, where k (number of repetitions) corresponds to the number of reasoning hops required. This ensures that at some point in the sequence, the necessary information appears at an optimal relative position to the current generation boundary.

**Example — before CoRe:**
```
User: Given the following documents, determine whether the merger 
      violates antitrust regulations, considering both Section 7 and 
      the Herfindahl-Hirschman Index thresholds.
      
[Document 1 — 2,000 tokens]
[Document 2 — 3,000 tokens] 
[Document 3 — 1,500 tokens]
```

**After CoRe (applied by APOST Advanced variant):**
```
[CRITICAL CONTEXT — STEP 1 GROUNDING]
Regulatory framework: Section 7 Clayton Act; HHI threshold: >2,500 = 
highly concentrated; >200 point increase = presumptive violation.

[Document 1 — 2,000 tokens]
[Document 2 — 3,000 tokens]

[CRITICAL CONTEXT RESTATE — STEP 2 GROUNDING]  
Regulatory framework: Section 7 Clayton Act; HHI threshold: >2,500 = 
highly concentrated; >200 point increase = presumptive violation.

[Document 3 — 1,500 tokens]
```

The critical regulatory criteria are repeated before the model enters each major reasoning hop, ensuring they are always within the recency effect's range.

### 5.2 RAL-Writer Restate — Beating the Attention Blind Spot

**Problem it solves:** When system instructions are long, constraints written in the middle of the system prompt fall into the attention blind spot. RAL-Writer (Retrieval-Augmented Long-Text Writer) addresses this with a "Retrieve-and-Restate" mechanism.

**Mechanism:** APOST's optimiser identifies instructions that are structurally forced into middle positions (because earlier positions are taken by role/context blocks that must come first). These identified instructions are then appended at the end of the system prompt in a `<restate_critical>` block.

**Example:** A 60-line system prompt has critical output format constraints at lines 25–30. After RAL-Writer Restate, those constraints are also echoed as the very last block before the user turn — placing them in the recency effect zone.

```xml
<system_directives>
  <role>...</role>              <!-- Lines 1-10: Primacy zone -->
  <context>...</context>       <!-- Lines 11-20 -->
  <constraints>                <!-- Lines 21-35: DANGER ZONE -->
    <rule>Output must be JSON only</rule>
    <rule>Do not exceed 500 tokens</rule>
  </constraints>
  <examples>...</examples>     <!-- Lines 36-55 -->
</system_directives>

<restate_critical>             <!-- Lines 56-60: Recency zone -->
  REMINDER: Output must be JSON only. Do not exceed 500 tokens.
  Violating either constraint renders the output invalid.
</restate_critical>
```

### 5.3 Claude Prefill — Locking Output Format at the Token Level

**Problem it solves:** Even with explicit format instructions, Claude models sometimes begin their response with a conversational preamble ("Sure! Here is the analysis you requested...") before producing the actual output. This preamble breaks downstream parsers and signals format drift.

**Mechanism:** Anthropic's API allows the caller to provide the first few tokens of the assistant's response before generation begins. This is called **prefilling**. The model cannot contradict its own already-stated output — so if you prefill with `{`, the model's first generated token will be the second character of a JSON object, not a conversational opener.

**APOST generates prefill suggestions for the Advanced variant when targeting Claude.** These are ready-to-copy strings for use in the `assistant` turn of the API call:

| Task Type | Prefill Suggestion | Effect |
|-----------|-------------------|--------|
| JSON output | `{` | Forces JSON mode without `json_mode: true` |
| XML output | `<analysis>` | Locks into XML structure immediately |
| Markdown report | `## ` | Forces structured Markdown, skips preamble |
| Structured list | `1.` | Forces numbered list from first token |
| Thinking + output | `<thinking>` | Opens a reasoning trace before the answer |

**How to use it in the API:**
```python
response = anthropic.messages.create(
    model="claude-sonnet-4-6",
    messages=[
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": "{"}  # ← The prefill suggestion from APOST
    ]
)
# Response continues from "{" — guaranteed JSON structure
```

---

## 6. Provider-Specific Engineering

### 6.1 Anthropic Claude — XML-First Architecture

Claude models (Opus, Sonnet, Haiku series) were trained with a particularly strong prior for XML-structured input. Anthropic explicitly documents that Claude performs better with XML semantic tags than with Markdown or free-form text for complex prompts.

**APOST applies these Claude-specific rules:**

1. **XML tags over everything else** — Every semantic zone gets a dedicated tag
2. **Primacy placement of constraints** — Hard rules go in the first 20% of the system prompt
3. **Recency echo** — Critical constraints are repeated in a `<restate_critical>` block at the end
4. **Role → Task → Context → Constraints → Format → Variables** — This ordering is non-negotiable for Claude
5. **Nested document arrays** — Multi-document inputs use `<documents><document index="N">` hierarchy
6. **Prefill suggestions** — Advanced variant includes a prefill string for format locking
7. **Variable isolation** — All injected variables are wrapped in `<input_variables>` to prevent prompt injection

### 6.2 OpenAI GPT and o-series — Markdown and Reasoning Separation

**Standard GPT models (GPT-4o, GPT-4.1):**
- Markdown-first: `###` headers, `**bold**`, bullet lists outperform XML for GPT
- System prompt: Role definition + overarching rules only
- User turn: Task specification + injected data
- Triple-backtick fences for code and structured data injection
- JSON Schema definitions for structured output requirements

**Reasoning models (o3, o4-mini):**
- System prompt must be extremely concise — reasoning models perform worse with verbose system prompts
- Zero chain-of-thought instruction — the model reasons internally
- Focus entirely on: what the output must contain, what format it must take, what it must NOT do
- No examples if they add length without semantic value — reasoning models generalise from principles
- Delimiters (` --- ` or ` ``` `) for data separation, not for structure

### 6.3 Google Gemini — Structured Data and System Instruction Separation

Gemini's architecture uses **System Instructions** as a persistent framework that persists across conversation turns. This is architecturally distinct from the single system prompt model used by Anthropic and OpenAI.

**APOST applies these Gemini-specific rules:**

1. **System Instructions** contain: role, persistent constraints, safety rules, and format requirements
2. **User turn** contains: task, data, and variable injections
3. **Gemini handles JSON, XML, and Markdown well** — APOST defaults to XML tags for complex tasks
4. **Decomposition is preferred over combination** — if a task involves summarisation + classification + translation, APOST signals this in the model notes as a candidate for prompt chaining
5. **Rich examples** — Gemini's large context window is an advantage; APOST includes more few-shot examples for Gemini than for other providers

### 6.4 Reasoning Model Treatment Across All Providers

All reasoning models — regardless of provider — share common engineering requirements that APOST enforces:

| Requirement | Why |
|-------------|-----|
| No explicit CoT instructions | Interferes with native RL-trained reasoning policies |
| Concise system prompt | Reasoning models allocate more internal compute; verbose prompts waste it |
| Hard constraints stated upfront | Reasoning models need boundary conditions, not reasoning guidance |
| Format requirements at the start | Output contracts must be established before internal reasoning begins |
| No "think step by step" | This phrase specifically degrades reasoning model performance |

The APOST UI displays an amber warning badge when a reasoning model is selected, and all seven optimisation frameworks automatically suppress CoT-forcing language in their output for these models.

---

## 7. APOST v4 Architecture — System Design Deep Dive

### 7.1 The Four-Phase State Machine

APOST v4's core workflow is implemented as a deterministic four-phase state machine. Understanding this state machine helps you predict how the tool will behave and how to navigate it efficiently.

```
┌─────────────────────────────────────────────────────────────────┐
│                    APOST v4 State Machine                        │
├──────────┬──────────────┬────────────────┬─────────────────────┤
│  IDLE    │  ANALYZING   │  INTERVIEW     │  OPTIMIZING/RESULTS │
│          │              │                │                     │
│ User     │ Gap analysis │ TCRTE coverage │ Three variants      │
│ inputs   │ API call in  │ meter shown.   │ generated. Chat     │
│ ready.   │ progress.    │ Questions      │ seeded with full    │
│ Action:  │ Spinner.     │ rendered.      │ output context.     │
│ Analyse  │ ~2-3 sec     │ User answers.  │ Results read-only.  │
│ Gaps or  │              │ Action:        │ Action: Refine in   │
│ Skip.    │              │ Optimise or    │ chat or Reset.      │
│          │              │ Skip Answers.  │                     │
└──────────┴──────────────┴────────────────┴─────────────────────┘
```

**State transitions:**
- `IDLE → ANALYZING`: User clicks "Analyse Gaps First"
- `ANALYZING → INTERVIEW`: Gap analysis API call returns successfully
- `ANALYZING → IDLE`: Gap analysis fails (error displayed)
- `INTERVIEW → OPTIMIZING`: User clicks "Optimise with Context"
- `INTERVIEW → OPTIMIZING`: User clicks "Skip Answers" (answers={})
- `OPTIMIZING → RESULTS`: Optimisation API call returns successfully
- `OPTIMIZING → INTERVIEW`: Optimisation fails (returns to interview with error)
- `RESULTS → IDLE`: User clicks "Reset" (all state cleared)
- `RESULTS → OPTIMIZING`: User clicks "Re-Optimise"

**Raw prompt change resets state:** If the user edits the raw prompt while in INTERVIEW or RESULTS state, the tool resets to IDLE. This prevents stale gap analysis from being applied to a different prompt.

### 7.2 Phase 1 — Gap Analysis Engine

The gap analysis is powered by a dedicated meta-prompt (`buildGapAnalysisPrompt`) sent to Claude Sonnet 4.0 (the internal optimiser model, distinct from the target model).

**What the gap analysis prompt sends:**
- The raw prompt verbatim
- Declared input variables
- Target provider, model, and reasoning classification
- Task type
- Instruction to return structured JSON with TCRTE scores, questions, complexity assessment, and recommended techniques

**What it returns (structured JSON):**
```json
{
  "tcrte": {
    "task":      {"score": 72, "status": "good",    "note": "Objective is clear and measurable"},
    "context":   {"score": 30, "status": "missing",  "note": "No domain or source specification"},
    "role":      {"score": 45, "status": "weak",     "note": "Persona exists but lacks expertise calibration"},
    "tone":      {"score": 20, "status": "missing",  "note": "No audience or register specified"},
    "execution": {"score": 60, "status": "weak",     "note": "Format described but schema not enforced"}
  },
  "overall_score": 45,
  "complexity": "complex",
  "complexity_reason": "Multi-document analysis with regulatory cross-referencing",
  "recommended_techniques": ["CoRe", "RAL-Writer", "XML-Bounding"],
  "questions": [...],
  "auto_enrichments": [...]
}
```

**Token cost of the gap analysis:** Approximately 800–1,200 tokens total (input + output). This is a deliberate design choice — the gap analysis is intentionally lightweight so that the cost of using the full workflow (gap → interview → optimise) is not significantly higher than going directly to optimisation.

### 7.3 Phase 2 — The Interview Layer

The interview phase renders the gap analysis results as an interactive UI:

**Coverage Meter:** A visual representation of all five TCRTE dimensions with animated progress bars, status badges, and per-dimension notes. The overall score is displayed prominently.

**Complexity Badge:** Simple / Medium / Complex classification with a one-sentence rationale. This primes the user to understand why certain techniques (CoRe for complex, KERNEL for simple) will be applied.

**Recommended Techniques Badges:** The gap analysis engine identifies which advanced injection techniques are warranted. These appear as teal badges before the questions section.

**Auto-Enrichments Block:** Some improvements the tool applies automatically — without requiring user input — are listed here. For example: "Strategic placement of constraints in primacy and recency zones" is an auto-enrichment that applies to every optimisation.

**Question Cards:** Each question is rendered as a card with:
- A TCRTE dimension badge (colour-coded to the dimension)
- An importance badge (CRITICAL / RECOMMENDED / OPTIONAL)
- The question text in natural language
- An input field with a placeholder example answer

Users do not need to know anything about TCRTE to answer these questions. They are phrased as natural questions a technical colleague might ask: "What domain or industry does this document come from?", "Who is the intended reader of the output?", "Should the model only use information from the provided documents, or can it draw on general knowledge?"

### 7.4 Phase 3 — The Optimisation Engine

The optimisation call (`buildOptimizerPrompt`) assembles a comprehensive meta-prompt from:

1. **Target configuration block** — Provider, model, reasoning classification, task type, complexity, framework
2. **Model-specific guidelines** — Provider-specific engineering rules baked into the prompt
3. **Framework guidelines** — The full specification of the selected framework
4. **Technique injection blocks** — CoRe and RAL-Writer instructions if flagged by gap analysis
5. **Raw prompt** — The verbatim user input
6. **Input variables** — Declared variable names and descriptions
7. **Gap interview answers** — Each question-answer pair, clearly labelled
8. **Output schema** — Rigid JSON schema the model must conform to

The optimiser is instructed to produce three strategic variants simultaneously in a single API call, which is more token-efficient than three separate calls and ensures the variants are coherent relative to each other.

**Token budget:** The optimisation call uses `max_tokens: 4096`. This is sufficient for three full variants with guards for most task types. Very complex tasks with large output format specifications may approach this limit; the chat refinement layer can then expand specific variants.

### 7.5 Phase 4 — Results and the Three-Variant Strategy

The three-variant strategy exists because **the right level of structural rigour depends on context that the tool cannot know:**

**Variant 1 — Conservative**
*Philosophy:* Clarity over structure. Minimal added tokens. Maximum readability for a developer reviewing the prompt.
*When to use:* Simple tasks, low-stakes applications, teams new to structured prompting, or when you want to understand what the model can do with minimal steering.

**Variant 2 — Structured**
*Philosophy:* Full framework application. Every TCRTE dimension explicitly addressed. Structural delimiters applied. Format locked.
*When to use:* Production deployments, any task where output consistency is required, teams comfortable with structured prompts.

**Variant 3 — Advanced**
*Philosophy:* Maximum guards, all auto-enrichments applied, CoRe/RAL-Writer/Prefill injected where warranted, anti-failure constraints for every identified failure mode.
*When to use:* High-stakes production, regulated domains, agentic systems, multi-document tasks, or any case where a failure in the field has significant consequences.

**TCRTE scores per variant:** Each variant includes a TCRTE mini-bar display showing how much each optimisation layer improved coverage on each dimension. Variant 3 should consistently score 80%+ across all dimensions.

### 7.6 The Conversational Refinement Layer

The chat panel is architecturally a context-aware RAG system for prompt refinement. Its system prompt (`buildChatSystem`) includes:

- The complete session context (raw prompt, variables, provider, model, task, framework, complexity, techniques applied)
- The gap analysis TCRTE scores and dimension status
- All gap interview questions and answers
- The full text of all three generated variants (system prompt + user prompt + prefill)

This means the assistant can answer questions like:
- "Why does Variant 2 use XML but not Variant 1?" — It can reference the framework application
- "Tighten the output format constraint on Variant 3" — It has the full text to revise
- "The role dimension in V1 scored 45 — what would push it to 80?" — It has the TCRTE scores and the gap notes

**Conversation history management:** The chat maintains a rolling 28-message history (the `slice(-28)` call). Older messages are dropped from the API call but remain visible in the UI. This prevents context window exhaustion on long refinement sessions while keeping the most recent exchanges (where the most specific refinements happen) always accessible.

### 7.7 Context Seeding — Why the Chat Knows Everything

The most important architectural decision in the chat design is **context seeding**. When optimisation completes, APOST does not simply say "done, go ask the assistant." It posts a complete, structured first message from the assistant that includes:

- The framework decision and why it was made
- The coverage delta (e.g., "Coverage improved from 38% → 91%")
- All techniques applied
- The top three issues fixed
- The complete system and user prompts for all three variants, in labelled code blocks
- TCRTE scores for each variant

This seed message serves two purposes. First, it gives the user an immediate, readable summary of what was generated — they do not need to read the output cards to know what happened. Second, and more importantly, it places the full prompt content into the chat history. All subsequent assistant responses can reference, quote, and modify the seeded content because it is part of the conversation thread.

The result is that the chat feels like you are talking to a colleague who was in the room when the prompts were generated — because they were.

---

## 8. The Three-Column UI — Architectural Rationale

The three-column layout is not an aesthetic choice. It reflects a deliberate information architecture designed around the three distinct cognitive modes of prompt engineering work.

### 8.1 Left Panel — Stable Configuration

**Content:** Raw prompt input, input variable declarations, provider selection, model selection, API key, endpoint override.

**Design philosophy:** The left panel contains information that is **stable across a single prompt engineering session**. You write your prompt once, select your model once, and enter your API key once. These inputs do not change as you iterate through the workflow. By isolating them in a dedicated panel, the tool prevents the visual noise of a changing workflow state from distracting from the inputs.

**The API key placement:** A deliberate decision was made to place the API key inside the model configuration section rather than in a separate "Authentication" section. The reasoning: the API key is a property of the provider, not the tool. Different providers require different keys with different formats. Placing the key adjacent to the provider selection makes this relationship explicit and prevents users from entering an OpenAI key when an Anthropic provider is selected.

### 8.2 Middle Panel — Workflow Execution

**Content:** Task type, framework selection, phase-specific controls, phase-specific output (coverage meter → interview questions → results).

**Design philosophy:** The middle panel is the **workflow execution space**. Its content changes based on the current phase. This is where the tool's intelligence is expressed — the gap audit results, the interview questions, the optimisation output.

The task type and framework selectors live at the top of this panel in a fixed controls strip because they inform every phase of the workflow. Selecting a different framework after gap analysis but before optimisation is valid and common — the gap analysis tells you what's missing, and then you choose the best structural framework to address those gaps.

The output area is deliberately **read-only**. Optimised prompts are engineering outputs, not drafts. They should be copied and used, or refined through the chat — not edited in place. This nudges the user toward the architectural workflow (configure → generate → refine via chat) rather than the ad-hoc workflow (write → tweak → write more).

### 8.3 Right Panel — Conversational Intelligence

**Content:** AI chat assistant with full optimisation context, quick action chips, persistent conversation history.

**Design philosophy:** The right panel provides **conversational access to the optimisation engine**. It exists because the three-variant output covers the most common structural decisions, but production prompts always require domain-specific refinements that a general optimiser cannot anticipate.

The panel is collapsible to a 46px icon strip. This acknowledges that for users in "batch mode" (optimising many prompts quickly), the chat is secondary. For users in "refinement mode" (iterating on a single complex prompt), the chat becomes the primary workspace.

The **quick action chips** are positioned above the input field, not below it. This placement is intentional: they are the most likely next action after seeing the results, and positioning them at the top of the input area (before the text box) keeps them in the user's visual flow without requiring a scroll.

---

## 9. User Guide — Step-by-Step Workflows

### 9.1 Quickstart — Your First Optimisation in 5 Minutes

**Prerequisites:** An API key for any supported provider (Anthropic, OpenAI, or Google).

**Step 1 — Enter your raw prompt**
Type or paste your prompt into the "Raw Prompt" textarea in the left panel. It can be as rough as a sentence or two. The tool is designed to handle incomplete prompts.

**Step 2 — Declare input variables (optional but recommended)**
If your prompt references dynamic data (documents, user inputs, thresholds), list them in the "Input Variables" field:
```
{{documents}} – array of PDF text strings
{{user_query}} – the end-user's question
{{risk_threshold}} – numeric percentage
```

**Step 3 — Select provider and model**
Choose your target LLM provider. Select the specific model. Enter the API key for that provider. The key is used only for this session and is not stored anywhere.

**Step 4 — Select task type**
Pick the closest match from the task type chips. If your task spans multiple types (e.g., reasoning + coding), pick the primary one.

**Step 5 — Choose a framework**
Leave on **Auto-Select** for your first run. Once you see the output and the framework explanation, you will develop intuition for when to override it.

**Step 6 — Click "Skip → Optimise"**
For a quick first run, skip the gap interview. Three variants will be generated in 10–20 seconds.

**Step 7 — Read the results**
Review Variant 2 (Structured) first — it is usually the best balance of completeness and usability. Check the Guards tab to understand what failure modes are protected against. Use the Meta tab to understand when each variant is appropriate.

**Step 8 — Copy and test**
Copy the system prompt and user prompt from Variant 2. Test it with your target model. Return to the chat to refine.

### 9.2 Full Workflow — With Gap Interview

This is the recommended workflow for any production prompt.

**Step 1–3:** Same as Quickstart.

**Step 4 — Click "Analyse Gaps First"**
The tool will run a TCRTE audit in 2–3 seconds. The coverage meter appears in the middle panel.

**Step 5 — Read the coverage report**
Review each dimension. Note which dimensions are RED (missing) and AMBER (weak). Read the one-line note under each bar explaining what specifically is missing.

**Step 6 — Answer the questions**
Work through each question card. You do not need to write perfect answers — rough notes are sufficient. The optimiser will structure them correctly. Prioritise CRITICAL questions (red badge) over RECOMMENDED (amber) and OPTIONAL (grey).

**Step 7 — Click "Optimise with Context"**
The optimiser now has your gap answers plus the TCRTE analysis. The resulting prompts will be significantly more complete than a Skip → Optimise run.

**Step 8 — Compare the coverage delta**
The results banner shows the coverage improvement (e.g., "Coverage improved from 42% → 87%"). Check the TCRTE mini-bars on each variant to confirm that previously weak dimensions are now scoring well.

### 9.3 Reading Your Coverage Report

The coverage report has four sections:

**Coverage Meter (top):** Overall score 0–100, plus per-dimension bars. Focus on the dimensions scoring below 35 first — these represent the highest risk of production failure.

**Complexity + Techniques (below meter):** The complexity badge tells you how much engineering sophistication your task requires. The technique badges tell you which injection techniques will be auto-applied. If you see "CoRe" and your task doesn't involve multi-hop reasoning, you may want to override by selecting a simpler framework.

**Auto-Enrichments (teal block):** These are applied unconditionally regardless of your answers. They include primacy/recency placement, structural delimiters, and failure-mode guards.

**Question Cards (bottom):** Address in importance order: CRITICAL → RECOMMENDED → OPTIONAL. Skipping OPTIONAL questions has minimal impact. Skipping CRITICAL questions may result in the same coverage gaps appearing in the output.

### 9.4 Understanding the Three Output Variants

Each variant card has four tabs:

**System Tab (cyan text):** The system prompt — the portion sent as the system role in the API call. This is the architectural backbone: role, rules, constraints, and format specification.

**User Tab (amber text):** The user turn template — the portion sent as the user message. This typically contains the task instruction and the variable injection points (`{{variable_name}}`).

**Guards Tab:** A readable breakdown of the specific overshoot and undershoot mitigations. Review this if a variant seems overly cautious or insufficiently constrained — it tells you exactly what the trade-offs are.

**Meta Tab:** Strengths and "best for" guidance. Use this to decide which variant to take to production.

**Prefill Tab (Advanced variant only, Anthropic models):** The Claude prefill string. Copy this into the `assistant` role of your API messages array as described in Section 5.3.

### 9.5 Using the Prefill Tab

The prefill tab appears only when:
- The target provider is Anthropic
- The gap analysis or framework selection determined that output format locking is warranted
- The target variant is Variant 3 (Advanced)

To use the prefill:
1. Copy the prefill string from the tab
2. In your API call, add a second message with `role: "assistant"` and `content: <the prefill string>`
3. Claude's response will begin from where the prefill ends, not from the beginning

```python
client.messages.create(
    model="claude-sonnet-4-6",
    system=system_prompt,   # From APOST System tab
    messages=[
        {"role": "user",      "content": user_prompt},    # From APOST User tab
        {"role": "assistant", "content": prefill_string}  # From APOST Prefill tab
    ]
)
```

### 9.6 Refining with the AI Chat

The AI chat is designed for **targeted refinements**, not wholesale rewrites. Use it when:

- You need to adjust a specific constraint in one variant
- You want to understand why a particular engineering decision was made
- You want to merge elements from multiple variants
- You need to add domain-specific examples or few-shot demonstrations
- You want to test a hypothesis ("What if we drop the role specification and replace it with X?")

**How to ask effectively:**

Good: "The Execution dimension in Variant 2 scored 55. The output format is specified but there's no schema. Add a strict JSON schema for the output object with field names and types."

Less effective: "Make it better."

The assistant has the full prompt text, TCRTE scores, and gap interview context. Reference variant numbers, dimension names, and specific constraints to get precise revisions.

### 9.7 Quick Action Reference

| Quick Action | When to Use |
|-------------|-------------|
| Make V1 more concise | V1 is too verbose for your system prompt budget |
| Add anti-hallucination guards to V2 | Task involves factual claims from provided documents |
| Convert V3 to reasoning-aware | Realised after generation that the model is a reasoning type |
| Merge best parts of all 3 variants | V1 clarity + V2 structure + V3 guards is what you actually need |
| Add few-shot examples to V2 | Classification or pattern-matching tasks need examples |
| Harden output format constraints | Downstream parser is failing on inconsistent model output |
| What are the biggest risks here? | Pre-deployment review — catch failure modes you haven't considered |
| Rewrite V1 with XML structural bounding | V1 is going to a Claude model and you want stronger boundaries |
| Apply full TCRTE coverage to V3 | V3 scores well on guards but has weak context or role dimension |
| Apply Context Repetition for multi-hop | Task involves multiple sequential reasoning steps over long context |

---

## 10. Task Type Selection Guide

| Task Type | Select When | Typical Frameworks | Key Engineering Concerns |
|-----------|------------|-------------------|------------------------|
| **Planning** | Agent must produce a structured plan, sequence of steps, or roadmap | Progressive Disclosure, TCRTE, CREATE | Preventing scope creep; ensuring each step is actionable |
| **Reasoning** | Chain of logical deductions; evidence-to-conclusion; multi-hop | CoT Ensemble, Reasoning-Aware, CoRe | Ensuring intermediate steps are preserved; context window for long chains |
| **Coding** | Code generation, debugging, refactoring, code review | KERNEL, XML Structured | Output format (fence language); preventing hallucinated imports; test coverage requirements |
| **Routing** | Classifying intent, selecting tools, triage, dispatch | KERNEL, Reasoning-Aware | Exhaustive class coverage; confidence thresholding; fallback handling |
| **Analysis** | Extracting insights from documents; competitive analysis; risk assessment | XML Structured, CoT Ensemble, RAL-Writer | Grounding in provided data; preventing training-prior contamination |
| **Extraction** | Named entity recognition; structured data from unstructured text; parsing | XML Structured, TextGrad | Output schema rigidity; null handling; partial match behaviour |
| **Creative** | Copywriting; narrative generation; brand voice adherence | TCRTE (Tone-heavy), CREATE | Tone dimension; audience specification; format constraints for length |
| **Q&A / RAG** | Answering questions from retrieved documents; chat over documents | XML Structured, CoRe, Anti-hallucination TextGrad | Strict source attribution; uncertainty acknowledgement; no inference beyond documents |

---

## 11. Framework Selection Decision Guide

Use this guide when you are not using Auto-Select and want to make a deliberate framework choice.

```
Is the target model a reasoning model (o-series, Extended Thinking, R1)?
├── YES → Reasoning-Aware (non-negotiable)
└── NO  →
    Is the task high-stakes (medical, legal, financial, safety-critical)?
    ├── YES → CoT Ensemble
    └── NO  →
        Is the task agentic (uses tools, spawns subagents, multi-step)?
        ├── YES → Progressive Disclosure
        └── NO  →
            Does the task involve multiple large documents in context?
            ├── YES → XML Structured
            └── NO  →
                Did TCRTE gap analysis reveal score < 50?
                ├── YES → TCRTE framework + answer the questions
                └── NO  →
                    Is the task simple and the problem "it's too vague"?
                    ├── YES → KERNEL
                    └── NO  →
                        Is explicit reasoning visibility important?
                        ├── YES → CREATE
                        └── NO  → TextGrad (good default for known failure modes)
```

---

## 12. Real-World Examples

### 12.1 Example A — RAG Pipeline Prompt for Financial Analysis

**Raw prompt entered by developer:**
```
Analyze the financial documents and find the risk factors.
```

**TCRTE Gap Analysis Result:**
- Task: 55 (WEAK — "find" is vague; no output structure)
- Context: 15 (MISSING — no domain, no document type, no date range)
- Role: 10 (MISSING — no expertise level)
- Tone: 20 (MISSING — no audience)
- Execution: 5 (MISSING — no output format whatsoever)
- **Overall: 21/100**

**Gap interview questions generated:**
1. (CRITICAL, Context) "What type of financial documents will be provided — SEC filings, internal reports, earnings transcripts, or another format?"
2. (CRITICAL, Execution) "What output format is required — a structured JSON object, a Markdown report, a risk matrix table, or free text?"
3. (CRITICAL, Role) "Should the model assume the perspective of a compliance analyst, an investment analyst, a risk manager, or another professional?"
4. (RECOMMENDED, Task) "Should risks be categorised by type (operational, financial, regulatory, market)? By severity? Both?"
5. (RECOMMENDED, Tone) "Who is the intended reader — a technical analyst, a non-technical executive, or a regulatory body?"

**Developer answers:**
1. SEC 10-K and 10-Q filings from the past 2 fiscal years
2. JSON with keys: `risk_factors` (array of objects with `category`, `description`, `severity`, `source_reference`)
3. Senior compliance analyst with SEC reporting expertise
4. Yes — categorise by type AND severity (Critical/High/Medium/Low)
5. Internal risk team — technical, can handle regulatory terminology

**Optimised Variant 2 System Prompt (condensed):**
```xml
<system_directives>
  <role>
    You are a senior compliance analyst with 12+ years of SEC reporting expertise. 
    You specialise in identifying, categorising, and quantifying material risk factors 
    in public company filings. You prioritise precision over comprehensiveness and 
    explicitly flag when evidence is ambiguous.
  </role>
  
  <task>
    Extract all material risk factors from the provided SEC filings (10-K and 10-Q). 
    Categorise each risk by type and severity. Ground every finding in explicit 
    textual evidence from the provided documents.
  </task>
  
  <constraints>
    <rule>ONLY identify risks explicitly stated or strongly implied in the provided documents. Do not infer risks from your training knowledge about the industry or company.</rule>
    <rule>Every risk entry must include a source_reference pointing to the specific section or paragraph in the source document.</rule>
    <rule>Severity must be one of: Critical | High | Medium | Low. Apply SEC materiality standards.</rule>
    <rule>Do not include risks mentioned only in boilerplate language that appears identically across all companies in the sector.</rule>
  </constraints>
  
  <output_format>
    Return a single JSON object. No preamble, no postamble. Schema:
    {
      "risk_factors": [
        {
          "category": "operational|financial|regulatory|market|other",
          "description": "string — 1-3 sentences",
          "severity": "Critical|High|Medium|Low",
          "source_reference": "Document name, Section, approximate location"
        }
      ],
      "analysis_metadata": {
        "documents_reviewed": ["list of document identifiers"],
        "coverage_confidence": "high|medium|low",
        "flagged_ambiguities": ["list of cases where evidence was ambiguous"]
      }
    }
  </output_format>
</system_directives>
```

**Coverage delta: 21/100 → 91/100**

### 12.2 Example B — Coding Agent System Prompt

**Raw prompt:**
```
You are a coding assistant. Help users write better code.
```

**Framework selected:** KERNEL + XML Structured

**Key gap interview answers:**
- Language: Python 3.11+, occasionally TypeScript
- Constraints: Must suggest type hints; must not use deprecated APIs; must not write global state
- Output format: Always code in fenced blocks; brief explanation before code; no explanation after

**Resulting Advanced Variant system prompt (excerpt):**
```xml
<system_directives>
  <role>
    You are a senior Python engineer (10 years, primarily backend systems and API design) 
    with secondary TypeScript proficiency. You write production-grade, maintainable code 
    and enforce type safety as a non-negotiable standard.
  </role>
  
  <constraints>
    <rule>All Python code must include type hints on all function parameters and return values. Unannotated code is invalid output.</rule>
    <rule>Do not use deprecated Python APIs (anything removed in Python 3.11+).</rule>
    <rule>Do not write or suggest global mutable state. Use dependency injection or configuration objects.</rule>
    <rule>If a user's approach is architecturally flawed, say so explicitly before showing an alternative. Do not silently implement a different approach.</rule>
    <rule>Do not add explanatory comments after the code block. All explanation goes before.</rule>
  </constraints>
  
  <output_format>
    Structure every response as:
    1. One-paragraph explanation of the approach and any concerns
    2. Code block with explicit language specifier (```python or ```typescript)
    3. Nothing after the code block
  </output_format>
</system_directives>
```

### 12.3 Example C — Customer Support Routing

**Raw prompt:**
```
Route customer messages to the right department.
```

**Framework selected:** KERNEL (simple classification task)

**Post-interview Variant 1 (Conservative) — appropriate for this task:**
```
You are a customer support triage agent for [Company]. Your only job is to classify 
incoming customer messages into exactly one department category.

Categories:
- BILLING: Payment issues, invoice disputes, subscription changes, refund requests
- TECHNICAL: Product bugs, integration failures, API errors, performance issues  
- SALES: Upgrade inquiries, new feature questions, pricing questions
- ACCOUNT: Password reset, profile changes, access permissions, account deletion
- ESCALATE: Legal threats, regulatory complaints, executive-level escalation requests

Rules:
- Output exactly one category name in uppercase. Nothing else.
- If a message clearly fits two categories, choose the PRIMARY issue.
- If the message is ambiguous or fits no category, output: ESCALATE
- Never output explanations, apologies, or any text beyond the single category name.

Message to classify:
{{customer_message}}
```

This is an example where KERNEL is the correct choice over XML Structured — the task is simple, the output is a single token, and adding XML overhead would add tokens without adding value.

---

## 13. Common Mistakes and Anti-Patterns

### Anti-Pattern 1 — Skipping the Gap Interview for Complex Tasks

The gap interview adds 2–3 seconds and saves you 30 minutes of iterative refinement. For any task that will run in production at scale, always run the gap analysis. The difference between a 21/100 and 91/100 coverage score is the difference between a prompt that sometimes works and one that reliably works.

### Anti-Pattern 2 — Always Using the Advanced Variant

Variant 3 is heavily guarded — it adds constraints, repetitions, and structural depth that add tokens and can make the prompt feel rigid. For simple tasks, the Advanced variant over-engineers the problem. Start with Variant 2 and promote to Variant 3 only when you observe specific failure modes in testing.

### Anti-Pattern 3 — Treating the Optimised Prompt as Final

APOST generates prompts optimised for your stated intent and target model. It does not know your domain-specific edge cases, your company's regulatory requirements, or your specific failure history. The chat refinement layer exists for this reason. Use it.

### Anti-Pattern 4 — Ignoring the Guards Tab

The Guards tab tells you exactly what failure modes the prompt is protected against. If you deploy a prompt and see unexpected behaviour, check the Guards tab first — there's a high probability the failure corresponds to an undershoot or overshoot case that was identified but de-prioritised.

### Anti-Pattern 5 — Using CoT Instructions with Reasoning Models

If you select an o-series or Extended Thinking model and then manually ask the chat to "add chain-of-thought instructions to Variant 2" — stop. This will degrade performance. The reasoning model's CoT is internal and cannot be steered with external CoT instructions. Ask instead for structural clarity improvements or hard constraint additions.

### Anti-Pattern 6 — One System Prompt for Multiple Models

A prompt optimised for Claude with XML structure will not perform optimally on GPT-4o. Use APOST to generate model-specific variants when you are deploying across providers. The provider-specific engineering rules in Sections 6.1–6.3 explain why.

### Anti-Pattern 7 — Ignoring the "Best For" Guidance

The Meta tab's "Best for" field is not decoration. It encodes the specific production conditions under which each variant is appropriate. Read it before choosing which variant to deploy.

---

## 14. Extending and Integrating APOST

APOST is delivered as a self-contained React component with no external dependencies beyond the Anthropic API. Extending it involves modifying the source JSX file.

### Adding a New Framework

1. Add an entry to the `FRAMEWORKS` array with `id`, `label`, `icon`, and `desc`
2. Add a corresponding entry to the `fwGuide` object in `buildOptimizerPrompt` with the full framework specification as a string
3. The framework will appear automatically in the framework selector and be available to the optimizer

```javascript
// In FRAMEWORKS array:
{id:"dspy", label:"DSPy Declarative", icon:"⊗", desc:"Declarative signatures + compiler-driven teleprompters"}

// In fwGuide inside buildOptimizerPrompt:
dspy: `Apply DSPy-style declarative prompt structure:
- Define the task as a typed signature (input fields → output fields)
- Use ChainOfThought module pattern: task decomposition into typed reasoning steps
- Include an evaluator specification: what metric defines success
- Structure for programmatic compilation: make instructions parametric, not literal`
```

### Adding a New Provider

1. Add an entry to the `PROVIDERS` object with `label`, `icon`, `color`, `soft`, `keyPlaceholder`, `keyHint`, `models` array, and `defaultEndpoint`
2. Add a corresponding entry to the `modelGuide` object in `buildOptimizerPrompt`
3. Update the `changeProvider` function if the provider requires a different auth header pattern

### Connecting to a Real API (Production Mode)

The current implementation routes all calls through Anthropic's API (using the user's key). In production, you would:

1. Create a backend proxy that accepts the optimiser request, injects a server-side API key, and returns the response
2. Replace the `fetch("https://api.anthropic.com/v1/messages", ...)` calls with calls to your proxy
3. Remove the API key input from the left panel (key lives on the server)
4. Add authentication to the proxy to prevent unauthorised use

This pattern means your users never need to manage API keys, and you can swap underlying models without UI changes.

### Persisting Optimisation History

The current implementation holds session state in React `useState` hooks — it does not persist across browser refreshes. To add persistence:

1. Use the artifact storage API (`window.storage`) to save the `result`, `gapData`, and `answers` state after each successful optimisation
2. Load from storage on component mount and restore state
3. Add a history panel showing past optimisations indexed by prompt hash and timestamp

---

## 15. Glossary of Terms

| Term | Definition |
|------|-----------|
| **Attention Mechanism** | The mathematical operation in transformers that determines how much weight each token assigns to every other token in the sequence |
| **Auto-Enrichment** | An optimisation that APOST applies automatically without requiring user input — e.g., primacy/recency placement of constraints |
| **Context Engineering** | The practice of architecting the complete informational environment around an LLM, as distinct from writing a single prompt |
| **CoRe** | Context Repetition — a technique that repeats critical context at k positions in the prompt, where k = number of reasoning hops |
| **CoT** | Chain-of-Thought — the technique of eliciting step-by-step reasoning from a model |
| **Coverage Delta** | The improvement in TCRTE overall score between the raw prompt and the optimised prompt |
| **CREATE** | Context · Role · Instruction · Steps · Execution — a sequential prompt framework |
| **Gap Interview** | APOST's Phase 2 workflow — presenting TCRTE gap analysis results and targeted questions to fill coverage gaps |
| **IFEval** | Instruction Following Evaluation — a benchmark framework for measuring instruction adherence accuracy |
| **KERNEL** | Keep · Explicit · Narrow · Known · Enforce · Logical — a minimalist prompt clarity framework |
| **Lost in the Middle** | The empirically observed phenomenon where LLMs exhibit low attention to information positioned in the middle of long contexts |
| **Medprompt** | Microsoft Research's prompt engineering framework combining dynamic kNN few-shot selection, auto-CoT, and ensemble methods |
| **Mega-Prompt** | An anti-pattern where all operational procedures are encoded into a single monolithic system prompt |
| **Overshoot** | Failure mode where the model does more than instructed — hallucination, scope creep, excessive verbosity |
| **Prefill** | Anthropic API technique where the first tokens of the assistant turn are provided by the caller to lock output format |
| **Primacy Effect** | The tendency of LLMs to assign higher attention to tokens near the beginning of the context |
| **Progressive Disclosure** | The Agent Skills architecture — loading operational information in layers based on task requirements |
| **Prompt Chaining** | Breaking a complex task into a sequence of simpler prompts where each output feeds the next input |
| **Prompt Engineering** | The practice of writing and refining prompts for LLMs |
| **RAG** | Retrieval-Augmented Generation — augmenting LLM prompts with documents retrieved from an external knowledge base |
| **RAL-Writer** | Retrieval-Augmented Long-Text Writer — a technique that restates middle-context instructions at the end of the prompt |
| **Reasoning Model** | An LLM trained with RL to generate internal reasoning traces before producing output (o-series, Extended Thinking, R1) |
| **Recency Effect** | The tendency of LLMs to assign higher attention to tokens near the end of the context |
| **TCRTE** | Task · Context · Role · Tone · Execution — a five-pillar prompt coverage framework |
| **TextGrad** | A prompt optimisation framework that uses LLM-generated textual critiques as gradients for prompt improvement |
| **Token Efficiency** | The ratio of semantic value to token count in a prompt — a key factor in both cost and model performance |
| **U-Shaped Attention Curve** | The empirical observation that LLM attention quality is high at context boundaries and low in the middle |
| **Undershoot** | Failure mode where the model does less than instructed — ignoring constraints, incomplete output, format violations |
| **XML Semantic Bounding** | Using XML-like tags to create hard semantic boundaries between different zones of a prompt |

---

## 16. References and Further Reading

### Primary Research Papers

1. **Lost in the Middle: How Language Models Use Long Contexts**
   Nelson F. Liu et al. — Established the empirical U-shaped attention curve and quantified the lost-in-the-middle phenomenon.

2. **TextGrad: Automatic "Differentiation" via Text**
   Yuksekgonul et al., Published in Nature — Introduced textual backpropagation as a prompt optimisation mechanism.

3. **The Power of Prompting (Medprompt)**
   Microsoft Research — Demonstrated that prompt engineering with dynamic kNN selection, auto-CoT, and ensembling could match domain-specific fine-tuned models.

4. **IFEval-Extended: Enhancing Instruction-Following Evaluation**
   Established standardised metrics for instruction coverage measurement.

5. **LLMLingua: Innovating LLM Efficiency with Prompt Compression**
   Microsoft Research — Perplexity-based semantic compression for reducing token footprint without losing instructional coverage.

6. **AutoPrune: Each Complexity Deserves a Pruning Policy**
   Adaptive complexity-based prompt pruning framework.

### Provider Documentation

7. **Anthropic Claude Prompting Best Practices**
   `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices`

8. **Anthropic Agent Skills Documentation**
   `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview`

9. **OpenAI Reasoning Best Practices**
   `https://developers.openai.com/api/docs/guides/reasoning-best-practices`

10. **Google Gemini Prompt Design Strategies**
    `https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/prompt-design-strategies`

### Conceptual Background

11. **Agentic AI Explained — MIT Sloan**
    `https://mitsloan.mit.edu/ideas-made-to-matter/agentic-ai-explained`

12. **Effective Context Engineering for AI Agents — Anthropic Engineering**
    `https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents`

13. **DSPy: Declarative Self-Improving Python**
    Framework documentation for programmatic prompt compilation.

14. **The Architecture of Instruction Adherence: Advanced Frameworks for Coverage, Emphasis, and Optimization in Generative AI**
    Primary research document forming the theoretical basis for APOST v4's TCRTE scoring, CoRe/RAL-Writer injection, and provider-specific optimisation rules.

---

> **A note on the research backing of this tool:**
> Every feature in APOST v4 corresponds to a documented, peer-reviewed or industry-validated technique. Nothing in this tool is based on intuition or anecdote. The TCRTE gap audit exists because instruction coverage is a measurable, benchmarkable metric. CoRe exists because context repetition has been empirically shown to reduce multi-hop accuracy degradation by up to 26%. RAL-Writer exists because the retrieve-and-restate mechanism is documented to counteract the lost-in-the-middle phenomenon. Prefill exists because Anthropic explicitly documents it as the most reliable mechanism for output format locking.
>
> When you use APOST, you are not using a "clever tool." You are applying a systematic engineering methodology backed by the same research that the leading AI labs use to design their own models' prompting interfaces. The goal is to make that research accessible without requiring you to have read it.

---

*APOST v4 Documentation — written for developers, architects, and engineers who believe that prompts are source code and deserve to be treated as such.*
