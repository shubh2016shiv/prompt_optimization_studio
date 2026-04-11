def build_tcrte_variant_3_system_prompt(*, role_section: str, task_section: str, context_section: str, tone_section: str, execution_section: str, constraints_text: str) -> str:
    return f"""=================
[R] ROLE DEFINITION
=================
{role_section}
You must strictly maintain this persona for the duration of the request.

=================
[T] TASK MANDATE
=================
{task_section}

=================
[C] CONTEXT GROUNDING
=================
{context_section}

=================
[T] TONE SPECIFICATION
=================
{tone_section}

=================
[E] EXECUTION CONSTRAINTS
=================
{execution_section}

=================
HARD CONSTRAINTS
=================
{constraints_text}
- Do NOT hallucinate facts outside the provided context.
- Do NOT append conversational preamble or postamble.
- Validate all output against the execution schema before responding."""