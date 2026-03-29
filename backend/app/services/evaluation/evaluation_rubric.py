"""
Evaluation Rubric Configuration — Single Source of Truth

All constants, weights, thresholds, and prompt templates used by the
PromptQualityCritic are defined here. This follows the same pattern used
by optimizer_configuration.py for the optimization frameworks.

┌──────────────────────────────────────────────────────────────────┐
│                    Configuration Categories                       │
├──────────────────────────────────────────────────────────────────┤
│  1. Quality Gate Threshold  — skip enhancement if above this      │
│  2. Dimension Weights       — for overall score calculation       │
│  3. Judge Model Settings    — which model evaluates prompts       │
│  4. Token Budgets           — max tokens per critique/enhance     │
│  5. Grade Boundaries        — score → letter grade mapping        │
│  6. Critique Prompt         — G-Eval rubric with CoT checklist    │
│  7. Enhancement Prompt      — targeted rewrite instructions       │
└──────────────────────────────────────────────────────────────────┘
"""

from app.config import get_settings


# ──────────────────────────────────────────────────────────────────────────────
# 1. Quality Gate Threshold
#    Variants scoring at or above this skip the enhancement pass.
#    Set at 70: variants with decent structure don't get over-engineered.
# ──────────────────────────────────────────────────────────────────────────────

QUALITY_GATE_THRESHOLD = 70

# ──────────────────────────────────────────────────────────────────────────────
# 2. Dimension Weights for Overall Score Calculation
#    Task Specificity and Constraint Completeness get 1.5× weight because
#    they have the highest correlation with downstream execution success.
# ──────────────────────────────────────────────────────────────────────────────

DIMENSION_WEIGHTS = {
    "role_clarity": 1.0,
    "task_specificity": 1.5,
    "constraint_completeness": 1.5,
    "output_format": 1.0,
    "hallucination_resistance": 1.0,
    "edge_case_handling": 1.0,
    "improvement_over_raw": 1.0,
}

# ──────────────────────────────────────────────────────────────────────────────
# 3. Judge Model Settings
#    The judge is always gpt-4.1-nano via OpenAI, regardless of the user's
#    target provider. This ensures cross-provider consistency and avoids
#    self-evaluation bias (the judge is never the model being optimised for).
# ──────────────────────────────────────────────────────────────────────────────

LLM_JUDGE_PROVIDER = "openai"
LLM_JUDGE_MODEL = get_settings().openai_subtask_model

# ──────────────────────────────────────────────────────────────────────────────
# 4. Token Budgets
# ──────────────────────────────────────────────────────────────────────────────

MAX_TOKENS_CRITIQUE = 1024      # For the critique/evaluation response
MAX_TOKENS_ENHANCEMENT = 2048   # For the enhanced prompt rewrite

# ──────────────────────────────────────────────────────────────────────────────
# 5. Grade Boundaries — score → letter grade
# ──────────────────────────────────────────────────────────────────────────────

GRADE_BOUNDARIES = [
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (50, "D"),
    (0, "F"),
]


def score_to_grade(score: int) -> str:
    """Convert a 0–100 overall score to a letter grade (A/B/C/D/F)."""
    for threshold, grade in GRADE_BOUNDARIES:
        if score >= threshold:
            return grade
    return "F"


# ──────────────────────────────────────────────────────────────────────────────
# 6. Critique Prompt — G-Eval Rubric with CoT Binary Checklist
#
#    This is the heart of the evaluation: the judge is forced to reason
#    through binary yes/no questions for each dimension BEFORE assigning
#    a score. This G-Eval decomposition has ~40% higher human-alignment
#    than direct "rate 1-100" scoring.
#
#    The prompt receives two placeholders:
#      {raw_prompt}     — the user's original, unoptimised prompt
#      {system_prompt}  — the optimised variant to evaluate
# ──────────────────────────────────────────────────────────────────────────────

CRITIQUE_SYSTEM_PROMPT = """You are a Prompt Quality Evaluator. You assess the quality of LLM system prompts.
You must be STRICT and OBJECTIVE. Return ONLY valid JSON matching the exact schema below."""

