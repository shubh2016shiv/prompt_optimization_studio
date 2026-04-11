TEMPLATE = """
You are performing a KERNEL rewrite.
Rewrite the prompt end-to-end, not as labels-only rearrangement.

KERNEL objective for this pass:
{objective}

KERNEL blueprint (must preserve intent):
{blueprint_json}

Original prompt:
<raw_prompt>
{raw_prompt}
</raw_prompt>

Rules:
- Rewrite prose for clarity and directness.
- Use explicit MUST and MUST NOT constraints.
- Keep scope narrow to one bounded objective.
- Include verifiable success criteria.
- Keep the structure logically ordered.
- Return only the final rewritten system prompt text.
""".strip()