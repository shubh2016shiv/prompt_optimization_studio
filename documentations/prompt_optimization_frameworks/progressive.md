# Progressive Disclosure: A Comprehensive Guide
### *Layered Agent Design: Discovery → Activation → Execution*

> **Who this guide is for:** Both newcomers building their first multi-step agent and seasoned engineers wanting to understand the research theory, routing logic, and algorithmic pipeline behind APOST's Progressive Disclosure framework. Read top-to-bottom for the full mental model, or jump to any section independently.

---

## Table of Contents

1. [What Problem Does Progressive Disclosure Solve?](#1-what-problem-does-progressive-disclosure-solve)
2. [The Research Foundations](#2-the-research-foundations)
3. [The Core Mental Model](#3-the-core-mental-model)
4. [The Three Control Layers](#4-the-three-control-layers)
5. [How It Works: The Algorithm](#5-how-it-works-the-algorithm)
6. [The Progressive Blueprint](#6-the-progressive-blueprint)
7. [The Three Optimization Tiers](#7-the-three-optimization-tiers)
8. [The Quality Gate](#8-the-quality-gate)
9. [Implementation Architecture](#9-implementation-architecture)
10. [Configuration and Tuning](#10-configuration-and-tuning)
11. [When to Use Progressive Disclosure (and When Not To)](#11-when-to-use-progressive-disclosure-and-when-not-to)
12. [Diagnosing Common Failures](#12-diagnosing-common-failures)
13. [Performance Playbook](#13-performance-playbook)
14. [Future Directions](#14-future-directions)
15. [References](#15-references)

---

## 1. What Problem Does Progressive Disclosure Solve?

### The Agentic Spaghettification Problem

When users build prompts for agents (agents that use tools, execute multi-step plans, or navigate state machines), they typically write flat, imperative lists of instructions. For example: "You are a customer service bot. If the user asks for a refund, check their account. If their account is over 30 days old, refuse the refund. Use the `check_account` tool to do this. Always be polite. If they ask about shipping, give them the tracking link."

This "flat" approach causes significant failure modes when deployed:

| Failure Mode | What It Looks Like | Why It Happens |
|---|---|---|
| **Trigger Skipping** | Model executes an action without checking the condition first. | Conditional logic is blended with procedural logic. |
| **Capability Hallucination** | Model invents a `refund_user` tool that doesn't exist. | The boundaries of what the system *can* do are not explicitly defined. |
| **Unbounded Branching** | Model executes the refund logic AND the shipping logic simultaneously. | No execution ordering guard to force mutual exclusivity. |
| **Logic Entanglement** | Safety constraints are forgotten during complex executions. | Safety policy is buried inside specific operational steps instead of acting as a global bound. |

> **Mental Model — The Employee Handbook vs. The Standard Operating Procedure (SOP):** A flat prompt acts like a 100-page employee handbook. When a crisis happens, the employee has to remember page 42 while reading page 99. Progressive Disclosure refactors the prompt into an **SOP**. It says: "Here is your desk (Discovery). If X happens, turn to page 2 (Activation). Page 2 says: do A, then B, then C (Execution)."

### What Progressive Disclosure Produces

Progressive Disclosure rewrites a raw prompt into a strictly separated, layered control structure. It forces the LLM to process instructions in a specific cognitive order: understand capabilities → evaluate triggers → execute procedures.

---

## 2. The Research Foundations

Progressive Disclosure synthesizes several major breakthroughs in agentic reasoning, tool use, and cognitive load management in LLMs.

### 2.1 ReAct: Synergizing Reasoning and Acting

**The finding:** LLMs stuck in pure "action" mode frequently hallucinate tools and enter infinite loops. Forcing the model to explicitly separate *Reasoning/Observation* from *Acting* dramatically improves task success rates.
**The source:** Yao et al. (2022), "ReAct: Synergizing Reasoning and Acting in Language Models".
**How Progressive Disclosure operationalizes this:** The framework rigidly separates the **Activation Layer** (Reasoning/Triggers) from the **Execution Layer** (Acting/Procedures). The LLM is structurally forbidden from executing a procedure before evaluating the trigger condition.

### 2.2 Toolformer: Explicit Capability Modeling

**The finding:** LLMs struggle to know *when* to use external plugins unless their capability boundaries are explicitly and formally documented within the context window.
**The source:** Schick et al. (2023), "Toolformer: Language Models Can Teach Themselves to Use Tools".
**How Progressive Disclosure operationalizes this:** The **Discovery Layer** explicitly enumerates boundaries. Instead of assuming the model knows its own limits, this layer forces the definition of available tools, capabilities, and context visibility upfront.

### 2.3 "Lost in the Middle" & Context Window Limits

**The finding:** When safety boundaries and failure-mode controls are buried in the middle of long, multi-step agent prompts, LLMs reliably forget them by the time they reach the output execution phase.
**The source:** Liu et al. (2023), "Lost in the Middle: How Language Models Use Long Contexts".
**How Progressive Disclosure operationalizes this:** Structured ordering places Discovery and Activation in the high-attention early tokens. The Advanced tier actively combats middle-loss by duplicating critical `safety_bounds` to the very end of the prompt (the Recency Echo).

---

## 3. The Core Mental Model

### Finite State Machine (FSM) Prompting

To succeed with agentic prompts, you must treat the LLM as the CPU inside a Finite State Machine rather than a text generator. 

The CPU needs to know:
1. What hardware is attached to me? (Discovery)
2. Which interrupt (trigger) should I listen for? (Activation)
3. What is the execution subroutine? (Execution)

If you blend the subroutine with the interrupt, the CPU executes the subroutine constantly. Progressive Disclosure enforces this FSM architecture at the token level.

```
┌────────────────────────────────────────────────────────┐
│  THE PROGRESSIVE FSM ARCHITECTURE                      │
│                                                        │
│  [ LAYER 1: DISCOVERY ]                                │
│   Capabilities: "I can read tickets and use tools"     │
│   Visibility: "I only see the current user thread"     │
│                                                        │
│  [ LAYER 2: ACTIVATION ]                               │
│   Trigger A: "IF user asks for refund"                 │
│   Action A: "Execute refund validation"                │
│                                                        │
│  [ LAYER 3: EXECUTION ]                                │
│   Procedure A:                                         │
│   1. Retrieve order history                            │
│   2. Check 30-day policy                               │
│   3. Emit JSON response                                │
│                                                        │
│  [ SYSTEM GUARDS ]                                     │
│   Output Format / Safety Bounds / Failure Modes        │
└────────────────────────────────────────────────────────┘
```

---

## 4. The Three Control Layers Explained

### Layer 1: Discovery (The "What")
**Purpose:** Sets the absolute limits of the agent's universe. It defines available capabilities, tool schemas, and context visibility.
**Prevents:** Capability hallucination ("I will now calculate the weather for you" — when no weather tool exists).

### Layer 2: Activation (The "When")
**Purpose:** A strict routing table consisting of `IF [trigger] THEN [action] (priority)`. 
**Prevents:** Premature execution and overlapping workflow branching. By defining priorities, it resolves conflicts when a user input triggers multiple conditions.

### Layer 3: Execution (The "How")
**Purpose:** Pure, deterministic, ordered procedural steps. It assumes the Activation trigger has already been passed.
**Prevents:** Skipped procedural steps and tangled logic.

---

## 5. How It Works: The Algorithm

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│               PROGRESSIVE DISCLOSURE ALGORITHM FLOW             │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │  STAGE 1: ENRICH                     │
  │  Merge gap-interview answers         │
  └───────────────┬──────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────┐
  │  STAGE 2: LAYERED BLUEPRINT PARSE    │
  │  LLM → strict JSON extraction        │
  │                                      │
  │  Extracts:                           │
  │  • discovery_metadata                │
  │  • activation_rules [trigger, action]│
  │  • execution_logic                   │
  │  • output_format                     │
  │  • safety_bounds                     │
  │  • failure_modes                     │
  │                                      │
  │  ❌ Parse fails? → Use default FSM   │
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
  │  │Clean    │ │Enforced  │ │+Escal-│ │
  │  │layering │ │determin- │ │ation &│ │
  │  │         │ │ism &     │ │Recency│ │
  │  │         │ │ordering  │ │Echo   │ │
  │  └────┬────┘ └────┬─────┘ └───┬───┘ │
  │       │           │           │     │
  │  ❌fail?      ❌fail?     ❌fail?   │
  │       ↓           ↓           ↓     │
  │  Deterministic layered template      │
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
def progressive_optimize(request):
    enriched = integrate_gap_answers(request)

    # 1. Parse FSM Blueprint
    blueprint = llm_parse_json(enriched, schema=PROGRESSIVE_SCHEMA)

    # 2. Tiered Rewrites
    rewritten = {}
    for tier in ["conservative", "structured", "advanced"]:
        try:
            rewritten[tier] = llm_rewrite(
                raw_prompt=enriched,
                blueprint=blueprint,
                objective=TIER_OBJECTIVES[tier]
            )
        except Exception:
            rewritten[tier] = deterministic_fallback_progressive(blueprint, tier=tier)

    # 3. Variable Injection
    for tier in rewritten:
        rewritten[tier] = inject_input_variables(rewritten[tier], request)

    # 4. Advanced: Recency Echo
    rewritten["advanced"] = restate_constraints_in_recency_zone(
        rewritten["advanced"],
        constraints=blueprint["safety_bounds"],
        provider=request.provider
    )

    response = build_variants(rewritten)
    return quality_gate(response, request)
```

---

## 6. The Progressive Blueprint

To execute a deep rewrite, APOST first decomposes the prompt into the following data structure:

| Field | Type | Function |
|---|---|---|
| `discovery_metadata` | list[str] | Bounding box of tools and capabilities. |
| `activation_rules` | list[dict] | Array of `{trigger: str, action: str, priority: str}`. |
| `execution_logic` | list[str] | Absolute procedural steps. |
| `output_format` | string | Format boundary. |
| `safety_bounds` | list[str] | Guardrails restricting execution. |
| `failure_modes` | list[str] | Explicit "Prevent: X" anti-patterns. |

> **Normalizing Triggers:** The `_parse_progressive_blueprint` extractor forces the LLM to map vague contextual statements into strict IF/THEN conditionals for the `activation_rules`. This is the single most critical step in fixing broken agent prompts.

---

## 7. The Three Optimization Tiers

```
┌──────────────────────────────────────────────────────────────┐
│  THE THREE TIERS                                             │
└──────────────────────────────────────────────────────────────┘

  CONSERVATIVE ─────────────────────────────────────────────────
  
  What it does:
  • Cleans language into explicit Discovery, Activation, and 
    Execution blocks.
  • Removes instruction blending while keeping tone identical.
  
  Best for: Simple rule-based bots that require slight 
  architectural cleanup but don't need heavy execution guards.
  
  ──────────────────────────────────────────────────────────────

  STRUCTURED ───────────────────────────────────────────────────
  
  What it does:
  • All CONSERVATIVE benefits, plus:
  • Enforces trigger-to-action determinism.
  • Adds the "ORDERING GUARD": explicitly tells the model to 
    "First check activation, then execute matching procedure, 
    then verify output."
  
  Best for: Multi-step agents in production, tool-use 
  frameworks, and routing pipelines.
  
  ──────────────────────────────────────────────────────────────

  ADVANCED ─────────────────────────────────────────────────────
  
  What it does:
  • All STRUCTURED benefits, plus:
  • Escalation Guard: Conflict resolution rules for competing 
    triggers.
  • Recency Echo: Restates critical safety bounds at the bottom 
    of the prompt to defeat "Lost in the Middle".
  • Explicit failure-mode defect prevention.
  
  Best for: High-stakes financial/legal agents, autonomous 
  systems, and uncontrolled-input facing environments.
  
  ──────────────────────────────────────────────────────────────
```

---

## 8. The Quality Gate

The shared internal judge critiques Progressive variants against specific architectural rubrics:
- Are activation conditions mutually exclusive or appropriately prioritized?
- Do execution steps contain rogue trigger logic? (Sub-triggers should be minimized).
- Are the safety bounds robust enough to handle empty tool returns or missing data?

If any variant fails this criteria (and `quality_gate_mode` permits), the judge's enhancement loop will actively repair the overlap or logic failure before returning the response.

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
        │   → selects progressive when:
        │     task_type == "agentic" OR "tool_use"
        │     OR as a lower-cost default for complex logic ops.
        │
        ▼
  OptimizerFactory.get_optimizer("progressive")
        │
        ▼
  progressive_disclosure_optimizer.py  ◄─── Core logic
  ProgressiveDisclosureOptimizer
        │
        ├── _parse_progressive_blueprint()
        │
        ├── _rewrite_with_progressive_objective()
        │
        ├── _fallback_progressive_prompt() (deterministic IF/THEN)
        │
        └── _refine_variants_with_quality_critique()
```

### Deterministic Fallback
If the LLM rewrite fails, `_fallback_progressive_prompt` programmatically string-builds:
```
DISCOVERY LAYER:
- {capability 1}

ACTIVATION LAYER:
- IF: {trigger}
  THEN: {action} (priority: {priority})

EXECUTION LAYER:
1. {step 1}
...
```
This guarantees that 100% of API requests reliably return three tiered variants, regardless of backend model instability.

---

## 10. Configuration and Tuning

### Parameter Reference

| Parameter | Tuning Advice |
|---|---|
| `MAX_TOKENS_COMPONENT_EXTRACTION` | Reduce if the `activation_rules` list captures unnecessary paragraphs instead of concise conditions. |
| `MAX_TOKENS_PROGRESSIVE_REWRITE` | Increase if testing highly complex agents, as the Advanced tier's Escalation Guards and Recency Echos consume significant tokens. |
| `quality_gate_mode` | Set to `sample_one_variant` for a high-quality Advanced output at 1/3 the critique cost. |

---

## 11. When to Use Progressive Disclosure (and When Not To)

### Strong Default For:

```
✅  Tool-using agents (ReAct loops, function calling)
✅  Multi-step customer service bots
✅  Routing agents (evaluating text and directing to subsystems)
✅  Complex planning tasks with conditional branching
```

### Consider Alternatives When:

```
⚠️  The task relies heavily on XML document extraction → Use 
    XML Structured Bounding instead.
⚠️  The prompt is meant for creative, persona-driven dialogue 
    with minimal rules → Use CREATE.
⚠️  The execution requires highly intense deductive reasoning 
    → Use CoT Ensemble or Reasoning Aware.
```

---

## 12. Diagnosing Common Failures

| Symptom | Most Likely Cause | Where to Investigate |
|---|---|---|
| Wrong workflow triggered | Activation conditions are overlapping / poorly prioritized | Blueprint `activation_rules`, raw prompt |
| Skipped procedural steps | Execution logic lacks enforced ordering | Upgrade to Structured/Advanced tier |
| Unbounded branching | Over-triggering without mutual exclusivity guards | Ensure "Ordering Guard" is present in prompt |
| API failures / Fallback triggered | LLM returning non-JSON on blueprint extraction | `_parse_progressive_blueprint()` |

---

## 13. Performance Playbook

**Tip 1: Push Tool Schemas into Discovery.**
When optimizing an agent prompt, ensure the raw prompt explicitly lists the tools available. The Progressive blueprint will naturally capture these into the Discovery Layer, making the subsequent activation logic vastly more reliable.

**Tip 2: Prioritize Activation Rules.**
If a user intent might trigger two simultaneous actions in your raw prompt, edit the raw prompt to state which action takes precedence. Progressive Disclosure's `priority` parser will capture this and codify it in the Advanced tier's Escalation Guard.

---

## 14. Future Directions

1. **Explicit State-Machine Compilation:** Evolve the layered prompt into an actual compiled state machine (JSON logic map) that can execute routing outside of the LLM context to save compute.
2. **Tool-Schema Binding:** Allow users to pass external OpenAPI JSON schemas during request submission. The optimizer would dynamically bind these schemas into the Discovery layer.
3. **Circular Trigger Detection:** Implement static Python checks validating that no `activation_rule` action generates a state that retriggers its own starting condition (Infinite ReAct loop prevention).

---

## 15. References

1. **Yao, S., et al. (2022).** "ReAct: Synergizing Reasoning and Acting in Language Models." *arXiv:2210.03629.* — Foundational architecture separating logic evaluation from tool execution.
2. **Schick, T., et al. (2023).** "Toolformer: Language Models Can Teach Themselves to Use Tools." *arXiv:2302.04761.* — Demonstrates the necessity of explicit capability modeling.
3. **Liu, N. F., et al. (2023).** "Lost in the Middle: How Language Models Use Long Contexts." *arXiv:2307.03172.* — Basis for the Recency Echo countermeasure applied to safety bounds.
4. **APOST Internal Documentation:** `APOST_v4_Documentation.md` and `backend/app/services/optimization/frameworks/progressive_disclosure_optimizer.py`.

---

*Progressive Disclosure is part of the APOST prompt optimization suite. For framework selection guidance, see the auto-router documentation in `framework_selector.py`.*
