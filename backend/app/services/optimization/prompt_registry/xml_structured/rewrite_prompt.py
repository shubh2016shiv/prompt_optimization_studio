TEMPLATE = """
You are rewriting a system prompt with XML semantic bounding.
Return a complete rewritten system prompt, not fragments.

Objective for this pass:
{objective}

Ontology blueprint:
{blueprint_json}

Original prompt:
<raw_prompt>
{raw_prompt}
</raw_prompt>

Rules:
- Keep original intent while rewriting prose for clarity.
- Encode hard constraints using explicit MUST and MUST NOT statements.
- Build an ontological hierarchy where higher-priority nodes appear earlier.
- Use explicit XML boundaries for directive zones and output contract.
- Include anti-hallucination boundaries and uncertainty behavior.
- Keep scope narrow to one primary objective.
- Return only the rewritten system prompt text.
""".strip()