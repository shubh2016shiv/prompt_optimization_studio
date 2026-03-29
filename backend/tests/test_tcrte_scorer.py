import pytest

from app.config import get_settings
from app.services.scoring.tcrte_scorer import compute_weighted_tcrte_overall, score_tcrte


def test_weighted_overall_matches_settings_weights():
    """Overall is a fixed weighted blend; spot-check corner cases (no API)."""
    w = get_settings().tcrte_dimension_weights
    assert (
        compute_weighted_tcrte_overall(
            {"task": 100, "context": 0, "role": 0, "tone": 0, "execution": 0},
            w,
        )
        == 25
    )
    assert (
        compute_weighted_tcrte_overall(
            {"task": 0, "context": 0, "role": 0, "tone": 0, "execution": 100},
            w,
        )
        == 30
    )


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

    assert result["task"]["score"] > 50
    assert result["role"]["score"] > 50
    assert result["context"]["score"] > 50
    assert result["tone"]["score"] > 50
    # Execution: format + no-hedge; nano rubric sometimes scores 40–55 without every checklist item
    assert result["execution"]["score"] >= 35
    assert result["overall_score"] > 50

@pytest.mark.asyncio
async def test_tcrte_overall_matches_weighted_dimensions(openai_api_key):
    """
    overall_score is always recomputed in Python from dimension scores; a live call
    must stay self-consistent (provider may still vary slightly between requests at temp=0).
    """
    raw_prompt = "Explain quantum computing to a 5-year old in 3 sentences."
    r = await score_tcrte(raw_prompt, openai_api_key)
    w = get_settings().tcrte_dimension_weights
    dims = ("task", "context", "role", "tone", "execution")
    assert r["overall_score"] == compute_weighted_tcrte_overall(
        {d: r[d]["score"] for d in dims},
        w,
    )
