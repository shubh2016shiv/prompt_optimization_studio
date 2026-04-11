def build_cot_variant_2_system_prompt(*, task_description: str, reasoning_steps_text: str, demonstrations_block: str, constraints_text: str, output_format: str) -> str:
    return f"""TASK: {task_description}

APPROACH - Dual-Path Reasoning with Self-Check:
You must generate TWO independent reasoning paths for this task.
For each path, show your working step by step.

Path 1 - Analytical Approach:
{reasoning_steps_text}

Path 2 - Verification Approach:
  1. Re-read the original input from a different angle.
  2. Challenge any assumptions from Path 1.
  3. Identify potential errors or oversights.

SELF-CHECK:
After both paths, compare results. If they agree, proceed with confidence.
If they disagree, explain the discrepancy and choose the more robust answer.

{f"DEMONSTRATIONS:{chr(10)}{demonstrations_block}" if demonstrations_block else ""}

CONSTRAINTS:
{constraints_text}

OUTPUT FORMAT: {output_format}"""