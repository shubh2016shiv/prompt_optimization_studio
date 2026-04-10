"""
Comprehensive Optimizer Framework Test Suite

Tests all 8 APOST optimization frameworks end-to-end with REAL LLM API calls
using healthcare-specific prompts. This is NOT a unit test with mocks — it
validates that each framework can actually communicate with the LLM,
extract components, assemble variants, and return a valid OptimizationResponse.

USAGE:
  cd d:\\Generative AI Portfolio Projects\\APOST\\backend
  python test_optimizers_locally.py

REQUIREMENTS:
  - OPENAI_API_KEY must be set in .env (used for gpt-4.1-nano sub-calls)
  - No other API keys required (all frameworks route through user's key)

TEST PROMPTS:
  Each framework is tested with a domain-specific healthcare prompt that
  exercises its unique capabilities:
    KERNEL          → Simple clinical extraction task
    XML Structured  → Multi-document medication reconciliation
    CREATE          → Patient education content generation
    Progressive     → Multi-step clinical decision support agent
    Reasoning-Aware → Diagnostic reasoning for an o-series model
    CoT Ensemble    → Complex adverse drug interaction analysis
    TCRTE Coverage  → Severely underspecified prompt needing gap-fill
    TextGrad        → Iterative refinement of a drug interaction review
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load .env from backend directory
BACKEND_DIRECTORY = Path(__file__).resolve().parent
ENV_FILE_PATH = BACKEND_DIRECTORY / ".env"
load_dotenv(ENV_FILE_PATH)

from app.models.requests import OptimizationRequest
from app.services.optimization.base import OptimizerFactory


# ══════════════════════════════════════════════════════════════════════════════
# Healthcare Test Prompts — one per framework
# ══════════════════════════════════════════════════════════════════════════════

HEALTHCARE_TEST_PROMPTS = {
    "kernel": """
Extract the primary diagnosis, ICD-10 code, and severity level from the
following clinical note. Return as structured JSON with fields:
diagnosis, icd10_code, severity (mild/moderate/severe).
Clinical note: Patient presents with acute exacerbation of COPD with
increased dyspnea and productive cough with purulent sputum for 3 days.
SpO2 92% on room air. Chest X-ray shows hyperinflation.
    """,

    "xml_structured": """
You are a medication reconciliation expert. Given the patient's hospital
admission medication list and their community pharmacy records, identify
discrepancies. The patient's admission list shows: Metformin 500mg BID,
Lisinopril 10mg daily, Aspirin 81mg daily. The pharmacy records show:
Metformin 1000mg BID, Lisinopril 20mg daily, Aspirin 81mg daily, and
Atorvastatin 40mg daily which is not on the admission list. Flag each
discrepancy with severity (critical/moderate/informational).
    """,

    "create": """
Create patient education materials for a newly diagnosed Type 2 diabetes
patient. The materials should explain what diabetes is, why blood sugar
monitoring is important, basic dietary guidelines, the importance of
exercise, and when to seek emergency care.
    """,

    "progressive": """
You are a clinical decision support agent for emergency department triage.
When a patient presents, you must:
1. Assess chief complaint and vital signs
2. Apply the Emergency Severity Index (ESI) algorithm
3. Check for red flags (chest pain, stroke symptoms, anaphylaxis)
4. Assign triage level 1-5
5. Generate appropriate orders based on triage level
Handle edge cases like pediatric patients differently.
    """,

    "reasoning_aware": """
Given the following patient presentation, determine the most likely
diagnosis using differential diagnosis methodology. Patient: 65-year-old
male with sudden onset crushing chest pain radiating to left arm,
diaphoresis, nausea. ECG shows ST elevation in leads II, III, aVF.
Troponin I elevated at 2.5 ng/mL. History of hypertension and smoking.
Think step by step about the differential and explain your reasoning.
    """,

    "cot_ensemble": """
A 72-year-old patient with atrial fibrillation is on warfarin (INR target
2.0-3.0). They've just been prescribed fluconazole for a fungal infection
and started on amiodarone for rate control. Current INR is 2.8. Recent labs
show mild hepatic impairment (ALT 65 U/L). Assess the cumulative drug
interaction risk, predict INR trajectory, and recommend dosage adjustments
with supporting clinical reasoning.
    """,

    "tcrte": """
