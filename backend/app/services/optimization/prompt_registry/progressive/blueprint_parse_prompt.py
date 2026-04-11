TEMPLATE = """
You are a systems architect for Progressive Disclosure prompting.
Extract layered execution anchors from the user's prompt.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY valid JSON:
{{
  "discovery_metadata": ["capabilities, tools, and context visibility"],
  "activation_rules": [
    {{
      "trigger": "condition that activates behavior",
      "action": "what should be executed",
      "priority": "critical|high|medium|low"
    }}
  ],
  "execution_logic": ["ordered procedural steps"],
  "output_format": "required output schema or format",
  "safety_bounds": ["guardrails and out-of-scope handling"],
  "failure_modes": ["common failure modes to prevent"]
}}
""".strip()