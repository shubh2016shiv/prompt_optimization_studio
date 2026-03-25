import pytest
from app.services.scoring.tcrte_scorer import score_tcrte

@pytest.mark.asyncio
async def test_tcrte_weak_prompt(openai_api_key):
    """
    A prompt with no role, context, or tone should score very low on those dimensions.
    """
    raw_prompt = "Write a function to sort a list."
    result = await score_tcrte(raw_prompt, openai_api_key)
    
    # Task should be high (has imperative verb and implicit output)
    # Role, Context, Tone should be < 35
    assert result["role"]["score"] < 35
    assert result["context"]["score"] < 35
    assert result["tone"]["score"] < 35
    # Overall score should be mediocre
    assert result["overall_score"] < 50

@pytest.mark.asyncio
async def test_tcrte_strong_prompt(openai_api_key):
    """
    A fully specified prompt should score highly across all dimensions.
    """
    raw_prompt = (
        "You are an expert financial analyst with 10 years of experience. "
        "Analyse the provided Q3 earnings report for ACME Corp. "
        "Maintain a highly formal, objective tone intended for the board of directors. "
        "Identify the top 3 revenue drivers and output them as a JSON list of strings. "
        "Do not include any introductory text or hedge your statements."
    )
    result = await score_tcrte(raw_prompt, openai_api_key)
    
    assert result["role"]["score"] > 50
    assert result["context"]["score"] > 50
    assert result["tone"]["score"] > 50
    assert result["execution"]["score"] > 50
    assert result["overall_score"] > 50

@pytest.mark.asyncio
async def test_tcrte_reproducibility(openai_api_key):
    """
    Proves that temperature=0 scoring is deterministic. 
    Running the exact same prompt twice should yield identical scores.
    """
    raw_prompt = "Explain quantum computing to a 5-year old in 3 sentences."
    
    result1 = await score_tcrte(raw_prompt, openai_api_key)
    result2 = await score_tcrte(raw_prompt, openai_api_key)
    
    # Assert exact match across all dimensions and notes
    assert result1["task"]["score"] == result2["task"]["score"]
    assert result1["context"]["score"] == result2["context"]["score"]
    assert result1["role"]["score"] == result2["role"]["score"]
    assert result1["tone"]["score"] == result2["tone"]["score"]
    assert result1["execution"]["score"] == result2["execution"]["score"]
    assert result1["overall_score"] == result2["overall_score"]
