TEMPLATE = """
You are a KERNEL decomposition specialist.
Extract stable optimization anchors from the prompt.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY valid JSON:
{{
  "task": "single bounded objective",
  "context": "required grounding context",
  "positive_constraints": ["must-do constraints"],
  "negative_constraints": ["must-not constraints"],
  "success_criteria": ["verifiable completion checks"],
  "output_format": "required output format/schema"
}}
""".strip()