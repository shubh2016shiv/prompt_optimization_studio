import pytest
from fastapi.testclient import TestClient

from app.models.requests import OptimizationRequest
from app.models.responses import (
    OptimizationAnalysis,
    OptimizationResponse,
    PromptVariant,
    VariantTCRTEScores,
)
from app.services.optimization.base import BaseOptimizerStrategy


class _CaptureLogger:
    def __init__(self):
        self.calls = []

    def info(self, event, **kwargs):
        self.calls.append(("info", event, kwargs))

    def warning(self, event, **kwargs):
        self.calls.append(("warning", event, kwargs))

    def exception(self, event, **kwargs):
        self.calls.append(("exception", event, kwargs))


class _NoOpStrategy(BaseOptimizerStrategy):
    async def generate_variants(self, request, core_k=2, few_shot_examples=None, auto_reason=None):
        response = OptimizationResponse(
            analysis=OptimizationAnalysis(
                detected_issues=[],
                model_notes="",
                framework_applied="kernel",
                coverage_delta="",
                auto_selected_framework=None,
                auto_reason=auto_reason,
                few_shot_source="not_applicable",
            ),
            techniques_applied=[],
            variants=[
                PromptVariant(
                    id=1,
                    name="V1",
                    strategy="test",
                    system_prompt="System prompt",
                    user_prompt="User prompt",
                    token_estimate=5,
                    tcrte_scores=VariantTCRTEScores(task=10, context=10, role=10, tone=10, execution=10),
                    strengths=[],
                    best_for="test",
                    overshoot_guards=[],
                    undershoot_guards=[],
                )
            ],
        )
        return await self._refine_variants_with_quality_critique(
            response=response,
            raw_prompt=request.raw_prompt,
            task_type=request.task_type,
            api_key=request.api_key,
            quality_gate_mode="off",
            framework="kernel",
            target_model=request.model_id,
        )


class _RouteDummyStrategy:
    async def generate_variants(self, request, core_k=2, few_shot_examples=None, auto_reason=None):
        return OptimizationResponse(
            analysis=OptimizationAnalysis(
                detected_issues=[],
                model_notes="",
                framework_applied="kernel",
                coverage_delta="",
                auto_selected_framework=None,
                auto_reason=auto_reason,
                few_shot_source="not_applicable",
            ),
            techniques_applied=[],
            variants=[
                PromptVariant(
                    id=1,
                    name="V1",
                    strategy="test",
                    system_prompt="System prompt",
                    user_prompt="User prompt",
                    token_estimate=5,
                    tcrte_scores=VariantTCRTEScores(task=10, context=10, role=10, tone=10, execution=10),
                    strengths=[],
                    best_for="test",
                    overshoot_guards=[],
                    undershoot_guards=[],
                )
            ],
        )


@pytest.mark.asyncio
async def test_quality_gate_logs_include_run_id(monkeypatch):
    from app.services.optimization import base

    capture_logger = _CaptureLogger()
    monkeypatch.setattr(base, "logger", capture_logger)

    request = OptimizationRequest(
        raw_prompt="Summarize this text",
        framework="kernel",
        provider="openai",
        model_id="gpt-4.1-mini",
        api_key="test-key",
        quality_gate_mode="off",
    )
    strategy = _NoOpStrategy()

    response = await strategy.generate_variants(request=request)
    assert response.run_metadata is not None

    metadata_log = [c for c in capture_logger.calls if c[1] == "optimize.run_metadata_initialized"]
    assert metadata_log
    run_id = metadata_log[0][2].get("run_id")
    assert run_id

    skipped_log = [c for c in capture_logger.calls if c[1] == "optimize.quality_gate_skipped"]
    assert skipped_log
    assert skipped_log[0][2].get("run_id") == run_id


def test_optimize_route_logs_request_id(monkeypatch):
    from app.api.routes import optimization as opt_route
    from app.main import app

    async def fake_execute_optimization_request(**kwargs):
        return OptimizationResponse(
            analysis=OptimizationAnalysis(
                detected_issues=[],
                model_notes="",
                framework_applied="kernel",
                coverage_delta="",
                auto_selected_framework=None,
                auto_reason=None,
                few_shot_source="not_applicable",
            ),
            techniques_applied=[],
            variants=[
                PromptVariant(
                    id=1,
                    name="V1",
                    strategy="test",
                    system_prompt="System prompt",
                    user_prompt="User prompt",
                    token_estimate=5,
                    tcrte_scores=VariantTCRTEScores(task=10, context=10, role=10, tone=10, execution=10),
                    strengths=[],
                    best_for="test",
                    overshoot_guards=[],
                    undershoot_guards=[],
                )
            ],
        )

    capture_logger = _CaptureLogger()
    monkeypatch.setattr(opt_route, "logger", capture_logger)
    monkeypatch.setattr(opt_route, "execute_optimization_request", fake_execute_optimization_request)

    with TestClient(app) as client:
        response = client.post(
            "/api/optimize",
            headers={"X-Request-ID": "req-opt-1"},
            json={
                "raw_prompt": "Summarize this text",
                "framework": "kernel",
                "provider": "openai",
                "model_id": "gpt-4.1-mini",
                "api_key": "secret-key",
                "quality_gate_mode": "off",
            },
        )
    assert response.status_code == 200

    start_logs = [c for c in capture_logger.calls if c[1] == "optimize.request_started"]
    assert start_logs
    assert start_logs[0][2].get("request_id") == "req-opt-1"
