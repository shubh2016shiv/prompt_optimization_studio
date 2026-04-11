TEMPLATE = """\
You are a constraint analysis engineer. Your job is to forensically extract
and categorise EVERY constraint, rule, boundary, or format requirement
hidden within this raw prompt.

Look for:
- Explicit constraints ("Must be under 500 words", "Return JSON")
- Implicit constraints ("Write a haiku" implies 5-7-5 syllables)
- Negative constraints ("Do not mention X", "Avoid bullet points")
- Stylistic constraints ("Use British spelling", "Professional tone")

<raw_prompt>
{raw_prompt}
</raw_prompt>

Also, evaluate if the prompt has high "Constraint Density" (many interwoven rules)
and if there are any conflicting constraints (e.g., "Explain in detail" vs "Keep under 50 words").

Return ONLY valid JSON:
{{
  "hard_constraints": [
    {{
      "rule": "The exact constraint rule",
      "criticality": "high|medium|low",
      "category": "format|length|content|style|negative"
    }}
  ],
  "soft_preferences": [
    "List of 'should/prefer' guidelines"
  ],
  "missing_implicit_constraints": [
    "Constraints that are logically required by the task but were NOT stated by the user"
  ],
  "conflicts": [
    "Description of any contradictory constraints found"
  ],
  "constraint_density": "high|medium|low",
  "summary": "Brief summary of the constraint landscape"
}}
"""