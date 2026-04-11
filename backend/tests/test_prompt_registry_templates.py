"""Unit tests for optimization prompt_registry templates and builders."""

from app.services.optimization.prompt_registry.core_attention import (
    CRITICALITY_ANALYSIS_PROMPT_TEMPLATE,
    STRATEGIC_REWRITE_PROMPT_TEMPLATE,
)
from app.services.optimization.prompt_registry.cot_ensemble import (
    COT_COMPONENT_EXTRACTION_PROMPT_TEMPLATE,
    SYNTHETIC_FEW_SHOT_GENERATION_PROMPT_TEMPLATE,
    build_cot_variant_1_system_prompt,
    build_cot_variant_2_system_prompt,
    build_cot_variant_3_system_prompt,
)
from app.services.optimization.prompt_registry.create import (
    CREATE_BLUEPRINT_PARSE_PROMPT_TEMPLATE,
    CREATE_REWRITE_PROMPT_TEMPLATE,
)
from app.services.optimization.prompt_registry.kernel import (
    KERNEL_COMPONENT_PARSE_PROMPT_TEMPLATE,
    KERNEL_REWRITE_PROMPT_TEMPLATE,
)
from app.services.optimization.prompt_registry.opro import OPRO_PROPOSAL_PROMPT_TEMPLATE
from app.services.optimization.prompt_registry.overshoot_undershoot import (
    FAILURE_MODE_ANALYSIS_PROMPT_TEMPLATE,
    STRUCTURAL_REWRITE_PROMPT_TEMPLATE,
)
from app.services.optimization.prompt_registry.progressive import (
    PROGRESSIVE_BLUEPRINT_PARSE_PROMPT_TEMPLATE,
    PROGRESSIVE_REWRITE_PROMPT_TEMPLATE,
)
from app.services.optimization.prompt_registry.ral_writer import (
    CONSTRAINT_EXTRACTION_PROMPT_TEMPLATE,
    NARRATIVE_DISENTANGLEMENT_PROMPT_TEMPLATE,
)
from app.services.optimization.prompt_registry.reasoning_aware import (
    REASONING_AWARE_PROMPT_TEMPLATE,
    build_reasoning_aware_variant_1_system_prompt,
    build_reasoning_aware_variant_2_system_prompt,
    build_reasoning_aware_variant_3_system_prompt,
)
from app.services.optimization.prompt_registry.sammo import (
    SAMMO_MUTATION_PROMPT_TEMPLATE,
    SAMMO_PARSE_PROMPT_TEMPLATE,
)
from app.services.optimization.prompt_registry.tcrte import (
    TCRTE_DIMENSION_FILL_PROMPT_TEMPLATE,
    build_tcrte_variant_2_system_prompt,
    build_tcrte_variant_3_system_prompt,
)
from app.services.optimization.prompt_registry.textgrad import (
    TEXTGRAD_EVALUATION_PROMPT_TEMPLATE,
    TEXTGRAD_GRADIENT_LOCALISATION_PROMPT_TEMPLATE,
    TEXTGRAD_PROMPT_REWRITE_PROMPT_TEMPLATE,
)
from app.services.optimization.prompt_registry.xml_structured import (
    XML_ONTOLOGY_PARSE_PROMPT_TEMPLATE,
    XML_REWRITE_PROMPT_TEMPLATE,
)


