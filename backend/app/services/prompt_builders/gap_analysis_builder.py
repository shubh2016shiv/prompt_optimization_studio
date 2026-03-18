"""
Gap analysis prompt builder.

Constructs the meta-prompt for TCRTE coverage auditing.
"""

from typing import Optional

from app.models.providers import PROVIDERS


def build_gap_analysis_prompt(
    raw_prompt: str,
    input_variables: Optional[str],
    task_type: str,
    provider: str,
    model_label: str,
    is_reasoning_model: bool,
) -> str:
    """
    Build the gap analysis prompt for TCRTE coverage auditing.

    Args:
        raw_prompt: The raw prompt to analyze.
        input_variables: Optional declared input variables.
        task_type: The type of task (planning, reasoning, etc.).
        provider: The LLM provider key (anthropic, openai, google).
        model_label: The target model's display label.
        is_reasoning_model: Whether the target is a reasoning model.

    Returns:
        The complete meta-prompt for gap analysis.
    """
    provider_label = PROVIDERS.get(provider, {}).get("label", provider)
    model_type = "REASONING" if is_reasoning_model else "STANDARD"

    variables_line = (
        f"Input variables declared: {input_variables}"
        if input_variables and input_variables.strip()
        else "No input variables declared."
    )

    return f"""You are an expert prompt engineer. Perform a rapid TCRTE coverage audit on this raw prompt.

TCRTE Dimensions:
- Task: Is the core objective specific, actionable, measurable?
- Context: Is background information, domain knowledge, or data provided?
- Role: Is a model persona/expertise level specified?
- Tone: Are style, register, or audience requirements stated?
- Execution: Are output format, length, constraints, and prohibitions defined?

Target model: {provider_label} {model_label} ({model_type})
Task type: {task_type}
{variables_line}

Raw prompt to audit:
\"\"\"
{raw_prompt}
\"\"\"

Generate a coverage analysis. For each weak/missing dimension, create ONE targeted clarifying question that will unlock the most value. Keep questions concise and practical.

Respond ONLY as valid JSON — no markdown fences:
{{
  "tcrte": {{
    "task":      {{"score":0,"status":"good|weak|missing","note":"short note"}},
    "context":   {{"score":0,"status":"good|weak|missing","note":"short note"}},
    "role":      {{"score":0,"status":"good|weak|missing","note":"short note"}},
    "tone":      {{"score":0,"status":"good|weak|missing","note":"short note"}},
    "execution": {{"score":0,"status":"good|weak|missing","note":"short note"}}
  }},
  "overall_score": 0,
  "complexity": "simple|medium|complex",
  "complexity_reason": "one sentence why",
  "recommended_techniques": ["list of: CoRe|RAL-Writer|Prefill|CoT-Ensemble|XML-Bounding|Progressive-Disclosure"],
  "questions": [
    {{
      "id": "q1",
      "dimension": "task|context|role|tone|execution",
      "question": "Specific question text",
      "placeholder": "example answer hint",
      "importance": "critical|recommended|optional"
    }}
  ],
  "auto_enrichments": ["list of automatic techniques that will be applied"]
}}"""
