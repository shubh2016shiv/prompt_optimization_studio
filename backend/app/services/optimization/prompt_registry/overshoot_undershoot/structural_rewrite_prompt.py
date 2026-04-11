TEMPLATE = """\
You are a prompt engineering specialist. Rewrite the user's raw prompt to add
clear structural improvements that prevent common generation failures.

<raw_prompt>
{raw_prompt}
</raw_prompt>

<failure_analysis>
{failure_analysis}
</failure_analysis>

Rewrite the prompt with the following improvements:
1. Add a clear, singular TASK statement with measurable success criteria.
2. Add explicit SCOPE boundaries defining what is in-scope and out-of-scope.
3. Add an OUTPUT FORMAT specification with field definitions where applicable.
4. Preserve ALL original intent - do not remove any information the user provided.

Return ONLY valid JSON:
{{
  "task_statement": "Clear singular imperative for the model",
  "scope_boundaries": "Explicit in-scope / out-of-scope definition",
  "original_context": "All original context from the raw prompt, preserved verbatim",
  "output_format": "Explicit output structure specification",
  "constraints": ["constraint1", "constraint2"]
}}
"""