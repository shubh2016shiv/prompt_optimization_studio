TEMPLATE = """
Generate {count} few-shot examples for the following task type: "{task_type}".
Each example should be a prompt optimization transformation that includes:
1. An original raw prompt (before optimization)
2. The optimized system prompt (after optimization)
3. A step-by-step reasoning trace explaining each optimization decision

The examples should be realistic, domain-appropriate, and demonstrate clear
reasoning about WHY each change was made.

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