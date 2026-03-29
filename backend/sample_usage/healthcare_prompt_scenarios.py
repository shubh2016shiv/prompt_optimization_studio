"""
Purpose:
  Define a centralized healthcare prompt/scenario bank used by pipeline checks and
  framework transparency suites.

Scope:
  - Stores 10 representative healthcare capabilities/scenarios.
  - Provides a single canonical pipeline scenario and sample gap answers.
  - Exposes helper lookup for scenario retrieval by id.

Method:
  - Represent each scenario as a typed PromptCase structure.
  - Keep scenario data static and versionable in source control.

Artifacts:
  - In-memory constants consumed by test runner scripts.

Run:
  Imported by pipeline_* and framework_* sample scripts.
"""

from __future__ import annotations

from typing import TypedDict


class PromptCase(TypedDict):
    id: str
    title: str
    task_type: str
    complexity: str
    input_variables: str
    raw_prompt: str


PROMPT_CASES: list[PromptCase] = [
    {
        "id": "hc_01_med_reconciliation",
        "title": "Medication Reconciliation Risk Flags",
        "task_type": "qa",
        "complexity": "medium",
        "input_variables": (
            "{{active_meds}} - list of {name, rxnorm_id, dose, frequency}\n"
            "{{allergies}} - list of allergy strings\n"
            "{{recent_discharges}} - discharge meds and discontinuation notes"
        ),
        "raw_prompt": (
            "You are a clinical informatics assistant for hospital pharmacists. "
            "Compare active medications against allergy records and recent discharge "
            "instructions. Return strict JSON with keys: high_risk_conflicts, "
            "duplicate_therapies, unclear_orders, and recommended_followups. "
            "Never diagnose. If data is missing, output insufficient_data for that section."
        ),
    },
    {
        "id": "hc_02_triage_prioritization",
        "title": "ED Triage Prioritization Suggestions",
        "task_type": "reasoning",
        "complexity": "complex",
        "input_variables": (
            "{{chief_complaint}}\n{{vitals_stream}}\n{{known_conditions}}\n{{nurse_notes}}"
        ),
        "raw_prompt": (
            "Support emergency department triage by ranking patient review urgency. "
            "Use provided vitals and nurse notes only. Produce JSON with triage_band, "
            "top_risk_signals, missing_information, and safe_next_step. "
            "Use cautious language and include confidence low/medium/high."
        ),
    },
    {
        "id": "hc_03_lab_interpretation",
        "title": "LOINC Lab Trend Interpretation",
        "task_type": "analysis",
        "complexity": "medium",
        "input_variables": (
            "{{loinc_results}} - array of {code, value, unit, ref_range, timestamp}\n"
            "{{problem_list}}"
        ),
        "raw_prompt": (
            "Review longitudinal lab results and identify clinically relevant directionality "
            "without diagnosis. Output JSON: concerning_trends, stable_markers, "
            "possible_confounders, and recommendation_for_clinician_review. "
            "Always echo exact LOINC codes in your output."
        ),
    },
    {
        "id": "hc_04_discharge_summary",
        "title": "Discharge Summary Normalization",
        "task_type": "summarization",
        "complexity": "simple",
        "input_variables": "{{discharge_note_text}}\n{{followup_orders}}",
        "raw_prompt": (
            "Convert an unstructured discharge note into a patient-safe clinician handoff JSON "
            "with medications_to_continue, medications_to_stop, warning_signs, "
            "followup_appointments, and documentation_gaps."
        ),
    },
    {
        "id": "hc_05_prior_auth",
        "title": "Prior Authorization Evidence Packet",
        "task_type": "planning",
        "complexity": "complex",
        "input_variables": (
            "{{payer_policy}}\n{{requested_drug}}\n{{trial_history}}\n{{contraindications}}"
        ),
        "raw_prompt": (
            "Draft a prior-authorization support outline for clinicians. "
            "Output JSON with coverage_requirements_met, unmet_requirements, "
            "recommended_attachments, and appeal_talking_points. "
            "Do not invent policy clauses that are absent from input."
        ),
    },
    {
        "id": "hc_06_radiology_followup",
        "title": "Radiology Follow-up Coordination",
        "task_type": "qa",
        "complexity": "medium",
        "input_variables": "{{radiology_report}}\n{{care_team_directory}}\n{{open_tasks}}",
        "raw_prompt": (
            "Extract actionable follow-up obligations from radiology impressions. "
            "Return JSON with critical_findings, required_time_window, owner_role, "
            "and escalation_path. Include insufficient_data if ownership cannot be inferred."
        ),
    },
    {
        "id": "hc_07_infection_surveillance",
        "title": "Infection Surveillance Signal Extraction",
        "task_type": "extraction",
        "complexity": "medium",
        "input_variables": "{{microbiology_results}}\n{{antibiotic_orders}}\n{{ward_events}}",
        "raw_prompt": (
            "Identify potential hospital-acquired infection signals for infection prevention teams. "
            "Output JSON only: candidate_events, evidence_snippets, confidence_band, "
            "and immediate_review_actions."
        ),
    },
    {
        "id": "hc_08_operational_capacity",
        "title": "Bed Capacity and Throughput Brief",
        "task_type": "planning",
        "complexity": "complex",
        "input_variables": "{{bed_state}}\n{{admission_forecast}}\n{{staffing_constraints}}",
        "raw_prompt": (
            "Generate an operations brief for clinical leadership. "
            "Use provided inputs to return JSON with bottlenecks, near_term_actions, "
            "tradeoffs, and risk_if_no_action. Keep statements evidence-grounded."
        ),
    },
    {
        "id": "hc_09_patient_education",
        "title": "Patient Education Personalization",
        "task_type": "writing",
        "complexity": "simple",
        "input_variables": "{{diagnosis_context}}\n{{reading_level_target}}\n{{language_pref}}",
        "raw_prompt": (
            "Create clinician-reviewed patient education content in plain language. "
            "Return JSON with key_points, do_and_dont, when_to_seek_help, and followup_prompt. "
            "Avoid fear language and unsupported claims."
        ),
    },
    {
        "id": "hc_10_rule_validation",
        "title": "Clinical Rules Engine Test Case Generator",
        "task_type": "coding",
        "complexity": "complex",
        "input_variables": "{{rule_spec}}\n{{edge_cases}}\n{{known_failures}}",
        "raw_prompt": (
            "Generate structured test cases for a clinical rules engine. "
            "Return JSON with positive_cases, negative_cases, boundary_cases, and "
            "regression_cases. Every case must include expected_result and rationale."
        ),
    },
]

PIPELINE_CASE_ID = "hc_01_med_reconciliation"

PIPELINE_SAMPLE_GAP_ANSWERS: dict[str, str] = {
    "q1": "Severity labels must map to policy levels: critical/high/moderate/low.",
    "q2": "Primary audience is licensed clinicians and clinical pharmacists.",
}


def get_prompt_case(case_id: str) -> PromptCase:
    for case in PROMPT_CASES:
        if case["id"] == case_id:
            return case
    raise KeyError(f"Unknown healthcare prompt case: {case_id}")



