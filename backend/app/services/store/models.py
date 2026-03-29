"""
Persistence models for optimization job storage.

These models represent what gets serialized into durable storage. They are
separate from API response models so storage evolution does not force direct
API-contract churn.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class OptimizationJobPersistedRecord(BaseModel):
    """
    Durable optimization job state stored in Redis (or other backing stores).

    Association:
      Produced and consumed by `IJobStore` implementations. The API layer maps
      this persisted shape into user-facing status/result payloads.
    """

    job_id: str = Field(..., description="Unique job identifier.")
    request_payload: dict[str, Any] = Field(..., description="Serialized OptimizationRequest payload.")
    status: Literal["queued", "running", "succeeded", "failed"] = Field(
        ...,
        description="Current durable lifecycle state.",
    )
    created_at: str = Field(..., description="UTC ISO8601 creation timestamp.")
    updated_at: str = Field(..., description="UTC ISO8601 update timestamp.")
    request_id: str | None = Field(default=None, description="HTTP correlation identifier.")
    trace_id: str | None = Field(default=None, description="Trace identifier for observability.")
    current_phase: str | None = Field(default=None, description="Current execution phase label.")
    run_id: str | None = Field(default=None, description="Optimization run identifier.")
    error_message: str | None = Field(default=None, description="Failure details when status=failed.")
    optimization_response_json: str | None = Field(
        default=None,
        description="Serialized OptimizationResponse for completed jobs.",
    )
