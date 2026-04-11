"""Centralized optimization configuration sourced from app settings.

This module preserves the historical constant exports used across optimizer
frameworks while delegating values to the typed Pydantic Settings model.
"""

from app.config import get_settings

_SETTINGS = get_settings()

# 1) LLM model/provider for optimization sub-tasks
LLM_SUB_TASK_PROVIDER = _SETTINGS.optimization_llm_sub_task_provider
LLM_SUB_TASK_MODEL = _SETTINGS.openai_subtask_model

# 2) Token budgets
MAX_TOKENS_COMPONENT_EXTRACTION = _SETTINGS.optimization_max_tokens_component_extraction
MAX_TOKENS_SYNTHETIC_EXAMPLE_GENERATION = (
    _SETTINGS.optimization_max_tokens_synthetic_example_generation
)
MAX_TOKENS_TEXTGRAD_EVALUATION = _SETTINGS.optimization_max_tokens_textgrad_evaluation
MAX_TOKENS_TEXTGRAD_GRADIENT = _SETTINGS.optimization_max_tokens_textgrad_gradient
MAX_TOKENS_TEXTGRAD_UPDATE = _SETTINGS.optimization_max_tokens_textgrad_update
MAX_TOKENS_TCRTE_DIMENSION_FILL = _SETTINGS.optimization_max_tokens_tcrte_dimension_fill
MAX_TOKENS_VARIANT_SCORE_ESTIMATION = _SETTINGS.optimization_max_tokens_variant_score_estimation
MAX_TOKENS_FAILURE_MODE_ANALYSIS = _SETTINGS.optimization_max_tokens_failure_mode_analysis
MAX_TOKENS_CORE_CRITICALITY_ANALYSIS = _SETTINGS.optimization_max_tokens_core_criticality_analysis
MAX_TOKENS_RAL_CONSTRAINT_EXTRACTION = _SETTINGS.optimization_max_tokens_ral_constraint_extraction
MAX_TOKENS_OPRO_PROPOSAL = _SETTINGS.optimization_max_tokens_opro_proposal
MAX_TOKENS_SAMMO_STRUCTURAL_PARSE = _SETTINGS.optimization_max_tokens_sammo_structural_parse
MAX_TOKENS_KERNEL_REWRITE = _SETTINGS.optimization_max_tokens_kernel_rewrite
MAX_TOKENS_XML_REWRITE = _SETTINGS.optimization_max_tokens_xml_rewrite
MAX_TOKENS_CREATE_REWRITE = _SETTINGS.optimization_max_tokens_create_rewrite
MAX_TOKENS_PROGRESSIVE_REWRITE = _SETTINGS.optimization_max_tokens_progressive_rewrite

# 3) TextGrad runtime
TEXTGRAD_DEFAULT_ITERATION_COUNT = _SETTINGS.optimization_textgrad_default_iteration_count
TEXTGRAD_EVALUATION_TEMPERATURE = _SETTINGS.optimization_textgrad_evaluation_temperature
TEXTGRAD_UPDATE_TEMPERATURE = _SETTINGS.optimization_textgrad_update_temperature

# 4) OPRO runtime
OPRO_DEFAULT_ITERATION_COUNT = _SETTINGS.optimization_opro_default_iteration_count
OPRO_CANDIDATES_PER_ITERATION = _SETTINGS.optimization_opro_candidates_per_iteration
OPRO_TRAJECTORY_KEEP_TOP = _SETTINGS.optimization_opro_trajectory_keep_top
OPRO_EXEMPLARS_IN_META_PROMPT = _SETTINGS.optimization_opro_exemplars_in_meta_prompt
OPRO_MAX_TRAINING_CASES = _SETTINGS.optimization_opro_max_training_cases
OPRO_PROPOSAL_TEMPERATURE = _SETTINGS.optimization_opro_proposal_temperature

# 5) SAMMO runtime
SAMMO_MIN_TCRTE_THRESHOLD = _SETTINGS.optimization_sammo_min_tcrte_threshold
SAMMO_TOKEN_WEIGHT = _SETTINGS.optimization_sammo_token_weight
SAMMO_TCRTE_WEIGHT = _SETTINGS.optimization_sammo_tcrte_weight

# 6) CoRe repetition bounds
CORE_MINIMUM_REPETITION_COUNT = _SETTINGS.optimization_core_minimum_repetition_count
CORE_MAXIMUM_REPETITION_COUNT = _SETTINGS.optimization_core_maximum_repetition_count

# 7) Prefill and provider formatting behavior
PREFILL_SUGGESTION_BY_TASK_TYPE = dict(_SETTINGS.optimization_prefill_suggestion_by_task_type)
PREFILL_DEFAULT = _SETTINGS.optimization_prefill_default
PROVIDER_FORMATTING_RULES = _SETTINGS.optimization_provider_formatting_rules_dict
PROVIDER_FORMATTING_DEFAULT = _SETTINGS.optimization_provider_formatting_default

# 8) Shared scoring/system prompt values
TCRTE_DIMENSION_WEIGHTS = _SETTINGS.tcrte_dimension_weights
SYSTEM_PROMPT_FOR_JSON_EXTRACTION = _SETTINGS.optimization_system_prompt_for_json_extraction

# Backward-compatible aggregate map used across optimization modules
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
