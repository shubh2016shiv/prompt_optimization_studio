"""
Base Optimizer Strategy Interface and Framework Factory

Provides the SOLID Strategy pattern interface for all 8 APOST prompt optimization
frameworks plus a Factory that resolves framework ID strings to concrete strategy
instances.

ARCHITECTURE OVERVIEW:
═══════════════════════════════════════════════════════════════════════════════

  ┌────────────────────┐
  │ OptimizationRequest│
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐      Resolves framework_id string
  │ OptimizerFactory   │──────────────────────────────────────────┐
  └─────────┬──────────┘                                          │
            │                                                      │
  ┌─────────┴──────────────────────────────────────────────────────┤
  │                 8 Concrete Strategy Classes                     │
  │                                                                │
  │  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌───────────┐│
  │  │ Kernel   │  │ XML          │  │ CREATE    │  │Progressive││
  │  │ Optimizer│  │ Structured   │  │ Optimizer │  │ Disclosure││
  │  └──────────┘  └──────────────┘  └───────────┘  └───────────┘│
  │  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌───────────┐│
  │  │Reasoning │  │ CoT Ensemble │  │ TCRTE     │  │ TextGrad  ││
  │  │Aware     │  │ (Medprompt)  │  │ Coverage  │  │ Iterative ││
  │  └──────────┘  └──────────────┘  └───────────┘  └───────────┘│
  └────────────────────────────────────────────────────────────────┘

NAMING CONVENTION:
  All framework strategy classes live inside:
    app/services/optimization/frameworks/

  Framework files follow the pattern:
    {framework_name}_optimizer.py

  This base module lives at:
    app/services/optimization/base.py

DESIGN DECISIONS:
  - Lazy imports inside get_optimizer() prevent circular imports.
  - Unrecognised framework IDs raise ValueError (fail-fast) instead of
    silently falling back to an unrelated framework.
  - "auto" is NOT in the registry — auto-select logic resolves to a concrete
    framework ID BEFORE reaching the factory (see framework_selector.py).
"""

from abc import ABC, abstractmethod
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, List, Optional, Literal
from uuid import uuid4

import structlog

from app.observability.usage_tracking import get_current_usage_snapshot
from app.models.requests import OptimizationRequest
from app.models.responses import (
    OptimizationRunMetadata,
    OptimizationResponse,
    PromptQualityDimensionScores,
    PromptQualityEvaluation,
)

logger = structlog.get_logger(__name__)


def _sync_run_usage_metadata(response: OptimizationResponse) -> None:
    """Project the current route-scoped usage totals into run metadata."""
    if response.run_metadata is None:
        return

    usage_snapshot = get_current_usage_snapshot()
    if usage_snapshot is None:
        return

    response.run_metadata.llm_call_count = usage_snapshot.llm_call_count
    response.run_metadata.estimated_prompt_tokens = usage_snapshot.prompt_tokens


