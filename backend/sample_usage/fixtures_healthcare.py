"""
Healthcare-themed fixtures for APOST API sample runs.

Scenario: a clinical decision support style prompt that consumes structured EHR-style
inputs (formulary, meds, LOINC labs, vitals) and returns strict JSON. This exercises
task_type, input_variables, and rich context — aligned with APOST doc §9 workflows.
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Raw prompt — intentionally dense so TCRTE gap analysis has material to score.
# -----------------------------------------------------------------------------
RAW_PROMPT = """
You are a clinical informatics assistant supporting licensed clinicians (not patients).

Given the structured inputs below, produce a single JSON object with these keys:
  "formulary_alerts": array of { "medication", "tier_or_status", "suggested_action" }
  "interaction_flags": array of { "pair", "severity_estimate", "evidence_level", "counseling_note" }
  "lab_summary": array of { "loinc_code", "name", "value", "unit", "interpretation_hint" }
  "vitals_trend_bullets": array of short strings (max 120 chars each)
  "disclaimers": array of strings stating limits of this analysis

Rules:
- Never diagnose. Use hedged clinical language ("may warrant review", "consider").
- If data is missing, state "insufficient_data" in the relevant section.
- Prefer RxNorm concept names when listing medications; include generic names.
- For LOINC, echo the exact code from input (e.g. 4548-4 for HbA1c).
- Output JSON only, no markdown fences.
""".strip()

# -----------------------------------------------------------------------------
# Declared template variables — matches how the UI passes input_variables to gap + optimize.
# -----------------------------------------------------------------------------
INPUT_VARIABLES = """
{{patient_context}} — age band, problems list, allergies (ICD-10 / free text)
{{active_medications}} — list of { rxnorm_id, name, dose, route, frequency }
{{formulary_json}} — payer formulary: tier, PA requirements, exclusions
{{loinc_results}} — labs: LOINC code, value, unit, reference range, collection time
{{vitals}} — BP, HR, RR, SpO2, temp with units and timestamps
""".strip()

# Default task type for this scenario (Q&A / RAG-like structured grounding)
TASK_TYPE = "qa"

# Example gap interview answers (optional second optimize call) — short, realistic
SAMPLE_GAP_ANSWERS: dict[str, str] = {
    "q1": "Severity labels must map to institution policy: critical / high / moderate / low only.",
    "q2": "Target audience is attending physicians and clinical pharmacists in ambulatory care.",
}
