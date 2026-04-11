TEMPLATE = """
Generate {count} few-shot examples for the following task type: "{task_type}".

These examples MUST be domain-appropriate for optimizing prompts similar to this target prompt:

=== TARGET PROMPT (for domain + format grounding) ===
{target_raw_prompt}
=== END TARGET PROMPT ===

Each example should be a prompt optimization transformation that includes:
1. An original raw prompt (before optimization)
2. The optimized system prompt (after optimization)
3. A step-by-step reasoning trace explaining each optimization decision

The examples should be realistic, domain-appropriate, and demonstrate clear
reasoning about WHY each change was made.

Keep the examples compact and focused. Prefer the same output format family
as the target prompt (e.g., JSON schema, headings, strict constraints) so the
demonstrations transfer cleanly.

Return ONLY valid JSON:
{{
  "examples": [
    {{
      "raw_prompt": "the original prompt text",
      "optimized_system_prompt": "the improved prompt text",
      "reasoning_trace": "Step 1: ... Step 2: ... Step 3: ..."
    }}
  ]
}}
"""
