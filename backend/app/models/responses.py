"""
Pydantic response models for API endpoints.

These define the shape of outgoing response bodies.
"""

from typing import Optional, Literal

from pydantic import BaseModel, Field


# Gap Analysis Response Models

class TCRTEScore(BaseModel):
    """Score for a single TCRTE dimension."""

    score: int = Field(..., ge=0, le=100, description="Score from 0-100")
    status: Literal["good", "weak", "missing"] = Field(..., description="Status classification")
    note: str = Field(..., description="Brief explanation of the score")


class TCRTEScores(BaseModel):
    """Scores for all five TCRTE dimensions."""

    task: TCRTEScore
    context: TCRTEScore
    role: TCRTEScore
    tone: TCRTEScore
    execution: TCRTEScore


class GapQuestion(BaseModel):
    """A question generated to fill a TCRTE gap."""

    id: str = Field(..., description="Unique question identifier")
    dimension: Literal["task", "context", "role", "tone", "execution"] = Field(
        ..., description="The TCRTE dimension this question addresses"
    )
    question: str = Field(..., description="The question text")
    placeholder: str = Field(..., description="Example answer hint")
    importance: Literal["critical", "recommended", "optional"] = Field(
        ..., description="Priority level"
    )


class GapAnalysisResponse(BaseModel):
    """Complete gap analysis response."""

    tcrte: TCRTEScores = Field(..., description="TCRTE dimension scores")
    tcrte_scores_source: Literal["openai_deterministic", "model_estimated"] = Field(
        default="model_estimated",
        description="Whether TCRTE scores came from the deterministic OpenAI scorer or from the model-generated fallback path.",
    )
    overall_score: int = Field(..., ge=0, le=100, description="Overall coverage score")
    complexity: Literal["simple", "medium", "complex"] = Field(
        ..., description="Task complexity assessment"
    )
    complexity_reason: str = Field(..., description="Explanation for complexity rating")
    recommended_techniques: list[str] = Field(
        ..., description="List of recommended techniques (CoRe, RAL-Writer, etc.)"
    )
    questions: list[GapQuestion] = Field(..., description="Questions to fill coverage gaps")
    auto_enrichments: list[str] = Field(
        ..., description="Automatic techniques that will be applied"
    )


# Optimization Response Models

class VariantTCRTEScores(BaseModel):
    """TCRTE scores for a single variant (simpler format)."""

    task: int = Field(..., ge=0, le=100)
    context: int = Field(..., ge=0, le=100)
    role: int = Field(..., ge=0, le=100)
    tone: int = Field(..., ge=0, le=100)
    execution: int = Field(..., ge=0, le=100)


class PromptQualityDimensionScores(BaseModel):
    """Per-dimension quality scores measured by the internal PromptQualityCritic."""

    role_clarity: int = Field(..., ge=0, le=100, description="Does the prompt define who the model is?")
    task_specificity: int = Field(..., ge=0, le=100, description="Is the task unambiguous and bounded?")
    constraint_completeness: int = Field(..., ge=0, le=100, description="Are hard/soft constraints explicit?")
    output_format: int = Field(..., ge=0, le=100, description="Is the output structure specified?")
    hallucination_resistance: int = Field(..., ge=0, le=100, description="Are anti-hallucination guards in place?")
    edge_case_handling: int = Field(..., ge=0, le=100, description="Is behaviour for edge cases defined?")
    improvement_over_raw: int = Field(..., ge=0, le=100, description="How much better than the raw prompt?")


class PromptQualityEvaluation(BaseModel):
    """Quality evaluation result attached to each variant by the internal critic."""

    status: Literal["ok", "degraded", "failed"] = Field(
        default="ok",
        description="Evaluation status: 'ok' when judge completed, 'degraded' when graceful fallback was used, and 'failed' when the quality evaluation crashed.",
    )
    overall_score: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Weighted average quality score. Null when evaluation failed hard and no trustworthy score exists.",
    )
    grade: Literal["A", "B", "C", "D", "F"] = Field(..., description="Letter grade (A=90+, B=80+, C=70+, D=50+, F=<50)")
    dimensions: PromptQualityDimensionScores = Field(..., description="Per-dimension breakdown")
    strengths: list[str] = Field(..., description="What the prompt does well")
    remaining_gaps: list[str] = Field(..., description="Weaknesses still present after enhancement")
    was_enhanced: bool = Field(..., description="True if the variant was improved by the critic")
    was_fallback: bool = Field(
        default=False,
        description="True when evaluation gracefully degraded and the judge did not complete reliably.",
    )


