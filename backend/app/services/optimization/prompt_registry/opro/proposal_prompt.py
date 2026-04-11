TEMPLATE = """
You are running OPRO (Optimization by PROmpting) for system prompt optimization.
Your goal is to propose full replacement SYSTEM PROMPTS that achieve higher
empirical task success scores on the provided evaluation examples.

ORIGINAL RAW PROMPT:
{raw_prompt}

TASK TYPE: {task_type}
TARGET MODEL: {model_label}

EVALUATION EXAMPLES:
{evaluation_examples}

PROMPT-SCORE TRAJECTORY:
The following prior prompts are sorted in ascending score order. Higher score is
better. Learn from the best prompts while still exploring meaningfully different
wording and structure.
{trajectory}

Generate exactly {candidate_count} new candidate system prompts.
Rules:
- Each candidate must be a complete system prompt, not a short instruction.
- Candidates must differ from prior prompts in the trajectory.
- Preserve task intent from the raw prompt.
- Include output constraints and failure-mode guards when useful.
- Do not mention OPRO, scores, or the optimization process in the candidate.

Return ONLY valid JSON:
{{
  "candidates": [
    {{"system_prompt": "complete prompt", "rationale": "why this should score better"}}
  ]
}}
""".strip()