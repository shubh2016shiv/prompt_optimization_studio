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
MAX_TOKENS_FAILURE_MODE_ANALYSIS = 1500   # For overshoot/undershoot risk analysis
MAX_TOKENS_CORE_CRITICALITY_ANALYSIS = 1200 # For CoRe attention risk analysis
MAX_TOKENS_RAL_CONSTRAINT_EXTRACTION = 1000 # For RAL-Writer constraint separation
MAX_TOKENS_OPRO_PROPOSAL = 2500       # For OPRO trajectory-based candidate proposal
MAX_TOKENS_SAMMO_STRUCTURAL_PARSE = 1500  # For SAMMO graph parsing and mutation calls
MAX_TOKENS_KERNEL_REWRITE = 2200      # For deep KERNEL rewrite passes
MAX_TOKENS_XML_REWRITE = 2200         # For ontology-aware XML rewrite passes
MAX_TOKENS_CREATE_REWRITE = 2200      # For deep CREATE rewrite passes
MAX_TOKENS_PROGRESSIVE_REWRITE = 2200 # For deep Progressive Disclosure rewrite passes

# ──────────────────────────────────────────────────────────────────────────────
# 3. TextGrad Iteration Configuration
# ──────────────────────────────────────────────────────────────────────────────

TEXTGRAD_DEFAULT_ITERATION_COUNT = 3       # Number of evaluate→critique→rewrite cycles
TEXTGRAD_EVALUATION_TEMPERATURE = 0.0      # Greedy for consistent critiques
TEXTGRAD_UPDATE_TEMPERATURE = 0.3          # Slight creativity for rewrites

# OPRO: Optimization by PROmpting. Defaults are deliberately bounded because
# each proposed prompt is empirically evaluated against user examples.
OPRO_DEFAULT_ITERATION_COUNT = 3
OPRO_CANDIDATES_PER_ITERATION = 2
OPRO_TRAJECTORY_KEEP_TOP = 20
OPRO_EXEMPLARS_IN_META_PROMPT = 3
OPRO_MAX_TRAINING_CASES = 12
OPRO_PROPOSAL_TEMPERATURE = 0.8

# SAMMO: Structure-Aware Multi-Objective Optimization.
SAMMO_MIN_TCRTE_THRESHOLD = 60
SAMMO_TOKEN_WEIGHT = 0.30
SAMMO_TCRTE_WEIGHT = 0.70

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
    "max_tokens_failure_mode_analysis": MAX_TOKENS_FAILURE_MODE_ANALYSIS,
    "max_tokens_core_criticality_analysis": MAX_TOKENS_CORE_CRITICALITY_ANALYSIS,
    "max_tokens_ral_constraint_extraction": MAX_TOKENS_RAL_CONSTRAINT_EXTRACTION,
    "max_tokens_opro_proposal": MAX_TOKENS_OPRO_PROPOSAL,
    "max_tokens_sammo_structural_parse": MAX_TOKENS_SAMMO_STRUCTURAL_PARSE,
    "max_tokens_kernel_rewrite": MAX_TOKENS_KERNEL_REWRITE,
    "max_tokens_xml_rewrite": MAX_TOKENS_XML_REWRITE,
    "max_tokens_create_rewrite": MAX_TOKENS_CREATE_REWRITE,
    "max_tokens_progressive_rewrite": MAX_TOKENS_PROGRESSIVE_REWRITE,
    "textgrad_default_iteration_count": TEXTGRAD_DEFAULT_ITERATION_COUNT,
    "textgrad_evaluation_temperature": TEXTGRAD_EVALUATION_TEMPERATURE,
    "textgrad_update_temperature": TEXTGRAD_UPDATE_TEMPERATURE,
    "opro_default_iteration_count": OPRO_DEFAULT_ITERATION_COUNT,
    "opro_candidates_per_iteration": OPRO_CANDIDATES_PER_ITERATION,
    "opro_trajectory_keep_top": OPRO_TRAJECTORY_KEEP_TOP,
    "opro_exemplars_in_meta_prompt": OPRO_EXEMPLARS_IN_META_PROMPT,
    "opro_max_training_cases": OPRO_MAX_TRAINING_CASES,
    "opro_proposal_temperature": OPRO_PROPOSAL_TEMPERATURE,
    "sammo_min_tcrte_threshold": SAMMO_MIN_TCRTE_THRESHOLD,
    "sammo_token_weight": SAMMO_TOKEN_WEIGHT,
    "sammo_tcrte_weight": SAMMO_TCRTE_WEIGHT,
    "core_minimum_repetition_count": CORE_MINIMUM_REPETITION_COUNT,
    "core_maximum_repetition_count": CORE_MAXIMUM_REPETITION_COUNT,
    "prefill_suggestion_by_task_type": PREFILL_SUGGESTION_BY_TASK_TYPE,
    "prefill_default": PREFILL_DEFAULT,
    "provider_formatting_rules": PROVIDER_FORMATTING_RULES,
    "tcrte_dimension_weights": TCRTE_DIMENSION_WEIGHTS,
    "system_prompt_for_json_extraction": SYSTEM_PROMPT_FOR_JSON_EXTRACTION,
}
