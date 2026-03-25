"""
Optimizer prompt builder.

Constructs the meta-prompt for generating optimized prompt variants.
"""

from typing import Optional, Any

from app.models.providers import PROVIDERS, FRAMEWORKS, TASK_TYPES


# Framework-specific guidelines
FRAMEWORK_GUIDELINES = {
    "kernel": """K-Keep simple (one objective). E-Explicit (MUST NOT as clear as MUST). R-Narrow (one job). N-Known criteria. L-Logical order (Context→Task→Constraints→Format).""",
    "xml_structured": """Wrap every semantic zone in XML tags. Isolate user vars. Place <constraints> at TOP. Nest docs.""",
    "progressive": """3 layers: DISCOVERY (metadata ~100t) → ACTIVATION (logic, rules, format) → EXECUTION (examples, scripts).""",
    "cot_ensemble": """2-3 few-shot examples with reasoning traces. Multi-path instruction. Self-check step. Ensemble synthesis.""",
    "textgrad": """Enumerate failure modes. Counter-constraint per mode. Anti-hallucination guard. Completion guard. Rigid output schema.""",
    "reasoning_aware": """Simplify prose. No "think step by step". Declare constraints + format UPFRONT. Let model reason autonomously.""",
    "tcrte": """Ensure all 5 TCRTE pillars are explicitly addressed: Task clarity, Context grounding, Role definition, Tone specification, Execution constraints. Score each in the output.""",
    "create": """Sequential structure: Context → Role → Instruction → Steps → Execution. Force reasoning trace before commitment.""",
    "auto": """Auto-select: reasoning models→Reasoning-Aware; multi-doc→XML; agents→Progressive; high-stakes→CoT-Ensemble; coverage gaps→TCRTE.""",
}

# Model-specific guidelines
MODEL_GUIDELINES = {
    "anthropic": """- Heavy XML semantic tags: <system_directive> <task> <constraints> <context> <input_variables> <output_format>
- Critical constraints FIRST (primacy), echo key rules at END (recency) — "lost in the middle" prevention
- Role → Task → Context → Constraints → Format → Variables
- Nested XML for docs: <documents><document index="1">…</document></documents>""",
    "anthropic_prefill": """- INCLUDE a <prefill_suggestion> field: the first few tokens of the assistant turn to lock output format""",
    "openai_reasoning": """- NO chain-of-thought forcing — reasoning models have native CoT
- Extremely concise system prompt with Markdown structure
- Focus: output format, hard constraints, what NOT to do""",
    "openai_standard": """- Markdown: ### headers, **bold**, bullets
- System = role + rules. User = task + injected data
- Triple-backtick fences for code/structured data""",
    "google": """- XML angle-bracket tags — Gemini adheres strongly
- Role → Instructions → Examples → Task → Format""",
}


