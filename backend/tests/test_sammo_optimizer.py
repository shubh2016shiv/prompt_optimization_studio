"""Unit tests for SAMMO topological optimizer."""

import pytest

from app.models.requests import OptimizationRequest
from app.services.optimization.base import OptimizerFactory
from app.services.optimization.frameworks.sammo_topological_optimizer import (
    SammoPromptGraph,
    SammoTopologicalOptimizer,
)


def _build_request() -> OptimizationRequest:
    return OptimizationRequest(
        raw_prompt="Extract entities and return strict JSON.",
        task_type="extraction",
        framework="sammo",
        provider="openai",
        model_id="gpt-4.1-mini",
        model_label="GPT-4.1 Mini",
        is_reasoning_model=False,
        api_key="test-api-key",
        quality_gate_mode="off",
    )


def test_optimizer_factory_registers_sammo():
    optimizer = OptimizerFactory.get_optimizer("sammo")

    assert isinstance(optimizer, SammoTopologicalOptimizer)
    assert "sammo" in OptimizerFactory.list_available_framework_ids()


@pytest.mark.asyncio
async def test_sammo_generates_three_distinct_variants(monkeypatch):
    optimizer = SammoTopologicalOptimizer()
    request = _build_request()

    base_graph = SammoPromptGraph(
        instruction="Extract entities from input.",
        context_blocks=["Use only supplied text.", "Domain: clinical notes."],
        rules=["No hallucination.", "Return deterministic output."],
        few_shot=["Input: fever. Output: {entity:'symptom'}"],
        output_format="JSON object with entities array.",
    )

    mutation_graphs = {
        "compression": SammoPromptGraph(
            instruction="Extract entities from input.",
            context_blocks=["Use only supplied text.", "Clinical domain."],
            rules=["No hallucination."],
            few_shot=[],
            output_format="JSON entities array.",
        ),
        "restructure": SammoPromptGraph(
            instruction="Extract entities from input and classify each.",
            context_blocks=["Domain: clinical notes.", "Use only supplied text."],
            rules=["Return deterministic output.", "No hallucination."],
            few_shot=["Input: fever. Output: symptom"],
            output_format="JSON object with entities and class fields.",
        ),
        "syntactical": SammoPromptGraph(
            instruction="You must extract entities step-by-step and emit valid JSON.",
            context_blocks=["Use only supplied text.", "Domain: clinical notes."],
            rules=["No hallucination.", "Return deterministic output."],
            few_shot=["Input: fever. Output: {entity:'symptom'}"],
            output_format="JSON object with entities array.",
        ),
    }

    async def fake_parse_prompt_graph(**kwargs):
        return base_graph

    async def fake_mutate_graph(*, mutation_operator, **kwargs):
        return mutation_graphs[mutation_operator]

    async def fake_estimate_tcrte_score(prompt_text, api_key):
        if "SAMMO Mutation Label\ncompression" in prompt_text:
            return 70
        if "SAMMO Mutation Label\nrestructure" in prompt_text:
            return 92
        if "SAMMO Mutation Label\nsyntactical" in prompt_text:
            return 85
        return 75

    monkeypatch.setattr(optimizer, "_parse_prompt_graph", fake_parse_prompt_graph)
    monkeypatch.setattr(optimizer, "_mutate_graph", fake_mutate_graph)
    monkeypatch.setattr(optimizer, "_estimate_tcrte_score", fake_estimate_tcrte_score)

    response = await optimizer.generate_variants(request=request)

    assert response.analysis.framework_applied == "sammo"
    assert [variant.name for variant in response.variants] == ["Conservative", "Structured", "Advanced"]
    assert len({variant.system_prompt for variant in response.variants}) == 3
    assert response.run_metadata is not None
    assert response.run_metadata.framework == "sammo"
    assert response.run_metadata.sammo_mutations_explored == 4
    assert "Pareto Multi-Objective Selection" in response.techniques_applied