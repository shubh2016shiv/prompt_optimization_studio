def build_reasoning_aware_variant_3_system_prompt(*, task: str, rules_list: str, output_format: str) -> str:
    return f"""# EXECUTION MANDATE
{task}

## BOUNDARY CONSTRAINTS
{rules_list}
- Adhere absolutely to the formatting schema.
- You do not need to explain your reasoning or show a chain of thought. You must proceed directly to emitting the exact final Output Format.

## OUTPUT FORMAT
{output_format}"""