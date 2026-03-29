"""
Central Optimizer Configuration — Single Source of Truth

All tunable constants used across the 8 APOST optimization frameworks are
defined here. This prevents magic numbers scattered across individual
optimizer files and makes it trivial to adjust behaviour globally.

┌────────────────────────────────────────────────────────────────────┐
│                   Configuration Categories                         │
├────────────────────────────────────────────────────────────────────┤
│  1. LLM Model Selection     — which model handles sub-tasks        │
│  2. Token Budgets            — max output per call type            │
│  3. TextGrad Iteration       — loops, temperature per phase        │
│  4. CoRe Repetition          — min/max k bounds                    │
│  5. Prefill Mapping          — task_type → first tokens            │
│  6. Provider Format Rules    — XML / Markdown / Declarative        │
│  7. TCRTE Dimension Weights  — for overall score calculation       │
└────────────────────────────────────────────────────────────────────┘

Usage:
    from app.services.optimization.optimizer_configuration import OPTIMIZER_CONFIG
    model = OPTIMIZER_CONFIG["llm_sub_task_model"]
"""

from app.config import get_settings

# ──────────────────────────────────────────────────────────────────────────────
# 1. LLM Model Selection for Internal Sub-Tasks
#    These are the cheap/fast models used for component extraction, scoring,
#    synthetic example generation, etc. They are NOT the user's target model.
#    Canonical values live in app.config.Settings (openai_subtask_model).
# ──────────────────────────────────────────────────────────────────────────────

LLM_SUB_TASK_PROVIDER = "openai"
LLM_SUB_TASK_MODEL = get_settings().openai_subtask_model

# ──────────────────────────────────────────────────────────────────────────────
# 2. Token Budgets Per Call Type
# ──────────────────────────────────────────────────────────────────────────────

MAX_TOKENS_COMPONENT_EXTRACTION = 2048    # For parsing raw prompts into structured components
MAX_TOKENS_SYNTHETIC_EXAMPLE_GENERATION = 1500  # For generating few-shot examples when kNN unavailable
MAX_TOKENS_TEXTGRAD_EVALUATION = 1200     # For TextGrad evaluator critique per iteration
MAX_TOKENS_TEXTGRAD_GRADIENT = 800        # For TextGrad gradient localisation per iteration
MAX_TOKENS_TEXTGRAD_UPDATE = 2048         # For TextGrad prompt rewrite per iteration
MAX_TOKENS_TCRTE_DIMENSION_FILL = 1500   # For filling missing TCRTE dimensions
MAX_TOKENS_VARIANT_SCORE_ESTIMATION = 350  # For scoring a generated variant

# ──────────────────────────────────────────────────────────────────────────────
# 3. TextGrad Iteration Configuration
# ──────────────────────────────────────────────────────────────────────────────

TEXTGRAD_DEFAULT_ITERATION_COUNT = 3       # Number of evaluate→critique→rewrite cycles
TEXTGRAD_EVALUATION_TEMPERATURE = 0.0      # Greedy for consistent critiques
TEXTGRAD_UPDATE_TEMPERATURE = 0.3          # Slight creativity for rewrites

# ──────────────────────────────────────────────────────────────────────────────
# 4. CoRe (Context Repetition) Bounds
#    k=2 is minimum (start + end). k=5 is max (beyond this, fixation occurs).
# ──────────────────────────────────────────────────────────────────────────────

CORE_MINIMUM_REPETITION_COUNT = 2
CORE_MAXIMUM_REPETITION_COUNT = 5

# ──────────────────────────────────────────────────────────────────────────────
# 5. Claude Prefill Mapping — task_type → ideal first tokens of assistant turn
#    Reference: APOST_v4_Documentation.md §5.3
# ──────────────────────────────────────────────────────────────────────────────

PREFILL_SUGGESTION_BY_TASK_TYPE = {
    "extraction": "{",
    "qa": "{",
    "routing": "{",
    "analysis": "## ",
    "coding": "```",
    "planning": "## ",
    "reasoning": "<thinking>",
    "creative": "",
}

