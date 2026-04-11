from app.services.analysis.framework_selector import select_framework

def test_select_framework_reasoning_model():
    """
    is_reasoning_model=True should bypass all other rules and select reasoning_aware.
    """
    framework, reason = select_framework(
        is_reasoning_model=True,
        task_type="qa",
        complexity="complex",
        tcrte_overall_score=20,
        provider="openai",
        recommended_techniques=["multi-document"]
    )
    assert framework == "reasoning_aware"
    assert "Reasoning model detected" in reason

def test_select_framework_xml_structured_qa():
    """
    qa tasks or multi-document tasks should select xml_structured.
    """
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="qa",
        complexity="standard",
        tcrte_overall_score=80,
        provider="anthropic",
        recommended_techniques=[]
    )
    assert framework == "xml_structured"
    assert "XML Structured Bounding" in reason

def test_select_framework_xml_structured_multidoc():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="analysis",
        complexity="medium",
        tcrte_overall_score=80,
        provider="anthropic",
        recommended_techniques=["XML-Bounding", "few-shot"]
    )
    assert framework == "xml_structured"
    assert "XML Structured Bounding" in reason

def test_select_framework_progressive():
    """
    Complex planning/coding tasks should be remapped to ROI allowlist.
    """
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="coding",
        complexity="complex",
        tcrte_overall_score=80,
        provider="openai",
        recommended_techniques=[]
    )
    assert framework == "create"
    assert "Auto-routing ROI policy remapped 'progressive' to 'create'" in reason

def test_select_framework_cot_ensemble():
    """
    Complex reasoning/analysis tasks should select cot_ensemble.
    """
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="reasoning",
        complexity="complex",
        tcrte_overall_score=80,
        provider="openai",
        recommended_techniques=[]
    )
    assert framework == "cot_ensemble"
    assert "CoT Ensemble injects" in reason


def test_select_framework_opro_requires_evaluation_dataset_and_signal():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="analysis",
        complexity="complex",
        tcrte_overall_score=82,
        provider="openai",
        recommended_techniques=["iterative_refinement"],
        has_evaluation_dataset=True,
    )
    assert framework == "textgrad"
    assert "Auto-routing ROI policy remapped 'opro' to 'textgrad'" in reason


def test_select_framework_does_not_auto_select_opro_without_evaluation_dataset():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="analysis",
        complexity="complex",
        tcrte_overall_score=82,
        provider="openai",
        recommended_techniques=["iterative_refinement"],
        has_evaluation_dataset=False,
    )
    assert framework == "cot_ensemble"
    assert "CoT Ensemble injects" in reason


def test_select_framework_sammo_when_structure_aware_signal_present():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="extraction",
        complexity="expert",
        tcrte_overall_score=78,
        provider="openai",
        recommended_techniques=["structure_aware"],
        has_evaluation_dataset=False,
    )
    assert framework == "core_attention"
    assert "Auto-routing ROI policy remapped 'sammo' to 'core_attention'" in reason


def test_select_framework_sammo_not_selected_without_signal():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="extraction",
        complexity="expert",
        tcrte_overall_score=78,
        provider="openai",
        recommended_techniques=[],
        has_evaluation_dataset=False,
    )
    assert framework == "kernel"
    assert "Kernel framework" in reason


def test_select_framework_accepts_core_product_vocabulary():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="analysis",
        complexity="medium",
        tcrte_overall_score=82,
        provider="openai",
        recommended_techniques=["CoRe"],
    )
    assert framework == "core_attention"
    assert "context-loss risk" in reason


def test_select_framework_accepts_ral_writer_product_vocabulary():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="analysis",
        complexity="medium",
        tcrte_overall_score=82,
        provider="openai",
        recommended_techniques=["RAL-Writer"],
    )
    assert framework == "ral_writer"
    assert "Heavy constraint/rule reliance" in reason


def test_select_framework_accepts_cot_product_vocabulary():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="reasoning",
        complexity="medium",
        tcrte_overall_score=82,
        provider="openai",
        recommended_techniques=["CoT-Ensemble"],
    )
    assert framework == "cot_ensemble"
    assert "structured reasoning support" in reason


def test_select_framework_accepts_progressive_product_vocabulary():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="planning",
        complexity="medium",
        tcrte_overall_score=82,
        provider="openai",
        recommended_techniques=["Progressive-Disclosure"],
    )
    assert framework == "create"
    assert "Auto-routing ROI policy remapped 'progressive' to 'create'" in reason