def build_optimizer_prompt(
    raw_prompt: str,
    input_variables: Optional[str],
    framework: str,
    task_type: str,
    provider: str,
    model: dict[str, Any],
    is_reasoning_model: bool,
    answers: Optional[dict[str, str]],
    gap_data: Optional[dict[str, Any]],
    core_k: int = 2,
    few_shot_examples: Optional[list[Any]] = None,
) -> str:
    """
    Build the optimization prompt for generating three prompt variants.

    Args:
        raw_prompt: The raw prompt to optimize.
        input_variables: Optional declared input variables.
        framework: The optimization framework to apply.
        task_type: The type of task.
        provider: The LLM provider key.
        model: The target model info dict with id, label, reasoning.
        is_reasoning_model: Whether the target is a reasoning model.
        answers: Optional user answers to gap interview questions.
        gap_data: Optional gap analysis data from previous step.
        core_k: CoRe repetition depth from hop_counter (optimization route).
        few_shot_examples: kNN-retrieved corpus entries for cot_ensemble (knn_retriever).

    Returns:
        The complete meta-prompt for optimization.
    """
    provider_label = PROVIDERS.get(provider, {}).get("label", provider)
    model_label = model.get("label", "Unknown") if isinstance(model, dict) else str(model)
    model_type = "REASONING — native CoT, no step-by-step instructions" if is_reasoning_model else "STANDARD"

    # Find framework info
    framework_info = next(
        (f for f in FRAMEWORKS if f["id"] == framework),
        FRAMEWORKS[0]  # Default to auto
    )

    # Find task type info
    task_info = next(
        (t for t in TASK_TYPES if t["id"] == task_type),
        TASK_TYPES[0]  # Default to planning
    )

    # Determine complexity and techniques from gap_data
    complexity = gap_data.get("complexity", "medium") if gap_data else "medium"
    techniques = gap_data.get("recommended_techniques", []) if gap_data else []

    use_core = "CoRe" in techniques or complexity == "complex"
    use_ral = "RAL-Writer" in techniques
    use_prefill = provider == "anthropic" and "Prefill" in techniques

    # Build model guidelines
    if provider == "anthropic":
        model_guide = MODEL_GUIDELINES["anthropic"]
        if use_prefill:
            model_guide += "\n" + MODEL_GUIDELINES["anthropic_prefill"]
    elif provider == "openai":
        model_guide = MODEL_GUIDELINES["openai_reasoning"] if is_reasoning_model else MODEL_GUIDELINES["openai_standard"]
    else:
        model_guide = MODEL_GUIDELINES["google"]

    # Build framework guidelines
    fw_guide = FRAMEWORK_GUIDELINES.get(framework, FRAMEWORK_GUIDELINES["auto"])

    # Build technique blocks
    core_block = ""
    if use_core:
        core_block = f"""<core_technique>
APPLY CONTEXT REPETITION (CoRe): For multi-hop reasoning, place the most critical context in
approximately {core_k} attention-favorable positions (at minimum at the START and END of the
user prompt). Mark repetitions clearly.
</core_technique>"""

    ral_block = ""
    if use_ral:
        ral_block = """<ral_technique>
APPLY RAL-WRITER RESTATE: Identify instructions likely to be "lost in the middle" and restate them at the END of the system prompt inside a <restate_critical> block.
</ral_technique>"""

    # Build answers block
    answers_block = ""
    if answers:
        answer_lines = "\n\n".join([f"Q: {q}\nA: {a}" for q, a in answers.items()])
        answers_block = f"""
<gap_interview_answers>
{answer_lines}
</gap_interview_answers>"""

    # Build variables block
    variables_block = ""
    if input_variables and input_variables.strip():
        variables_block = f"<input_variables>{input_variables}</input_variables>"

    few_shot_block = ""
    if few_shot_examples:
        parts: list[str] = []
        for i, ex in enumerate(few_shot_examples, 1):
            if isinstance(ex, dict):
                parts.append(
                    f'<example index="{i}">\n'
                    f"<raw>{ex.get('raw_prompt', '')}</raw>\n"
                    f"<optimized>{ex.get('optimized_system_prompt', '')}</optimized>\n"
                    f"<trace>{ex.get('reasoning_trace', '')}</trace>\n"
                    "</example>"
                )
            else:
                parts.append(f'<example index="{i}">{ex!s}</example>')
        few_shot_block = (
            "<retrieved_few_shot_demonstrations>\n"
            + "\n".join(parts)
            + "\n</retrieved_few_shot_demonstrations>\n"
        )

    # Build prefill instruction
    prefill_instruction = ""
    if use_prefill:
        prefill_instruction = """
For the Advanced variant, include a prefill_suggestion field with the ideal first tokens of the assistant turn."""

    return f"""You are an expert AI prompt engineer specialising in context engineering, attention management, and instruction coverage. Transform the raw prompt into 3 production-grade variants.

<target_configuration>
  <provider>{provider_label}</provider><model>{model_label}</model>
  <model_type>{model_type}</model_type>
  <task_type>{task_info["label"]}</task_type><complexity>{complexity}</complexity>
  <framework>{framework_info["label"]}: {framework_info["description"]}</framework>
</target_configuration>

<model_guidelines>{model_guide}</model_guidelines>
<framework_guidelines>{fw_guide}</framework_guidelines>
{core_block}
{ral_block}

<failure_modes>
  <overshoot>Hallucination, scope creep, infinite loops, applying irrelevant policies</overshoot>
  <undershoot>Ignoring constraints, incomplete output, losing instructions mid-context</undershoot>
</failure_modes>

<raw_prompt>{raw_prompt}</raw_prompt>
{few_shot_block}
{variables_block}
{answers_block}

Generate 3 variants: Conservative (clarity-first), Structured (full framework), Advanced (max guards + all auto-enrichments applied).
{prefill_instruction}

Respond ONLY as valid JSON — no markdown fences:
{{
  "analysis":{{"detected_issues":[],"model_notes":"","framework_applied":"","coverage_delta":"Coverage improved from X% → Y% after gap answers"}},
  "techniques_applied":["CoRe"|"RAL-Writer"|"Prefill"|"XML-Bounding"|etc],
  "variants":[
    {{"id":1,"name":"Conservative","strategy":"",
     "system_prompt":"","user_prompt":"",{'"prefill_suggestion":"",' if use_prefill else ''}
     "token_estimate":0,"tcrte_scores":{{"task":0,"context":0,"role":0,"tone":0,"execution":0}},
     "strengths":[],"best_for":"","overshoot_guards":[],"undershoot_guards":[]}},
    {{"id":2,"name":"Structured",  "strategy":"","system_prompt":"","user_prompt":"","token_estimate":0,"tcrte_scores":{{"task":0,"context":0,"role":0,"tone":0,"execution":0}},"strengths":[],"best_for":"","overshoot_guards":[],"undershoot_guards":[]}},
    {{"id":3,"name":"Advanced",    "strategy":"","system_prompt":"","user_prompt":"","token_estimate":0,"tcrte_scores":{{"task":0,"context":0,"role":0,"tone":0,"execution":0}},"strengths":[],"best_for":"","overshoot_guards":[],"undershoot_guards":[]}}
  ]
}}"""