CRITIQUE_USER_PROMPT_TEMPLATE = """Evaluate this OPTIMISED system prompt against the ORIGINAL raw prompt.

=== ORIGINAL RAW PROMPT (user wrote this) ===
{raw_prompt}

=== OPTIMISED SYSTEM PROMPT (to evaluate) ===
{system_prompt}

TASK: Evaluate the optimised prompt on EXACTLY 7 dimensions. For each dimension, answer the binary checklist questions, then assign a score 0-100.

DIMENSION 1: role_clarity
- Does it define WHO the model is? (yes/no)
- Does it state expertise level or domain? (yes/no)
- Is the persona scope bounded (what it should NOT claim to be)? (yes/no)
Score guide: 0 = no role at all, 50 = basic role, 80 = role + expertise, 100 = role + expertise + scope bounds

DIMENSION 2: task_specificity
- Is the task unambiguous (only one interpretation)? (yes/no)
- Are measurable success criteria stated? (yes/no)
- Is the task scope bounded (what is NOT in scope)? (yes/no)
Score guide: 0 = vague task, 50 = clear task, 80 = clear + criteria, 100 = clear + criteria + scope

DIMENSION 3: constraint_completeness
- Are hard constraints explicit (format, length, forbidden content)? (yes/no)
- Are negative constraints stated (what NOT to do)? (yes/no)
- Are constraints enforceable (machine-verifiable, not subjective)? (yes/no)
Score guide: 0 = no constraints, 50 = some constraints, 80 = positive + negative, 100 = all verifiable

DIMENSION 4: output_format
- Is the exact output structure specified (JSON schema, headers, etc.)? (yes/no)
- Are field names/types defined? (yes/no)
- Is an output example provided or clearly implied? (yes/no)
Score guide: 0 = no format, 50 = general format, 80 = specific structure, 100 = schema + example

DIMENSION 5: hallucination_resistance
- Does it instruct to use ONLY provided context? (yes/no)
- Does it say to express uncertainty or say "I don't know"? (yes/no)
- Does it forbid inventing facts or data? (yes/no)
Score guide: 0 = no guards, 50 = one guard, 80 = two guards, 100 = all three

DIMENSION 6: edge_case_handling
- Does it define behaviour for missing or incomplete input? (yes/no)
- Does it define behaviour for ambiguous requests? (yes/no)
- Does it define a fallback/error format? (yes/no)
Score guide: 0 = no handling, 50 = one case, 80 = two cases, 100 = all three

DIMENSION 7: improvement_over_raw
- Is the structure objectively better than the raw prompt? (yes/no)
- Does it add specificity that the raw prompt lacked? (yes/no)
- Does it preserve the user's original intent without distortion? (yes/no)
Score guide: 0 = worse than raw, 50 = marginal improvement, 80 = clear improvement, 100 = transformative

Return ONLY this JSON (no markdown fences, no commentary):
{{
  "reasoning": "Step-by-step checklist evaluation for each dimension...",
  "dimensions": {{
    "role_clarity": <0-100>,
    "task_specificity": <0-100>,
    "constraint_completeness": <0-100>,
    "output_format": <0-100>,
    "hallucination_resistance": <0-100>,
    "edge_case_handling": <0-100>,
    "improvement_over_raw": <0-100>
  }},
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["specific weakness 1", "specific weakness 2"],
  "enhancement_suggestions": ["add X to address weakness 1", "add Y to address weakness 2"]
}}"""


# ──────────────────────────────────────────────────────────────────────────────
# 7. Enhancement Prompt — Targeted Rewrite Based on Critique
#
#    This prompt takes the original system prompt and the specific weaknesses
#    identified by the critic, then produces a surgically improved version.
#    Key constraint: "Add ONLY what is missing. Do NOT restructure."
#
#    Placeholders:
#      {system_prompt}  — the current system prompt to improve
#      {weaknesses}     — bulleted list of specific weaknesses
#      {suggestions}    — bulleted list of enhancement suggestions
#      {task_type}      — the task type for context
# ──────────────────────────────────────────────────────────────────────────────

ENHANCEMENT_SYSTEM_PROMPT = """You are a Prompt Enhancement Specialist. You surgically improve system prompts by addressing specific weaknesses.
You must preserve the EXISTING structure and add ONLY what is needed. Do NOT restructure or rewrite from scratch."""

ENHANCEMENT_USER_PROMPT_TEMPLATE = """Improve this system prompt by addressing EXACTLY the weaknesses listed below.

=== CURRENT SYSTEM PROMPT ===
{system_prompt}

=== WEAKNESSES TO FIX ===
{weaknesses}

=== SUGGESTED IMPROVEMENTS ===
{suggestions}

=== TASK TYPE ===
{task_type}

RULES:
1. Preserve ALL existing content. Do not remove or rephrase working sections.
2. ADD the missing elements identified in the weaknesses list.
3. Place new content in the most logical position within the existing structure.
4. Keep the same formatting style (markdown headers, XML tags, etc.) as the original.
5. Do NOT add generic filler. Every addition must address a specific weakness.

Return ONLY the improved system prompt text. No explanations, no markdown fences."""
