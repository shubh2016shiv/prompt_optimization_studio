# Framework Transparency Harness (Healthcare Scenarios)

This harness runs each optimization framework against a centralized set of 10 healthcare prompt scenarios and writes full visual outputs to markdown files.

## What You Get

- 10 centralized healthcare scenarios: `healthcare_prompt_scenarios.py`
- 8 isolated framework runner scripts:
  - `run_framework_kernel_suite.py`
  - `run_framework_xml_structured_suite.py`
  - `run_framework_create_suite.py`
  - `run_framework_progressive_suite.py`
  - `run_framework_reasoning_aware_suite.py`
  - `run_framework_cot_ensemble_suite.py`
  - `run_framework_tcrte_suite.py`
  - `run_framework_textgrad_suite.py`
- Optional all-in-one runner: `run_all_framework_suites.py`
- Full markdown output per scenario:
  - `sample_usage/prompt_output/<framework>/<timestamp>/<case_id>.md`
  - `sample_usage/prompt_output/<framework>/<timestamp>/_summary.md`

## Console Output

Each runner prints compact per-scenario summaries:

- scenario id
- status (`OK` / `FAILED`)
- framework applied (backend-reported)
- variant count
- average quality score
- fallback variant count

## Prerequisites

1. Start backend API:
   - `uvicorn app.main:app --reload --port 8000`
2. Set API key env:
   - `APOST_TEST_API_KEY` (recommended)
   - or provider-specific key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`)

## Run

From `backend/`:

- Single framework:
  - `python sample_usage/run_framework_kernel_suite.py`
- All frameworks:
  - `python sample_usage/run_all_framework_suites.py`

## Useful Env Overrides

- `APOST_SAMPLE_BASE_URL` (default: `http://127.0.0.1:8000`)
- `APOST_TEST_PROVIDER` (`openai|anthropic|google`)
- `APOST_TEST_MODEL_ID`
- `APOST_TEST_MODEL_LABEL`
- `APOST_QUALITY_GATE_MODE` (`full|critique_only|off|sample_one_variant`)
- `APOST_IS_REASONING_MODEL` (`1|true|yes`)
