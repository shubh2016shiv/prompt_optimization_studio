TEMPLATE = """
Parse the raw prompt into a structured prompt graph.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY valid JSON:
{{
  "instruction": "core instruction",
  "context_blocks": ["context block 1", "context block 2"],
  "rules": ["rule 1", "rule 2"],
  "few_shot": ["few-shot or exemplar block"],
  "output_format": "required output format and schema guidance"
}}
""".strip()