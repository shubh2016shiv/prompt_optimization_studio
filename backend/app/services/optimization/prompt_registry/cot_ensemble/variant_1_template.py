def build_cot_variant_1_system_prompt(*, task_description: str, reasoning_steps_text: str, demonstration_block: str, constraints_text: str, output_format: str) -> str:
    return f"""TASK: {task_description}

APPROACH - Single-Path Reasoning:
Follow these steps sequentially:
{reasoning_steps_text}

{f"DEMONSTRATION:{chr(10)}{demonstration_block}" if demonstration_block else ""}

CONSTRAINTS:
{constraints_text}

OUTPUT FORMAT: {output_format}"""