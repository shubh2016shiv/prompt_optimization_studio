TEMPLATE = """
You are performing a Progressive Disclosure rewrite.
Return a full rewritten system prompt, not fragments.

Objective for this pass:
{objective}

Layered blueprint:
{blueprint_json}

Original prompt:
<raw_prompt>
{raw_prompt}
</raw_prompt>

Rules:
- Preserve intent while rewriting for precise activation and execution behavior.
- Keep three layers explicit: Discovery, Activation, Execution.
- Activation rules must be condition -> action statements.
- Execution logic must be ordered and deterministic.
- Include safety boundaries and failure-mode prevention.
- Keep scope narrow to the intended workflow.
- Return only the final rewritten system prompt text.
""".strip()