class TaskEvaluationCaseResult(BaseModel):
    """
    Per-case empirical result for one prompt variant.

    Association:
      Produced by app.services.evaluation.task_level_evaluation.TaskLevelEvaluationService
      and attached to PromptVariant.task_evaluation.
    """

    case_index: int = Field(..., ge=1, description="1-based index of the dataset case.")
    score: int = Field(..., ge=0, le=100, description="Case-level task success score.")
    status: Literal["pass", "partial", "fail"] = Field(
        ...,
        description="Pass/fail classification derived from the case score threshold.",
    )
    scoring_method: Literal["deterministic", "rubric", "pairwise"] = Field(
        ...,
        description="How the case score was produced.",
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Machine-readable reason when a case does not pass.",
    )


class TaskEvaluationResult(BaseModel):
    """
    Aggregated empirical task performance for one prompt variant.

    Association:
      This object complements PromptQualityEvaluation by measuring real task
      success over user-provided evaluation examples.
    """

    task_success_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Aggregate score for this variant over the evaluation dataset.",
    )
    pass_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of dataset cases that passed the threshold.",
    )
    total_cases: int = Field(..., ge=1, description="Total number of evaluated dataset cases.")
    passed_cases: int = Field(..., ge=0, description="Number of cases classified as pass.")
    judging_mode: Literal["deterministic", "rubric", "pairwise", "mixed"] = Field(
        ...,
        description="Dominant evaluation mode used for this variant.",
    )
    pairwise_tie_break_applied: bool = Field(
        default=False,
        description="Whether this variant score was adjusted by pairwise tie-break logic.",
    )
    failure_reasons: list[str] = Field(
        default_factory=list,
        description="Unique failure reasons observed across case results.",
    )
    case_results: list[TaskEvaluationCaseResult] = Field(
        default_factory=list,
        description="Per-case evaluation breakdown for traceability and debugging.",
    )


class PromptVariant(BaseModel):
    """A single optimized prompt variant."""

    id: int = Field(..., ge=1, le=3, description="Variant number (1, 2, or 3)")
    name: str = Field(..., description="Variant name (Conservative, Structured, Advanced)")
    strategy: str = Field(..., description="Brief description of the variant's approach")
    system_prompt: str = Field(..., description="The optimized system prompt")
    user_prompt: str = Field(..., description="The optimized user prompt template")
    prefill_suggestion: Optional[str] = Field(
        default=None, description="Claude prefill suggestion for format locking"
    )
    token_estimate: int = Field(..., ge=0, description="Estimated token count")
    tcrte_scores: VariantTCRTEScores = Field(..., description="TCRTE coverage scores")
    tcrte_scores_source: Literal[
        "initial_framework_estimate",
        "quality_critic_proxy",
        "not_evaluated",
    ] = Field(
        default="initial_framework_estimate",
        description="Where tcrte_scores came from (framework estimate vs quality-critic proxy).",
    )
    quality_evaluation: Optional[PromptQualityEvaluation] = Field(
        default=None, description="Quality evaluation from the internal PromptQualityCritic"
    )
    task_evaluation: Optional[TaskEvaluationResult] = Field(
        default=None,
        description=(
            "Empirical task-level evaluation over evaluation_dataset cases. "
            "Present only when the caller supplied evaluation_dataset."
        ),
    )
    quality_scores_source: Literal[
        "prompt_quality_critic",
        "fallback",
        "not_evaluated",
    ] = Field(
        default="not_evaluated",
        description="Where quality_evaluation came from, or not_evaluated when quality gate did not run.",
    )
    strengths: list[str] = Field(..., description="Key strengths of this variant")
    best_for: str = Field(..., description="Use cases this variant is best suited for")
    overshoot_guards: list[str] = Field(..., description="Anti-overshoot protections")
    undershoot_guards: list[str] = Field(..., description="Anti-undershoot protections")


