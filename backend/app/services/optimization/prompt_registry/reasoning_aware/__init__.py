from .extraction_prompt import TEMPLATE as REASONING_AWARE_PROMPT_TEMPLATE
from .variant_1_template import build_reasoning_aware_variant_1_system_prompt
from .variant_2_template import build_reasoning_aware_variant_2_system_prompt
from .variant_3_template import build_reasoning_aware_variant_3_system_prompt

__all__ = [
    "REASONING_AWARE_PROMPT_TEMPLATE",
    "build_reasoning_aware_variant_1_system_prompt",
    "build_reasoning_aware_variant_2_system_prompt",
    "build_reasoning_aware_variant_3_system_prompt",
]