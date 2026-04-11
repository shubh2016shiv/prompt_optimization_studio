TEMPLATE = """
You are performing a CREATE rewrite.
Return a complete rewritten system prompt, not fragments.

Objective for this pass:
{objective}

CREATE blueprint:
{blueprint_json}

Original prompt:
<raw_prompt>
{raw_prompt}
</raw_prompt>

Rules:
- Preserve intent while rewriting for clarity and enforceability.
- Keep CREATE structure explicit: Character, Request, Examples, Adjustments, Type of Output, Extras.
- Convert adjustments into executable MUST and MUST NOT rules.
- Keep one bounded objective and avoid speculative scope expansion.
- Include verification checks in actionable language.
- Return only the final rewritten system prompt text.
""".strip()