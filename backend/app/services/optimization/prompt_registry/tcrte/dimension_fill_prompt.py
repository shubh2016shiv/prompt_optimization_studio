TEMPLATE = """
You are an expert prompt architect. The user's raw prompt is UNDERSPECIFIED
and needs structural repair across the 5 TCRTE dimensions.

Here is the raw prompt:
<raw_prompt>
{raw_prompt}
</raw_prompt>

{dimension_repair_instructions}

Rewrite the prompt with explicit sections for ALL 5 TCRTE dimensions.
For dimensions marked as MISSING or WEAK, you MUST generate substantial content.
For dimensions marked as GOOD, preserve the original content.

{user_provided_answers_block}

Return ONLY valid JSON matching this schema:
{{
  "task_section": "Explicit task definition with measurable outputs and success criteria",
  "context_section": "Domain, data sources, temporal scope, grounding information",
  "role_section": "Expert persona with seniority and behavioural calibration",
  "tone_section": "Formality register, audience type, hedging rules",
  "execution_section": "Output format, length constraints, prohibited content",
  "constraints": ["list of identified constraints"],
  "critical_context_for_core": "The single most important context element"
}}
"""