Analyze the patient data and tell me what's wrong.
    """,

    "textgrad": """
Review the patient's medication list and check for drug interactions.
The patient takes warfarin 5mg, amiodarone 200mg, and metoprolol 50mg.
Let me know the results.
    """,
}

# Simulated gap analysis data for the TCRTE optimizer test
SIMULATED_GAP_DATA_FOR_TCRTE = {
    "tcrte": {
        "task": {"score": 25, "status": "missing", "note": "No measurable output defined"},
        "context": {"score": 15, "status": "missing", "note": "No domain or patient info specified"},
        "role": {"score": 0, "status": "missing", "note": "No role defined"},
        "tone": {"score": 0, "status": "missing", "note": "No audience or formality specified"},
        "execution": {"score": 20, "status": "missing", "note": "No output format defined"},
    },
    "overall_score": 12,
    "complexity": "medium",
    "recommended_techniques": ["TCRTE"],
}

SIMULATED_GAP_ANSWERS_FOR_TCRTE = {
    "What domain is this analysis for?": "Cardiology — post-cardiac catheterisation monitoring",
    "What specific output do you need?": "JSON risk assessment with severity, findings, and recommendations",
    "Who is the intended audience?": "Attending cardiologist in the cath lab",
}


# ══════════════════════════════════════════════════════════════════════════════
# Test Runner
# ══════════════════════════════════════════════════════════════════════════════

async def test_single_framework(
    framework_id: str,
    test_prompt: str,
    api_key: str,
    gap_data: dict | None = None,
    answers: dict[str, str] | None = None,
) -> dict:
    """
    Test a single framework end-to-end with a real LLM API call.

    Returns a dict with: framework_id, status ("PASS"/"FAIL"), duration_seconds,
    variant_count, error_message (if any).
    """
    request = OptimizationRequest(
        raw_prompt=test_prompt,
        provider="openai",
        model_id="gpt-4.1-nano",
        model_label="GPT-4.1 Nano",
        task_type="analysis",
        framework=framework_id,
        is_reasoning_model=(framework_id == "reasoning_aware"),
        gap_data=gap_data,
        answers=answers,
        api_key=api_key,
    )

    start_time = time.time()

    try:
        strategy = OptimizerFactory.get_optimizer(framework_id)
        result = await strategy.generate_variants(request=request)
        duration = time.time() - start_time

        # Validate the response structure
        assert result.analysis is not None, "Missing analysis"
        assert result.analysis.framework_applied == framework_id, (
            f"Expected framework '{framework_id}', got '{result.analysis.framework_applied}'"
        )
        assert len(result.variants) == 3, f"Expected 3 variants, got {len(result.variants)}"

        # Collect quality scores for each variant
        quality_scores = []
        for variant in result.variants:
            assert variant.system_prompt, f"Variant {variant.id} has empty system_prompt"
            assert variant.name in ("Conservative", "Structured", "Advanced"), (
                f"Unexpected variant name: {variant.name}"
            )
            assert variant.token_estimate > 0, f"Variant {variant.id} has zero token_estimate"

            # Quality evaluation assertions
            if variant.quality_evaluation is not None:
                qe = variant.quality_evaluation
                assert 0 <= qe.overall_score <= 100, (
                    f"Variant {variant.id} quality score out of range: {qe.overall_score}"
                )
                assert qe.grade in ("A", "B", "C", "D", "F"), (
                    f"Variant {variant.id} invalid grade: {qe.grade}"
                )
                quality_scores.append({
                    "variant_id": variant.id,
                    "variant_name": variant.name,
                    "overall_score": qe.overall_score,
                    "grade": qe.grade,
                    "was_enhanced": qe.was_enhanced,
                    "role_clarity": qe.dimensions.role_clarity,
                    "task_specificity": qe.dimensions.task_specificity,
                    "constraint_completeness": qe.dimensions.constraint_completeness,
                    "output_format": qe.dimensions.output_format,
                    "hallucination_resistance": qe.dimensions.hallucination_resistance,
                    "edge_case_handling": qe.dimensions.edge_case_handling,
                    "improvement_over_raw": qe.dimensions.improvement_over_raw,
                })
            else:
                quality_scores.append({
                    "variant_id": variant.id,
                    "variant_name": variant.name,
                    "overall_score": None,
                    "grade": "N/A",
                    "was_enhanced": False,
                })

        return {
            "framework_id": framework_id,
            "status": "PASS",
            "duration_seconds": round(duration, 2),
            "variant_count": len(result.variants),
            "token_estimates": [v.token_estimate for v in result.variants],
            "techniques_applied": result.techniques_applied,
            "quality_scores": quality_scores,
            "error_message": None,
        }

    except Exception as error:
        duration = time.time() - start_time
        import traceback
        return {
            "framework_id": framework_id,
            "status": "FAIL",
            "duration_seconds": round(duration, 2),
            "variant_count": 0,
            "token_estimates": [],
            "techniques_applied": [],
            "error_message": f"{type(error).__name__}: {str(error)}",
            "traceback": traceback.format_exc(),
        }


async def run_all_framework_tests():
    """
    Run end-to-end tests for all 8 frameworks sequentially.
    Prints a summary table at the end.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-ant") or len(api_key) < 20:
        print("=" * 80)
        print("ERROR: Valid OPENAI_API_KEY not found in .env")
        print(f"  Looked in: {ENV_FILE_PATH}")
        print("  The test uses gpt-4.1-nano for all framework sub-calls.")
        print("=" * 80)
        sys.exit(1)

    # All 8 frameworks in the order they appear in the documentation
    frameworks_to_test = [
        "kernel",
        "xml_structured",
        "create",
        "progressive",
        "reasoning_aware",
        "cot_ensemble",
        "tcrte",
        "textgrad",
    ]

    print("=" * 80)
    print("  APOST Optimizer Framework Test Suite")
    print("  Testing all 8 frameworks with healthcare prompts")
    print(f"  API Key: {api_key[:12]}...{api_key[-4:]}")
    print(f"  Model: gpt-4.1-nano")
    print("=" * 80)

    results: list[dict] = []
    total_start_time = time.time()

    for framework_id in frameworks_to_test:
        test_prompt = HEALTHCARE_TEST_PROMPTS[framework_id]

        # Special handling for frameworks that need gap data
        gap_data = SIMULATED_GAP_DATA_FOR_TCRTE if framework_id == "tcrte" else None
        answers = SIMULATED_GAP_ANSWERS_FOR_TCRTE if framework_id == "tcrte" else None

        print(f"\n{'─' * 60}")
        print(f"  Testing: {framework_id.upper()}")
        print(f"  Prompt: {test_prompt.strip()[:80]}...")
        print(f"{'─' * 60}")

        result = await test_single_framework(
            framework_id=framework_id,
            test_prompt=test_prompt,
            api_key=api_key,
            gap_data=gap_data,
            answers=answers,
        )
        results.append(result)

        # Print immediate result
        status_icon = "✓" if result["status"] == "PASS" else "✗"
        print(f"  {status_icon} {result['status']} ({result['duration_seconds']}s)")

        if result["status"] == "PASS":
            print(f"    Variants: {result['variant_count']}")
            print(f"    Token estimates: {result['token_estimates']}")
            print(f"    Techniques: {result['techniques_applied']}")

            # Print quality evaluation table for each variant
            if result.get("quality_scores"):
                print(f"    {'─' * 50}")
                print(f"    QUALITY EVALUATION (PromptQualityCritic):")
                for qs in result["quality_scores"]:
                    if qs.get("overall_score") is not None:
                        enhanced_marker = " ★ENHANCED" if qs["was_enhanced"] else ""
                        print(f"      V{qs['variant_id']} ({qs['variant_name']:12s}) "
                              f"│ Score: {qs['overall_score']:3d}/100 "
                              f"│ Grade: {qs['grade']}{enhanced_marker}")
                        print(f"        Role:{qs.get('role_clarity', 'N/A'):>4}  "
                              f"Task:{qs.get('task_specificity', 'N/A'):>4}  "
                              f"Constraints:{qs.get('constraint_completeness', 'N/A'):>4}  "
                              f"Format:{qs.get('output_format', 'N/A'):>4}  "
                              f"Halluc:{qs.get('hallucination_resistance', 'N/A'):>4}  "
                              f"Edge:{qs.get('edge_case_handling', 'N/A'):>4}  "
                              f"Delta:{qs.get('improvement_over_raw', 'N/A'):>4}")
                    else:
                        print(f"      V{qs['variant_id']} ({qs['variant_name']:12s}) │ Quality evaluation unavailable")
        else:
            print(f"    Error: {result['error_message']}")
            if "traceback" in result:
                # Print first 5 lines of traceback for debugging
                tb_lines = result["traceback"].strip().split("\n")
                for line in tb_lines[-5:]:
                    print(f"    {line}")

    total_duration = time.time() - total_start_time

    # ── Summary Table ─────────────────────────────────────────────────────
    print("\n")
    print("=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)
    print(f"  {'Framework':<20} {'Status':<8} {'Duration':<10} {'Variants':<10} {'Techniques'}")
    print(f"  {'─' * 20} {'─' * 8} {'─' * 10} {'─' * 10} {'─' * 25}")

    pass_count = 0
    fail_count = 0

    for result in results:
        status = result["status"]
        duration = f"{result['duration_seconds']}s"
        variants = str(result["variant_count"])
        techniques = ", ".join(result["techniques_applied"][:3]) if result["techniques_applied"] else "N/A"

        if status == "PASS":
            pass_count += 1
        else:
            fail_count += 1

        print(f"  {result['framework_id']:<20} {status:<8} {duration:<10} {variants:<10} {techniques}")

    # ── Quality Score Summary Table ───────────────────────────────────────
    print(f"\n{'=' * 80}")
    print("  QUALITY EVALUATION SUMMARY (PromptQualityCritic G-Eval Scores)")
    print(f"{'=' * 80}")
    print(f"  {'Framework':<18} {'V1 Score':>8} {'V2 Score':>8} {'V3 Score':>8}  {'Best':>4}  {'Enhanced?'}")
    print(f"  {'─' * 18} {'─' * 8} {'─' * 8} {'─' * 8}  {'─' * 4}  {'─' * 12}")

    for result in results:
        if result["status"] == "PASS" and result.get("quality_scores"):
            scores = result["quality_scores"]
            v1_score = scores[0].get("overall_score", "N/A") if len(scores) > 0 else "N/A"
            v2_score = scores[1].get("overall_score", "N/A") if len(scores) > 1 else "N/A"
            v3_score = scores[2].get("overall_score", "N/A") if len(scores) > 2 else "N/A"

            # Find best variant
            valid_scores = [(s["variant_id"], s["overall_score"]) for s in scores if s.get("overall_score") is not None]
            best = f"V{max(valid_scores, key=lambda x: x[1])[0]}" if valid_scores else "N/A"

            # Count enhanced variants
            enhanced_list = [f"V{s['variant_id']}" for s in scores if s.get("was_enhanced")]
            enhanced_str = ", ".join(enhanced_list) if enhanced_list else "None"

            v1_str = f"{v1_score:>3}({scores[0].get('grade', '?')})" if isinstance(v1_score, int) else f"{'N/A':>8}"
            v2_str = f"{v2_score:>3}({scores[1].get('grade', '?')})" if isinstance(v2_score, int) else f"{'N/A':>8}"
            v3_str = f"{v3_score:>3}({scores[2].get('grade', '?')})" if isinstance(v3_score, int) else f"{'N/A':>8}"

            print(f"  {result['framework_id']:<18} {v1_str:>8} {v2_str:>8} {v3_str:>8}  {best:>4}  {enhanced_str}")
        else:
            print(f"  {result['framework_id']:<18} {'SKIPPED (test failed)'}")

    print(f"\n  Total: {pass_count} PASSED, {fail_count} FAILED")
    print(f"  Total duration: {round(total_duration, 2)}s")
    print("=" * 80)

    # Exit with error code if any tests failed
    if fail_count > 0:
        print(f"\n  ⚠ {fail_count} framework(s) failed. See details above.")
        sys.exit(1)
    else:
        print(f"\n  ✓ All {pass_count} frameworks passed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_all_framework_tests())
