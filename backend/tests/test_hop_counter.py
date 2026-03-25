import pytest
from app.services.analysis.hop_counter import count_reasoning_hops

@pytest.mark.asyncio
async def test_hop_counter_single_step(openai_api_key):
    """
    A simple single-step instruction should default to k=2 (the minimum hop count for CoRe,
    representing start+end context repetition).
    """
    prompt = "Summarize the following email thread into three bullet points."
    k = await count_reasoning_hops(prompt, openai_api_key)
    assert k == 2

@pytest.mark.asyncio
async def test_hop_counter_multi_step(openai_api_key):
    """
    A multi-hop instruction requiring carrying context forward should return k >= 3.
    """
    prompt = (
        "Step 1: Read Document A and extract the safety threshold integer. "
        "Step 2: Read Document B and find all reported incident values. "
        "Step 3: Compare the incidents from Step 2 against the threshold from Step 1 "
        "and list only those that exceed it."
    )
    k = await count_reasoning_hops(prompt, openai_api_key)
    # The prompt explicitly describes 3 dependent steps
    assert k >= 3 and k <= 5
