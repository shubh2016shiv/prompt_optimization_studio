# Prompt Optimization Framework Audit

Date: 2026-04-11

This note captures the latest live audit of the prompt optimization frameworks in APOST using the healthcare sample usage harness.

Scope:
- Latest documentation only: `documentations/prompt_optimization_frameworks`
- Live verification target: `backend/sample_usage/run_framework_*_suite.py`
- Evidence source: newest markdown artifacts under `backend/sample_usage/prompt_output/<framework>/<timestamp>/`

## Overall Result

All 13 prompt optimization frameworks completed successfully in the latest live reruns after the Docker rebuild.

For the tested healthcare scenarios, each framework:
- followed the algorithmic behavior described in its latest documentation,
- produced outputs that matched the expected framework style,
- and returned evaluation results consistent with the framework's intended scoring / critique flow.

## Framework-by-Framework Audit

| Framework | Implementation vs docs | Output behavior | Evaluation behavior | Notes |
|---|---|---|---|---|
| `kernel` | Pass | Pass | Pass | Deep rewrite flow appears as documented. |
| `xml_structured` | Pass | Pass | Pass | XML/ontology-style restructuring behaves as expected. |
| `create` | Pass | Pass | Pass | CREATE-style structural rewrite is consistent with the doc. |
| `progressive` | Pass | Pass | Pass | Stepwise layered rewrite behavior matches the documentation. |
| `reasoning_aware` | Pass | Pass | Pass | Reasoning hooks are suppressed and rewritten declaratively as expected. |
| `cot_ensemble` | Pass | Pass | Pass | Now correctly uses KNN few-shot retrieval and ensemble synthesis. |
| `tcrte` | Pass | Pass | Pass | Coverage repair and missing-dimension filling are visible in the outputs. |
| `textgrad` | Pass | Pass | Pass | Iterative refinement runs cleanly and no longer falls back in the latest rerun. |
| `overshoot_undershoot` | Pass | Pass | Pass | Guard selection follows the dominant failure mode in the current run. |
| `core_attention` | Pass | Pass | Pass | CoRe-style attention analysis and redistribution are present. |
| `ral_writer` | Pass | Pass | Pass | Hard constraint extraction and recency echo behave as expected. |
| `opro` | Pass | Pass | Pass, with caveat | Works end-to-end now, but the sample harness still uses a deliberately bounded 1-case evaluation dataset, so robustness is narrower than a full search setup. |
| `sammo` | Pass | Pass | Pass | Candidate mutation and topology selection are consistent with the framework design. |

## Key Notes

- Auto mode policy update: when `framework="auto"`, routing is restricted to the ROI-approved set only (`create`, `xml_structured`, `core_attention`, `ral_writer`, `cot_ensemble`, `overshoot_undershoot`, `textgrad`, `kernel`, `tcrte`, `reasoning_aware`).
- The earlier `HTTP 502` / `Name or service not known` failures were transient runtime/network issues rather than framework logic failures.
- The judge fallback issue that previously showed zero-quality variants has been hardened and was no longer present in the latest reruns.
- `CoT Ensemble` now reflects the updated healthcare few-shot corpus and cache fingerprint behavior.
- `OPRO` is functioning again, but it should be revisited later if you want a broader evaluation dataset in the harness.

## Evidence Locations

- `backend/sample_usage/prompt_output/kernel/20260411_184418/_summary.md`
- `backend/sample_usage/prompt_output/xml_structured/20260411_184602/_summary.md`
- `backend/sample_usage/prompt_output/create/20260411_184828/_summary.md`
- `backend/sample_usage/prompt_output/progressive/20260411_185009/_summary.md`
- `backend/sample_usage/prompt_output/reasoning_aware/20260411_185242/_summary.md`
- `backend/sample_usage/prompt_output/cot_ensemble/20260411_185319/_summary.md`
- `backend/sample_usage/prompt_output/tcrte/20260411_185410/_summary.md`
- `backend/sample_usage/prompt_output/textgrad/20260411_191643/_summary.md`
- `backend/sample_usage/prompt_output/overshoot_undershoot/20260411_191145/_summary.md`
- `backend/sample_usage/prompt_output/core_attention/20260411_190853/_summary.md`
- `backend/sample_usage/prompt_output/ral_writer/20260411_191326/_summary.md`
- `backend/sample_usage/prompt_output/opro/20260411_192027/_summary.md`
- `backend/sample_usage/prompt_output/sammo/20260411_191430/_summary.md`

## Follow-Up Review Items

1. Broaden the OPRO evaluation dataset in the sample harness if you want stronger empirical-search realism.
2. Re-run the full framework sweep after any future judge-model or provider changes.
3. Keep this audit note updated when the latest docs change.
