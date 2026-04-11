from .component_extraction_prompt import TEMPLATE as COT_COMPONENT_EXTRACTION_PROMPT_TEMPLATE
from .synthetic_few_shot_generation_prompt import TEMPLATE as SYNTHETIC_FEW_SHOT_GENERATION_PROMPT_TEMPLATE
from .variant_1_template import build_cot_variant_1_system_prompt
from .variant_2_template import build_cot_variant_2_system_prompt
from .variant_3_template import build_cot_variant_3_system_prompt

__all__ = [
    "COT_COMPONENT_EXTRACTION_PROMPT_TEMPLATE",
    "SYNTHETIC_FEW_SHOT_GENERATION_PROMPT_TEMPLATE",
    "build_cot_variant_1_system_prompt",
    "build_cot_variant_2_system_prompt",
    "build_cot_variant_3_system_prompt",
]