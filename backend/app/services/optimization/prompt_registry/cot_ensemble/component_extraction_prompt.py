TEMPLATE = """
Analyze the following prompt and extract its core components for a Chain-of-Thought
ensemble optimization. Focus on identifying the reasoning requirements.

Extract:
1. "task": The primary objective that requires step-by-step reasoning.
2. "reasoning_steps": A list of the sequential reasoning steps needed to complete the task.
3. "constraints": Hard rules the model must follow.
4. "output_format": The expected output structure.
5. "critical_context": The most important context that must not be lost (for CoRe injection).

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY valid JSON matching this schema:
{{
  "task": "string",
  "reasoning_steps": ["step1", "step2", ...],
  "constraints": ["constraint1", ...],
  "output_format": "string",
  "critical_context": "string"
}}
"""