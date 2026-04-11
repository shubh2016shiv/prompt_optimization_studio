TEMPLATE = """
You are a CREATE framework architect.
Extract stable CREATE anchors from the user's prompt.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY valid JSON:
{{
  "character": "role/persona the assistant should adopt",
  "request": "single bounded objective",
  "examples": ["example context or references"],
  "adjustments": ["hard constraints and adjustments"],
  "type_of_output": "required output format",
  "extras": ["safety, edge-case, or reliability directives"],
  "forbidden_behaviors": ["explicit must-not behaviors"],
  "verification_checks": ["verifiable completion checks"]
}}
""".strip()