TEMPLATE = """\
Rewrite this prompt to SEPARATE the core task/context narrative from the
constraints.

Currently, the constraints and rules are tangled up with the background
information and the task request. I want you to extract ALL constraints out
of the narrative, leaving only a clean, pure statement of Context and Task.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY valid JSON:
{{
  "task_narrative": "The clean task instruction with constraints removed",
  "context_narrative": "The clean background context with constraints removed"
}}
"""