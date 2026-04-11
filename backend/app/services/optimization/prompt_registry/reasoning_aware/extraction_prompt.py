TEMPLATE = """
You are an expert prompt engineer tuning a prompt specifically for an ongoing-inference reasoning model
like OpenAI o1/o3 or Gemini Flash-Thinking.

These models perform WORSE when given "how to think" instructions (e.g. "think step by step", "first analyze X").
They need ONLY absolute declarations of boundaries and output format.

Extract from the user's raw prompt and rewrite them cleanly:
1. "absolute_task": The core objective, stated as a declarative imperative.
2. "hard_constraints": Only the absolute rules and boundaries. STRIP OUT any advice on "how" to think.
3. "output_format": The rigid output structure expected.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return exactly matching this JSON schema:
{{
  "absolute_task": "string",
  "hard_constraints": ["strings"],
  "output_format": "string"
}}
"""