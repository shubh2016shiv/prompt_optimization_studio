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
    assert "QA or multi-document task" in reason

def test_select_framework_xml_structured_multidoc():
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="analysis",
        complexity="standard",
        tcrte_overall_score=80,
        provider="anthropic",
        recommended_techniques=["multi-document", "few-shot"]
    )
    assert framework == "xml_structured"
    assert "QA or multi-document task" in reason

def test_select_framework_progressive():
    """
    Complex planning/coding tasks should select progressive.
    """
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="coding",
        complexity="complex",
        tcrte_overall_score=80,
        provider="openai",
        recommended_techniques=[]
    )
    assert framework == "progressive"
    assert "Progressive scaffolding builds" in reason

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
    assert framework == "opro"
    assert "prompt-score trajectories" in reason


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
    assert framework == "sammo"
    assert "topology" in reason


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
    assert framework == "progressive"
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
