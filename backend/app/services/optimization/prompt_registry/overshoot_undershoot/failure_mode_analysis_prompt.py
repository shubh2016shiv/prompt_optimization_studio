TEMPLATE = """\
You are an expert prompt reliability engineer. Analyse the following prompt
for BOTH classes of generation failure that LLMs commonly exhibit.

OVERSHOOT failures - the model generates too much:
  1. verbosity_risk:     No length/scope anchor -> model generates excessively long output
  2. hallucination_risk: Broad topic without source grounding -> model fabricates facts
  3. caveat_risk:        Ambiguous intent -> model hedges with disclaimers and caveats
  4. tangent_risk:       Multiple possible interpretations -> model drifts off-topic
  5. enumeration_risk:   List-like tasks without caps -> model generates endless lists

UNDERSHOOT failures - the model generates too little:
  1. completeness_risk:  Multiple sub-tasks without exhaustiveness requirement
  2. depth_risk:         Complex analysis requested but no depth/detail anchor
  3. schema_risk:        Expected structured output but no schema definition
  4. edge_case_risk:     Edge cases exist but no explicit handling requirement
  5. reasoning_risk:     Reasoning needed but no "show your work" instruction

<raw_prompt>
{raw_prompt}
</raw_prompt>

For each risk dimension, score severity as:
  0 = not applicable or already well-handled in the prompt
  1 = low risk (minor concern)
  2 = moderate risk (likely to affect output quality)
  3 = critical risk (very likely to cause failure)

Also provide evidence - a brief explanation of WHY that score was given.

Return ONLY valid JSON matching this schema:
{{
  "overshoot_risks": {{
    "verbosity_risk":     {{"severity": 0, "evidence": "string"}},
    "hallucination_risk": {{"severity": 0, "evidence": "string"}},
    "caveat_risk":        {{"severity": 0, "evidence": "string"}},
    "tangent_risk":       {{"severity": 0, "evidence": "string"}},
    "enumeration_risk":   {{"severity": 0, "evidence": "string"}}
  }},
  "undershoot_risks": {{
    "completeness_risk": {{"severity": 0, "evidence": "string"}},
    "depth_risk":        {{"severity": 0, "evidence": "string"}},
    "schema_risk":       {{"severity": 0, "evidence": "string"}},
    "edge_case_risk":    {{"severity": 0, "evidence": "string"}},
    "reasoning_risk":    {{"severity": 0, "evidence": "string"}}
  }},
  "overall_overshoot_score": 0,
  "overall_undershoot_score": 0,
  "dominant_failure_mode": "overshoot|undershoot|balanced",
  "summary": "One-paragraph summary of the prompt's failure mode landscape."
}}
"""