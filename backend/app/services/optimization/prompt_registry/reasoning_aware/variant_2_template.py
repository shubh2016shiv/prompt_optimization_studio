def build_reasoning_aware_variant_2_system_prompt(*, task: str, rules_list: str, output_format: str) -> str:
    return f"""### OBJECTIVE DECLARATION
{task}

### FORMATTING CONTRACT (REQUIRED)
{output_format}

### HARD CONSTRAINTS
{rules_list}
"""