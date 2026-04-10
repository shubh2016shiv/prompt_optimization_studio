"""Validation tests for OptimizationRequest.evaluation_dataset."""

import pytest
from pydantic import ValidationError

from app.models.requests import OptimizationRequest


def _build_base_payload() -> dict:
    """Build a minimal valid optimization payload for request-model tests."""
    return {
        "raw_prompt": "Extract invoice fields from the input.",
        "task_type": "extraction",
        "framework": "kernel",
        "provider": "openai",
        "model_id": "gpt-4.1-mini",
        "model_label": "GPT-4.1 Mini",
        "is_reasoning_model": False,
        "api_key": "test-api-key",
    }


def test_optimization_request_accepts_valid_evaluation_dataset():
    """A valid non-empty evaluation_dataset should pass model validation."""
    payload = _build_base_payload()
    payload["evaluation_dataset"] = [
        {"input": "Invoice #2044, amount 1842.50, due 2026-04-15", "expected_output": {"invoice_number": "2044"}}
    ]

    request_model = OptimizationRequest.model_validate(payload)
    assert request_model.evaluation_dataset is not None
    assert len(request_model.evaluation_dataset) == 1


def test_optimization_request_rejects_empty_evaluation_dataset():
    """An empty evaluation_dataset list must be rejected."""
    payload = _build_base_payload()
    payload["evaluation_dataset"] = []

    with pytest.raises(ValidationError):
        OptimizationRequest.model_validate(payload)


def test_optimization_request_rejects_missing_expected_output():
    """Each dataset case must include expected_output."""
    payload = _build_base_payload()
    payload["evaluation_dataset"] = [{"input": "input only"}]

    with pytest.raises(ValidationError):
        OptimizationRequest.model_validate(payload)


def test_optimization_request_rejects_null_expected_output():
    """expected_output=None must fail because scorers require a concrete reference."""
    payload = _build_base_payload()
    payload["evaluation_dataset"] = [{"input": "sample", "expected_output": None}]

    with pytest.raises(ValidationError):
        OptimizationRequest.model_validate(payload)


def test_optimization_request_accepts_valid_expected_output_json_schema():
    """Valid JSON schema should be accepted in evaluation dataset cases."""
    payload = _build_base_payload()
    payload["evaluation_dataset"] = [
        {
            "input": "Invoice #2044, amount 1842.50",
            "expected_output": {"invoice_number": "2044", "amount": 1842.50},
            "expected_output_json_schema": {
                "type": "object",
                "properties": {
                    "invoice_number": {"type": "string"},
                    "amount": {"type": "number"},
                },
                "required": ["invoice_number", "amount"],
                "additionalProperties": False,
            },
        }
    ]

    request_model = OptimizationRequest.model_validate(payload)
    assert request_model.evaluation_dataset is not None
    assert request_model.evaluation_dataset[0].expected_output_json_schema is not None


def test_optimization_request_rejects_invalid_expected_output_json_schema():
    """Malformed JSON schemas must be rejected at request validation time."""
    payload = _build_base_payload()
    payload["evaluation_dataset"] = [
        {
            "input": "Invoice #2044",
            "expected_output": {"invoice_number": "2044"},
            "expected_output_json_schema": {"type": "unknown_type"},
        }
    ]

    with pytest.raises(ValidationError):
        OptimizationRequest.model_validate(payload)
