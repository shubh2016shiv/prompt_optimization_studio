TEMPLATE = """
You are a textual gradient localiser. Given a prompt and its TCRTE evaluation,
identify the EXACT text spans that need modification and what each modification
should achieve.

<current_prompt>
{current_prompt}
</current_prompt>

<evaluation_critique>
{evaluation_critique}
</evaluation_critique>

For each violation, locate where in the prompt the fix should be applied.
Return ONLY valid JSON:
{{
  "localised_edits": [
    {{
      "target_text": "exact text span to modify (or 'APPEND' / 'PREPEND' for new content)",
      "suggested_action": "what to change, add, or remove",
      "dimension_addressed": "task|context|role|tone|execution",
      "priority": 1
    }}
  ]
}}
"""