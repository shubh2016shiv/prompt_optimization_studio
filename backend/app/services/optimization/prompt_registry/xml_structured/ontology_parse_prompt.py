TEMPLATE = """
You are an ontology architect for instruction systems.
Extract the semantic structure of the prompt so it can be rewritten into robust XML bounds.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY valid JSON:
{{
  "objective": "single bounded objective",
  "instruction_hierarchy": [
    {{
      "node": "instruction block label",
      "purpose": "why this block exists",
      "depends_on": ["other node labels"],
      "priority": "critical|high|medium|low"
    }}
  ],
  "hard_constraints": ["non-negotiable constraints"],
  "soft_preferences": ["nice-to-have preferences"],
  "required_outputs": {{
    "format": "output format",
    "schema_notes": "required fields or schema notes"
  }},
  "safety_bounds": ["hallucination and boundary constraints"]
}}
""".strip()