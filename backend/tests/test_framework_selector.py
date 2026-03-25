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

def test_select_framework_textgrad_default():
    """
    If no other rules match, the default should be textgrad to harden against failure modes.
    """
    framework, reason = select_framework(
        is_reasoning_model=False,
        task_type="unknown_task",
        complexity="standard",
        tcrte_overall_score=80,
        provider="openai",
        recommended_techniques=[]
    )
    assert framework == "textgrad"
    assert "No specific rule matched" in reason