def test_static_templates_are_non_empty():
    templates = [
        KERNEL_COMPONENT_PARSE_PROMPT_TEMPLATE,
        KERNEL_REWRITE_PROMPT_TEMPLATE,
        XML_ONTOLOGY_PARSE_PROMPT_TEMPLATE,
        XML_REWRITE_PROMPT_TEMPLATE,
        CREATE_BLUEPRINT_PARSE_PROMPT_TEMPLATE,
        CREATE_REWRITE_PROMPT_TEMPLATE,
        PROGRESSIVE_BLUEPRINT_PARSE_PROMPT_TEMPLATE,
        PROGRESSIVE_REWRITE_PROMPT_TEMPLATE,
        REASONING_AWARE_PROMPT_TEMPLATE,
        COT_COMPONENT_EXTRACTION_PROMPT_TEMPLATE,
        SYNTHETIC_FEW_SHOT_GENERATION_PROMPT_TEMPLATE,
        TCRTE_DIMENSION_FILL_PROMPT_TEMPLATE,
        TEXTGRAD_EVALUATION_PROMPT_TEMPLATE,
        TEXTGRAD_GRADIENT_LOCALISATION_PROMPT_TEMPLATE,
        TEXTGRAD_PROMPT_REWRITE_PROMPT_TEMPLATE,
        CRITICALITY_ANALYSIS_PROMPT_TEMPLATE,
        STRATEGIC_REWRITE_PROMPT_TEMPLATE,
        CONSTRAINT_EXTRACTION_PROMPT_TEMPLATE,
        NARRATIVE_DISENTANGLEMENT_PROMPT_TEMPLATE,
        OPRO_PROPOSAL_PROMPT_TEMPLATE,
        SAMMO_PARSE_PROMPT_TEMPLATE,
        SAMMO_MUTATION_PROMPT_TEMPLATE,
        FAILURE_MODE_ANALYSIS_PROMPT_TEMPLATE,
        STRUCTURAL_REWRITE_PROMPT_TEMPLATE,
    ]
    assert all(isinstance(template, str) and template.strip() for template in templates)


def test_placeholder_rendering_works_for_key_templates():
    rendered_kernel = KERNEL_COMPONENT_PARSE_PROMPT_TEMPLATE.format(raw_prompt="hello")
    rendered_xml = XML_REWRITE_PROMPT_TEMPLATE.format(
        objective="obj",
        blueprint_json="{}",
        raw_prompt="prompt",
    )
    rendered_opro = OPRO_PROPOSAL_PROMPT_TEMPLATE.format(
        raw_prompt="r",
        task_type="analysis",
        model_label="m",
        evaluation_examples="e",
        trajectory="t",
        candidate_count=2,
    )
    assert "hello" in rendered_kernel
    assert "obj" in rendered_xml
    assert "Generate exactly 2 new candidate system prompts." in rendered_opro


def test_reasoning_aware_variant_builders_include_expected_sections():
    v1 = build_reasoning_aware_variant_1_system_prompt(
        task="Task",
        rules_list="- Rule",
        output_format="JSON",
    )
    v2 = build_reasoning_aware_variant_2_system_prompt(
        task="Task",
        rules_list="- Rule",
        output_format="JSON",
    )
    v3 = build_reasoning_aware_variant_3_system_prompt(
        task="Task",
        rules_list="- Rule",
        output_format="JSON",
    )
    assert "OBJECTIVE" in v1 and "FORMAT" in v1
    assert "### OBJECTIVE DECLARATION" in v2 and "### HARD CONSTRAINTS" in v2
    assert "# EXECUTION MANDATE" in v3 and "## OUTPUT FORMAT" in v3


def test_cot_variant_builders_include_expected_sections():
    v1 = build_cot_variant_1_system_prompt(
        task_description="Task",
        reasoning_steps_text="1. Step",
        demonstration_block="demo",
        constraints_text="- Rule",
        output_format="JSON",
    )
    v2 = build_cot_variant_2_system_prompt(
        task_description="Task",
        reasoning_steps_text="1. Step",
        demonstrations_block="demo",
        constraints_text="- Rule",
        output_format="JSON",
    )
    v3 = build_cot_variant_3_system_prompt(
        task_description="Task",
        reasoning_steps_text="1. Step",
        demonstrations_block="demo",
        constraints_text="- Rule",
        output_format="JSON",
    )
    assert "APPROACH - Single-Path Reasoning" in v1
    assert "APPROACH - Dual-Path Reasoning with Self-Check" in v2
    assert "APPROACH - Tri-Path Ensemble Synthesis" in v3
    assert "CONSTRAINTS:" in v3 and "Do NOT skip any ensemble path" in v3


def test_tcrte_variant_builders_include_expected_sections():
    v2 = build_tcrte_variant_2_system_prompt(
        role_section="role",
        task_section="task",
        context_section="context",
        tone_section="tone",
        execution_section="execution",
        constraints_text="- c",
    )
    v3 = build_tcrte_variant_3_system_prompt(
        role_section="role",
        task_section="task",
        context_section="context",
        tone_section="tone",
        execution_section="execution",
        constraints_text="- c",
    )
    assert "### ROLE" in v2 and "### EXECUTION" in v2
    assert "[R] ROLE DEFINITION" in v3 and "HARD CONSTRAINTS" in v3