class BaseOptimizerStrategy(ABC):
    """
    Abstract base class for prompt optimization strategies.

    Any concrete framework implementation must subclass this and implement
    the generate_variants() method. This enforces a uniform interface
    across all 8 frameworks (Open/Closed Principle).

    The generate_variants() method receives the full OptimizationRequest
    plus cross-cutting parameters (core_k, few_shot_examples, auto_reason)
    that individual frameworks may or may not use.

    Concrete helper: _refine_variants_with_quality_critique() is a shared
    quality gate that all frameworks call after first-pass assembly to
    critique and enhance each variant using the internal PromptQualityCritic.
    """

    @abstractmethod
    async def generate_variants(
        self,
        request: OptimizationRequest,
        core_k: int = 2,
        few_shot_examples: Optional[List[Any]] = None,
        auto_reason: Optional[str] = None,
    ) -> OptimizationResponse:
        """
        Transform the raw prompt into 3 optimised variants.

        This is the main algorithm entry point for each framework. Every
        framework MUST:
          1. Read request.raw_prompt (and optionally request.answers, request.gap_data)
          2. Return an OptimizationResponse with exactly 3 PromptVariant objects
          3. Populate analysis.framework_applied with its own framework ID

        Args:
            request: The full API request containing raw_prompt, provider,
                     model_id, task_type, answers, gap_data, input_variables, etc.
            core_k: CoRe repetition depth from hop_counter (§5.1).
                     k=2 means start+end. k=5 means 5 evenly-spaced insertions.
            few_shot_examples: kNN-retrieved corpus entries for CoT Ensemble (§4.4).
                               None for most frameworks.
            auto_reason: Human-readable string explaining why auto-select chose
                         this framework. None if user manually selected.

        Returns:
            OptimizationResponse matching the exact frontend API contract.
        """
        pass

    # ──────────────────────────────────────────────────────────────────────
    # Concrete Quality Gate — shared by all 8 frameworks
    # ──────────────────────────────────────────────────────────────────────

    async def _refine_variants_with_quality_critique(
        self,
        response: OptimizationResponse,
        raw_prompt: str,
        task_type: str,
        api_key: str,
        quality_gate_mode: Literal["full", "critique_only", "off", "sample_one_variant"] = "full",
        framework: Optional[str] = None,
        target_model: Optional[str] = None,
    ) -> OptimizationResponse:
        """
        Internal quality gate: critique each variant, enhance weak ones,
        replace hardcoded TCRTE scores with real measured scores.

        Called by every framework as the LAST step before returning. This is
        the invisible driver that ensures every prompt reaching the user has
        been objectively evaluated and, if necessary, improved.

        Flow (for each of 3 variants, all in parallel):
          1. PromptQualityCritic.critique_prompt() → CritiqueResult
          2. If overall_score < QUALITY_GATE_THRESHOLD → enhance_from_critique()
          3. Replace hardcoded tcrte_scores with real measured scores
          4. Attach PromptQualityEvaluation to the variant

        Graceful degradation: if critique fails for any variant, that variant
        is returned unchanged with quality_evaluation.was_fallback = True.

        Args:
            response: The first-pass OptimizationResponse from the framework.
            raw_prompt: The user's original unoptimised prompt.
            task_type: The task type (reasoning, extraction, etc.).
            api_key: API key for the LLM client (for judge calls).
            quality_gate_mode: Controls critique/enhancement scope:
                - full: critique + conditional enhancement for all 3 variants
                - critique_only: critique all 3 variants, no enhancement
                - off: skip critique/enhancement entirely
                - sample_one_variant: run full mode on variant 1 only

        Returns:
            The same OptimizationResponse with refined variants and real scores.
        """
        # Lazy import to avoid circular dependency (evaluation imports LLMClient)
        from app.services.evaluation.prompt_quality_critic import PromptQualityCritic
        from app.services.evaluation.evaluation_rubric import (
            LLM_JUDGE_MODEL,
            QUALITY_GATE_THRESHOLD,
            score_to_grade,
        )
        from app.services.llm_client import LLMClient

        run_id = str(uuid4())
        response.run_metadata = OptimizationRunMetadata(
            run_id=run_id,
            raw_prompt_hash=hashlib.sha256(raw_prompt.encode("utf-8")).hexdigest(),
            framework=framework or response.analysis.framework_applied,
            judge_model=LLM_JUDGE_MODEL,
            target_model=target_model or "unknown",
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        _sync_run_usage_metadata(response)
        structlog.contextvars.bind_contextvars(run_id=run_id, framework=response.run_metadata.framework)
        logger.info(
            "optimize.run_metadata_initialized",
            run_id=run_id,
            framework=response.run_metadata.framework,
            target_model=response.run_metadata.target_model,
        )

        critic = PromptQualityCritic()
        evaluated_variant_indices = [0, 1, 2]
        allow_enhancement = quality_gate_mode == "full"

        if quality_gate_mode == "off":
            for variant in response.variants:
                variant.quality_evaluation = None
                variant.quality_scores_source = "not_evaluated"
                variant.tcrte_scores_source = "initial_framework_estimate"
            logger.info("optimize.quality_gate_skipped", mode="off", run_id=run_id)
            return response

        if quality_gate_mode == "sample_one_variant":
            evaluated_variant_indices = [0]
            allow_enhancement = True
            for idx in (1, 2):
                response.variants[idx].quality_evaluation = None
                response.variants[idx].quality_scores_source = "not_evaluated"
                response.variants[idx].tcrte_scores_source = "initial_framework_estimate"
            logger.info("optimize.quality_gate_mode", mode="sample_one_variant", run_id=run_id)

        if quality_gate_mode == "critique_only":
            allow_enhancement = False
            logger.info("optimize.quality_gate_mode", mode="critique_only", run_id=run_id)

        async def _critique_and_enhance_single_variant(variant_index: int) -> None:
            """Critique and optionally enhance one variant in-place."""
            variant = response.variants[variant_index]

            try:
                async with LLMClient(api_key=api_key) as llm_client:
                    # Step 1: Critique the variant's system prompt
                    critique = await critic.critique_prompt(
                        system_prompt=variant.system_prompt,
                        raw_prompt=raw_prompt,
                        task_type=task_type,
                        llm_client=llm_client,
                    )

                    was_enhanced = False
                    final_system_prompt = variant.system_prompt

                    # Step 2: Enhance if below quality gate
                    if (
                        allow_enhancement
                        and not critique.passed_quality_gate
                        and not critique.was_fallback
                    ):
                        enhanced_prompt = await critic.enhance_prompt_from_critique(
                            system_prompt=variant.system_prompt,
                            critique=critique,
                            task_type=task_type,
                            llm_client=llm_client,
                        )
                        if enhanced_prompt != variant.system_prompt:
                            final_system_prompt = enhanced_prompt
                            was_enhanced = True

                            logger.info(
                                "optimize.quality_gate_enhanced",
                                run_id=run_id,
                                variant_id=variant.id,
                                variant_name=variant.name,
                                score=critique.overall_score,
                                threshold=QUALITY_GATE_THRESHOLD,
                            )

                    # Step 3: Update the variant with real scores and enhanced prompt
                    variant.system_prompt = final_system_prompt
                    variant.token_estimate = len(final_system_prompt) // 4

                    # Preserve original framework TCRTE estimate for contract stability.
                    variant.tcrte_scores_source = "initial_framework_estimate"

                    # Attach quality evaluation metadata
                    fallback_gaps = [critique.reasoning] if critique.was_fallback and critique.reasoning else []
                    variant.quality_evaluation = PromptQualityEvaluation(
                        status="degraded" if critique.was_fallback else "ok",
                        overall_score=critique.overall_score,
                        grade=score_to_grade(critique.overall_score),
                        dimensions=PromptQualityDimensionScores(
                            role_clarity=critique.dimensions.role_clarity,
                            task_specificity=critique.dimensions.task_specificity,
                            constraint_completeness=critique.dimensions.constraint_completeness,
                            output_format=critique.dimensions.output_format,
                            hallucination_resistance=critique.dimensions.hallucination_resistance,
                            edge_case_handling=critique.dimensions.edge_case_handling,
                            improvement_over_raw=critique.dimensions.improvement_over_raw,
                        ),
                        strengths=critique.strengths,
                        remaining_gaps=(
                            fallback_gaps
                            if critique.was_fallback
                            else (critique.weaknesses if was_enhanced else [])
                        ),
                        was_enhanced=was_enhanced,
                        was_fallback=critique.was_fallback,
                    )
                    variant.quality_scores_source = (
                        "fallback" if critique.was_fallback else "prompt_quality_critic"
                    )
                    if critique.was_fallback:
                        logger.warning(
                            "optimize.quality_gate_fallback",
                            run_id=run_id,
                            variant_id=variant.id,
                            variant_index=variant_index,
                            reason=critique.reasoning or "unspecified",
                        )

            except Exception as variant_error:
                logger.warning(
                    "optimize.quality_gate_failed",
                    run_id=run_id,
                    variant_id=variant.id,
                    variant_index=variant_index,
                    error=str(variant_error),
                )
                variant.quality_evaluation = PromptQualityEvaluation(
                    status="failed",
                    overall_score=None,
                    grade=score_to_grade(0),
                    dimensions=PromptQualityDimensionScores(
                        role_clarity=0,
                        task_specificity=0,
                        constraint_completeness=0,
                        output_format=0,
                        hallucination_resistance=0,
                        edge_case_handling=0,
                        improvement_over_raw=0,
                    ),
                    strengths=[],
                    remaining_gaps=[f"Critique unavailable: {variant_error}"],
                    was_enhanced=False,
                    was_fallback=True,
                )
                variant.quality_scores_source = "fallback"
                variant.tcrte_scores_source = "initial_framework_estimate"
                logger.warning(
                    "optimize.quality_gate_hard_failure",
                    run_id=run_id,
                    variant_id=variant.id,
                    variant_index=variant_index,
                    reason=str(variant_error),
                )

        # Run selected variant critiques in parallel for minimal latency.
        await asyncio.gather(
            *(_critique_and_enhance_single_variant(idx) for idx in evaluated_variant_indices)
        )
        _sync_run_usage_metadata(response)
        logger.info(
            "optimize.quality_gate_completed",
            run_id=run_id,
            evaluated_variants=len(evaluated_variant_indices),
            mode=quality_gate_mode,
        )

        return response


class OptimizerFactory:
    """
    Factory that resolves a framework ID string to its concrete strategy instance.

    The registry maps EXACTLY the framework IDs used by the frontend dropdown
    and the framework_selector auto-select logic. If a framework ID is not
    recognised, ValueError is raised immediately (fail-fast principle) rather
    than silently routing to an unrelated framework.

    Usage:
        strategy = OptimizerFactory.get_optimizer("kernel")
        response = await strategy.generate_variants(request=request, ...)
    """

    # ──────────────────────────────────────────────────────────────────────
    # Registry: framework_id → Strategy class
    #
    # NOTE: "auto" is NOT here. Auto-select logic in framework_selector.py
    # resolves "auto" to a concrete framework_id BEFORE calling the factory.
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_optimizer(framework_id: str) -> BaseOptimizerStrategy:
        """
        Resolve a framework ID to its concrete optimizer strategy.

        Args:
            framework_id: One of: kernel, xml_structured, create, progressive,
                          reasoning_aware, cot_ensemble, tcrte, textgrad,
                          overshoot_undershoot, core_attention, ral_writer,
                          opro, sammo.

        Returns:
            An instance of the corresponding BaseOptimizerStrategy subclass.

        Raises:
            ValueError: If framework_id is not recognised (fail-fast).
        """
        # Lazy imports to prevent circular dependencies
        from app.services.optimization.frameworks.kernel_optimizer import KernelOptimizer
        from app.services.optimization.frameworks.xml_structured_optimizer import XmlStructuredOptimizer
        from app.services.optimization.frameworks.create_optimizer import CreateOptimizer
        from app.services.optimization.frameworks.progressive_disclosure_optimizer import ProgressiveDisclosureOptimizer
        from app.services.optimization.frameworks.reasoning_aware_optimizer import ReasoningAwareOptimizer
        from app.services.optimization.frameworks.cot_ensemble_optimizer import ChainOfThoughtEnsembleOptimizer
        from app.services.optimization.frameworks.tcrte_coverage_optimizer import TcrteCoverageOptimizer
        from app.services.optimization.frameworks.textgrad_iterative_optimizer import TextGradIterativeOptimizer
        from app.services.optimization.frameworks.overshoot_undershoot_optimizer import OvershootUndershootOptimizer
        from app.services.optimization.frameworks.core_attention_optimizer import CoreAttentionOptimizer
        from app.services.optimization.frameworks.ral_writer_optimizer import RalWriterOptimizer
        from app.services.optimization.frameworks.opro_trajectory_optimizer import OproTrajectoryOptimizer
        from app.services.optimization.frameworks.sammo_topological_optimizer import SammoTopologicalOptimizer

        FRAMEWORK_REGISTRY: dict[str, type[BaseOptimizerStrategy]] = {
            "kernel": KernelOptimizer,
            "xml_structured": XmlStructuredOptimizer,
            "create": CreateOptimizer,
            "progressive": ProgressiveDisclosureOptimizer,
            "reasoning_aware": ReasoningAwareOptimizer,
            "cot_ensemble": ChainOfThoughtEnsembleOptimizer,
            "tcrte": TcrteCoverageOptimizer,
            "textgrad": TextGradIterativeOptimizer,
            "overshoot_undershoot": OvershootUndershootOptimizer,
            "core_attention": CoreAttentionOptimizer,
            "ral_writer": RalWriterOptimizer,
            "opro": OproTrajectoryOptimizer,
            "sammo": SammoTopologicalOptimizer,
        }

        strategy_class = FRAMEWORK_REGISTRY.get(framework_id)

        if strategy_class is None:
            available_framework_ids = ", ".join(sorted(FRAMEWORK_REGISTRY.keys()))
            raise ValueError(
                f"Unrecognised framework ID '{framework_id}'. "
                f"Available frameworks: {available_framework_ids}"
            )

        return strategy_class()

    @staticmethod
    def list_available_framework_ids() -> list[str]:
        """Return sorted list of all registered framework IDs."""
        return [
            "core_attention",
            "cot_ensemble",
            "create",
            "kernel",
            "opro",
            "overshoot_undershoot",
            "progressive",
            "ral_writer",
            "reasoning_aware",
            "sammo",
            "tcrte",
            "textgrad",
            "xml_structured",
        ]