class OptimizationAnalysis(BaseModel):
    """Analysis summary from the optimization process."""

    detected_issues: list[str] = Field(..., description="Issues found in the original prompt")
    model_notes: str = Field(..., description="Notes about model-specific optimizations")
    framework_applied: str = Field(..., description="The framework that was applied")
    coverage_delta: str = Field(..., description="Coverage improvement summary")
    auto_selected_framework: Optional[str] = Field(
        default=None,
        description="Framework chosen by auto-select logic. None if user manually selected.",
    )
    auto_reason: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of why auto-select chose this framework.",
    )
    few_shot_source: Literal["knn", "synthetic", "not_applicable"] = Field(
        default="not_applicable",
        description="Provenance for few-shot examples used by cot_ensemble.",
    )


class OptimizationRunMetadata(BaseModel):
    """Audit metadata for a single optimization execution."""

    run_id: str = Field(..., description="Unique optimization run identifier (UUID4).")
    raw_prompt_hash: str = Field(..., description="SHA256 hash of the raw prompt.")
    framework: str = Field(..., description="Effective framework used for optimization.")
    judge_model: str = Field(..., description="Model used by the internal quality judge.")
    target_model: str = Field(..., description="User-selected target model for optimization.")
    timestamp: str = Field(..., description="UTC ISO8601 timestamp for the run.")
    llm_call_count: int = Field(
        default=0,
        ge=0,
        description="Total number of LLM or embedding API calls made during this optimization request.",
    )
    estimated_prompt_tokens: Optional[int] = Field(
        default=None,
        ge=0,
        description="Estimated total input tokens counted across calls for this optimization request.",
    )


class OptimizationJobCreatedResponse(BaseModel):
    """Response returned when an asynchronous optimization job is created."""

    job_id: str = Field(..., description="Unique job identifier for polling and result retrieval.")
    status: Literal["queued", "running", "succeeded", "failed"] = Field(
        ...,
        description="Current lifecycle status for the job.",
    )
    created_at: str = Field(..., description="UTC ISO8601 timestamp when the job was created.")
    request_id: Optional[str] = Field(
        default=None,
        description="HTTP correlation identifier associated with the job creation request.",
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Langfuse trace identifier associated with the optimization job.",
    )


class OptimizationJobStatusResponse(BaseModel):
    """Status payload for an asynchronous optimization job."""

    job_id: str = Field(..., description="Unique job identifier.")
    status: Literal["queued", "running", "succeeded", "failed"] = Field(
        ...,
        description="Current lifecycle status for the job.",
    )
    created_at: str = Field(..., description="UTC ISO8601 timestamp when the job was created.")
    updated_at: str = Field(..., description="UTC ISO8601 timestamp for the latest state change.")
    current_phase: Optional[str] = Field(
        default=None,
        description="Human-readable phase label describing current execution progress.",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="HTTP correlation identifier captured at job creation time.",
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Langfuse trace identifier used for this job execution.",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Optimization run identifier once generation has started.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Failure message when the job enters failed status.",
    )


class OptimizationResponse(BaseModel):
    """Complete optimization response with all three variants."""

    analysis: OptimizationAnalysis = Field(..., description="Optimization analysis summary")
    techniques_applied: list[str] = Field(
        ..., description="List of techniques applied (CoRe, RAL-Writer, etc.)"
    )
    variants: list[PromptVariant] = Field(..., description="The three optimized variants")
    run_metadata: Optional[OptimizationRunMetadata] = Field(
        default=None,
        description="Execution metadata for observability and auditability.",
    )


# Chat Response Models

class ChatMessage(BaseModel):
    """A single chat message."""

    role: Literal["user", "assistant"] = Field(..., description="Message sender role")
    content: str = Field(..., description="Message content")


class ChatResponse(BaseModel):
    """Chat endpoint response."""

    message: ChatMessage = Field(..., description="The assistant's response")