def test_select_framework_prefill_is_ignored_for_routing():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="analysis",
        complexity="medium",
        tcrte_overall_score=82,
        provider="anthropic",
        recommended_techniques=["Prefill"],
    )
    assert framework == "kernel"
    assert "lower-cost default" in reason


def test_select_framework_tcrte_low_score():
    """
    Low TCRTE score (<50) on non-complex/non-qa tasks should select tcrte.
    """
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="planning",
        complexity="standard",
        tcrte_overall_score=30,  # Below 50
        provider="anthropic",
        recommended_techniques=[]
    )
    assert framework == "tcrte"
    assert "Overall TCRTE score is 30/100" in reason


def test_select_framework_low_score_qa_prefers_structural_recovery():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="qa",
        complexity="medium",
        tcrte_overall_score=30,
        provider="openai",
        recommended_techniques=["XML-Bounding"],
    )
    assert framework == "tcrte"
    assert "structural gaps must be filled" in reason


def test_select_framework_low_score_complex_reasoning_prefers_textgrad():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="reasoning",
        complexity="complex",
        tcrte_overall_score=35,
        provider="openai",
        recommended_techniques=["CoT-Ensemble"],
    )
    assert framework == "textgrad"
    assert "structural recovery" in reason

def test_select_framework_kernel():
    """
    Routing/extraction or simple tasks should select kernel.
    """
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="extraction",
        complexity="simple",
        tcrte_overall_score=80,
        provider="openai",
        recommended_techniques=[]
    )
    assert framework == "kernel"
    assert "Simple or tool-oriented task" in reason

def test_select_framework_textgrad_only_for_complex_low_tcrte():
    """
    TextGrad should be selected only for complex tasks with very low TCRTE.
    """
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="unknown_task",
        complexity="complex",
        tcrte_overall_score=35,
        provider="openai",
        recommended_techniques=[]
    )
    assert framework == "textgrad"
    assert "very low TCRTE" in reason


def test_select_framework_score_50_avoids_textgrad():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="unknown_task",
        complexity="complex",
        tcrte_overall_score=50,
        provider="openai",
        recommended_techniques=[]
    )
    assert framework == "create"
    assert "Auto-routing ROI policy remapped 'progressive' to 'create'" in reason


def test_select_framework_medium_complexity_maps_to_standard_for_moderate_scores():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="unknown_task",
        complexity="medium",
        tcrte_overall_score=60,
        provider="openai",
        recommended_techniques=[],
    )
    assert framework == "overshoot_undershoot"
    assert "Moderate TCRTE" in reason


def test_select_framework_unknown_complexity_falls_back_safely():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="unknown_task",
        complexity="mysterious",
        tcrte_overall_score=80,
        provider="openai",
        recommended_techniques=[],
    )
    assert framework == "kernel"
    assert "lower-cost default" in reason


def test_select_framework_default_unmatched_goes_kernel():
    """
    Unmatched non-complex tasks should default to kernel (lower-cost fallback).
    """
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="unknown_task",
        complexity="standard",
        tcrte_overall_score=80,
        provider="openai",
        recommended_techniques=[]
    )
    assert framework == "kernel"
    assert "lower-cost default" in reason


def test_select_framework_auto_allowlist_blocks_legacy_frameworks():
    allowed_frameworks = {
        "create",
        "xml_structured",
        "core_attention",
        "ral_writer",
        "cot_ensemble",
        "overshoot_undershoot",
        "textgrad",
        "kernel",
        "tcrte",
        "reasoning_aware",
    }

    scenarios = [
        {
            "is_reasoning_model": False,
            "task_type": "analysis",
            "complexity": "complex",
            "tcrte_overall_score": 82,
            "provider": "openai",
            "recommended_techniques": ["iterative_refinement"],
            "has_evaluation_dataset": True,
        },
        {
            "is_reasoning_model": False,
            "task_type": "extraction",
            "complexity": "expert",
            "tcrte_overall_score": 78,
            "provider": "openai",
            "recommended_techniques": ["structure_aware"],
            "has_evaluation_dataset": False,
        },
        {
            "is_reasoning_model": False,
            "task_type": "planning",
            "complexity": "complex",
            "tcrte_overall_score": 80,
            "provider": "openai",
            "recommended_techniques": ["Progressive-Disclosure"],
            "has_evaluation_dataset": False,
        },
    ]

    for scenario in scenarios:
        framework, _ = select_framework(**scenario)
        assert framework in allowed_frameworks
