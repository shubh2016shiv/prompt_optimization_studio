def build_cot_variant_3_system_prompt(*, task_description: str, reasoning_steps_text: str, demonstrations_block: str, constraints_text: str, output_format: str) -> str:
    return f"""TASK: {task_description}

APPROACH - Tri-Path Ensemble Synthesis:
You must generate THREE independent reasoning paths. Each path must approach
the problem from a fundamentally different angle. After all three, synthesise
across paths using majority-vote logic.

Path 1 - Sequential Analytical Approach:
{reasoning_steps_text}

Path 2 - Adversarial Verification:
  1. Assume Path 1's answer is WRONG. What evidence would disprove it?
  2. Check boundary conditions and edge cases.
  3. Re-derive the answer independently.

Path 3 - First-Principles Decomposition:
  1. Strip the problem to its most fundamental components.
  2. Solve each component in isolation.
  3. Reassemble the component solutions into a coherent answer.

ENSEMBLE SYNTHESIS:
Compare all three paths. For each claim, count how many paths agree.
If unanimous: high confidence - proceed.
If 2-of-3 agree: moderate confidence - explain the dissent.
If all disagree: flag uncertainty - present all three perspectives.

{f"DEMONSTRATIONS:{chr(10)}{demonstrations_block}" if demonstrations_block else ""}

CONSTRAINTS:
{constraints_text}
- Do NOT hallucinate facts outside the provided context.
- Do NOT skip any ensemble path - all three must be shown.

OUTPUT FORMAT: {output_format}"""