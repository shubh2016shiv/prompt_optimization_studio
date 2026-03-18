"""
Chat system prompt builder.

Builds the system prompt for the AI chat assistant with full session context.
"""

from typing import Optional, Any

from app.models.providers import PROVIDERS, TCRTE_DIMENSIONS


def build_chat_system_prompt(context: Optional[dict[str, Any]] = None) -> str:
    """
    Build the system prompt for the chat assistant.

    Args:
        context: Optional session context containing raw_prompt, variants, gap_data, answers, etc.

    Returns:
        The system prompt string for the chat assistant.
    """
    if not context:
        return _build_generic_system_prompt()

    return _build_contextual_system_prompt(context)


def _build_generic_system_prompt() -> str:
    """Build a generic system prompt when no context is available."""
    return """You are APOST Assistant — an expert AI prompt engineer. Help users design, refine, and optimise prompts.

Your expertise includes:
- TCRTE framework (Task, Context, Role, Tone, Execution)
- KERNEL methodology (Keep · Explicit · Narrow · Known · Enforce · Logical)
- XML semantic bounding for Claude models
- Context Repetition (CoRe) for multi-hop reasoning
- RAL-Writer restate technique for long contexts
- TextGrad iterative constraint hardening
- DSPy declarative prompt compilation
- Medprompt ensemble techniques
- Overshoot/undershoot failure mode prevention
- Reasoning-model specific prompting (o-series, extended thinking)

Guidelines:
- Be concise, technical, and actionable
- Provide specific code/prompt examples when helpful
- Explain the "why" behind recommendations
- Reference research and best practices where relevant"""


def _build_contextual_system_prompt(context: dict[str, Any]) -> str:
    """Build a system prompt with full session context."""
    raw_prompt = context.get("raw_prompt", "")
    variables = context.get("variables", "")
    framework = context.get("framework", "auto")
    task_type = context.get("task_type", "reasoning")
    provider = context.get("provider", "anthropic")
    model = context.get("model", {})
    model_label = model.get("label", "Unknown") if isinstance(model, dict) else str(model)
    is_reasoning = context.get("is_reasoning", False)
    result = context.get("result", {})
    gap_data = context.get("gap_data", {})
    answers = context.get("answers", {})

    provider_label = PROVIDERS.get(provider, {}).get("label", provider)

    # Build TCRTE scores section
    tcrte_section = ""
    if gap_data and "tcrte" in gap_data:
        tcrte = gap_data["tcrte"]
        tcrte_lines = []
        for dim in TCRTE_DIMENSIONS:
            dim_id = dim["id"]
            if dim_id in tcrte:
                score = tcrte[dim_id].get("score", 0)
                status = tcrte[dim_id].get("status", "unknown")
                tcrte_lines.append(f"  {dim['label']}: {score}/100 ({status})")
        if tcrte_lines:
            tcrte_section = f"""
<gap_analysis>
  TCRTE overall: {gap_data.get('overall_score', 0)}/100
{chr(10).join(tcrte_lines)}
</gap_analysis>"""

    # Build answers section
    answers_section = ""
    if answers:
        answer_lines = [f"  Q: {q}\n  A: {a}" for q, a in answers.items()]
        answers_section = f"""
<gap_answers>
{chr(10).join(answer_lines)}
</gap_answers>"""

    # Build variants section
    variants_section = ""
    if result and "variants" in result:
        variant_blocks = []
        for variant in result["variants"]:
            tcrte_scores = variant.get("tcrte_scores", {})
            tcrte_str = f"T{tcrte_scores.get('task', 0)} C{tcrte_scores.get('context', 0)} R{tcrte_scores.get('role', 0)} Tone{tcrte_scores.get('tone', 0)} E{tcrte_scores.get('execution', 0)}"
            
            prefill_line = ""
            if variant.get("prefill_suggestion"):
                prefill_line = f"\nPREFILL: {variant['prefill_suggestion']}"

            variant_blocks.append(f"""
=== VARIANT {variant.get('id', '?')}: {variant.get('name', 'Unknown')} ===
SYSTEM: {variant.get('system_prompt', '')}
USER: {variant.get('user_prompt', '')}{prefill_line}
TCRTE: {tcrte_str}
Strengths: {'; '.join(variant.get('strengths', []))}
Best for: {variant.get('best_for', '')}""")

        variants_section = f"""
<generated_variants>
{chr(10).join(variant_blocks)}
</generated_variants>"""

    # Build techniques applied section
    techniques_section = ""
    if result and "techniques_applied" in result:
        techniques = result["techniques_applied"]
        if techniques:
            techniques_section = f"\n  <techniques_applied>{', '.join(techniques)}</techniques_applied>"

    return f"""You are APOST Assistant — expert prompt engineer in the APOST studio. You help users refine generated prompts conversationally. You have full memory of every message in this thread.

<session_context>
  <raw_prompt>{raw_prompt}</raw_prompt>
  {f'<variables>{variables}</variables>' if variables else ''}
  <provider>{provider_label}</provider>
  <model>{model_label}</model>
  <model_type>{'REASONING' if is_reasoning else 'STANDARD'}</model_type>
  <task>{task_type}</task>
  <framework>{framework}</framework>
  <complexity>{gap_data.get('complexity', 'unknown')}</complexity>{techniques_section}
</session_context>
{tcrte_section}
{answers_section}
{variants_section}

Guidelines:
- Output revised prompts in ```SYSTEM\n…``` and ```USER\n…``` blocks
- Reference prior turns in the conversation
- Explain WHY changes improve coverage or reduce over/undershoot
- Be proactive with suggestions
- Keep responses focused and actionable"""
