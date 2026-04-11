def build_reasoning_aware_variant_1_system_prompt(*, task: str, rules_list: str, output_format: str) -> str:
    return f"""OBJECTIVE
{task}

RULES
{rules_list}

FORMAT
{output_format}"""