# Default if task_type is not in the mapping
PREFILL_DEFAULT = "{"

# ──────────────────────────────────────────────────────────────────────────────
# 6. Provider-Specific Formatting Rules
#    Reference: APOST_v4_Documentation.md §6
# ──────────────────────────────────────────────────────────────────────────────

PROVIDER_FORMATTING_RULES = {
    "anthropic": {
        "delimiter_style": "xml",
        "section_header_format": "<{name}>\n{content}\n</{name}>",
        "constraint_position": "primacy",  # Constraints go first (top)
        "supports_prefill": True,
        "supports_restate_critical": True,
    },
    "openai": {
        "delimiter_style": "markdown",
        "section_header_format": "### {name}\n{content}",
        "constraint_position": "primacy",
        "supports_prefill": False,
        "supports_restate_critical": True,
    },
    "google": {
        "delimiter_style": "xml",
        "section_header_format": "<{name}>\n{content}\n</{name}>",
        "constraint_position": "primacy",
        "supports_prefill": False,
        "supports_restate_critical": True,
    },
}

PROVIDER_FORMATTING_DEFAULT = PROVIDER_FORMATTING_RULES["openai"]

# ──────────────────────────────────────────────────────────────────────────────
# 7. TCRTE Dimension Weights for Overall Score Calculation
#    Task and Execution get higher weights per APOST_v4_Documentation.md §3.3
#    Canonical weights: app.config.Settings (tcrte_weight_*).
# ──────────────────────────────────────────────────────────────────────────────

TCRTE_DIMENSION_WEIGHTS = get_settings().tcrte_dimension_weights

# ──────────────────────────────────────────────────────────────────────────────
# 8. System Prompt for Component Extraction (shared across multiple frameworks)
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_FOR_JSON_EXTRACTION = "You are a precision text parser. Return ONLY valid JSON matching the specified schema. No markdown fences, no explanation."

# ──────────────────────────────────────────────────────────────────────────────
# Aggregated Config Dict (for backwards compatibility and easy import)
# ──────────────────────────────────────────────────────────────────────────────

OPTIMIZER_CONFIG = {
    "llm_sub_task_provider": LLM_SUB_TASK_PROVIDER,
    "llm_sub_task_model": LLM_SUB_TASK_MODEL,
    "max_tokens_component_extraction": MAX_TOKENS_COMPONENT_EXTRACTION,
    "max_tokens_synthetic_example_generation": MAX_TOKENS_SYNTHETIC_EXAMPLE_GENERATION,
    "max_tokens_textgrad_evaluation": MAX_TOKENS_TEXTGRAD_EVALUATION,
    "max_tokens_textgrad_gradient": MAX_TOKENS_TEXTGRAD_GRADIENT,
    "max_tokens_textgrad_update": MAX_TOKENS_TEXTGRAD_UPDATE,
    "max_tokens_tcrte_dimension_fill": MAX_TOKENS_TCRTE_DIMENSION_FILL,
    "max_tokens_variant_score_estimation": MAX_TOKENS_VARIANT_SCORE_ESTIMATION,
    "textgrad_default_iteration_count": TEXTGRAD_DEFAULT_ITERATION_COUNT,
    "textgrad_evaluation_temperature": TEXTGRAD_EVALUATION_TEMPERATURE,
    "textgrad_update_temperature": TEXTGRAD_UPDATE_TEMPERATURE,
    "core_minimum_repetition_count": CORE_MINIMUM_REPETITION_COUNT,
    "core_maximum_repetition_count": CORE_MAXIMUM_REPETITION_COUNT,
    "prefill_suggestion_by_task_type": PREFILL_SUGGESTION_BY_TASK_TYPE,
    "prefill_default": PREFILL_DEFAULT,
    "provider_formatting_rules": PROVIDER_FORMATTING_RULES,
    "tcrte_dimension_weights": TCRTE_DIMENSION_WEIGHTS,
    "system_prompt_for_json_extraction": SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
}
