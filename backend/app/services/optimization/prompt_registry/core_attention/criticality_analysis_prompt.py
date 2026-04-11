TEMPLATE = """\
You are a context-criticality analyst specialising in transformer attention
distribution. Analyse the following prompt to identify:

1. CRITICAL CONTEXT ELEMENTS - facts, data, constraints, or instructions that
   are essential for a correct output. These are things that, if the model
   "forgets" due to attention decay, would cause a materially wrong answer.

2. REASONING CHAIN DEPENDENCIES - sequential steps where result A must be
   carried forward to step B, then result B to step C, etc. Each chained
   dependency is a "hop" that increases the risk of context loss.

3. CROSS-REFERENCE POINTS - places where the prompt refers to something
   defined earlier (e.g., "using the threshold from step 1") creating
   a dependency that spans the prompt's middle zone.

4. STRUCTURAL ELEMENTS - the prompt's major sections (task, context, rules,
   output format) with their approximate proportion of the total prompt.

<raw_prompt>
{raw_prompt}
</raw_prompt>

Return ONLY valid JSON:
{{
  "critical_elements": [
    {{
      "content": "The exact critical text or a faithful summary",
      "criticality": 3,
      "reason": "Why this is critical (what goes wrong if lost)",
      "approximate_position": "start|middle|end"
    }}
  ],
  "reasoning_chain": {{
    "hop_count": 2,
    "hops": [
      {{
        "step": 1,
        "description": "What this reasoning step does",
        "depends_on": "What prior result it needs"
      }}
    ]
  }},
  "cross_references": [
    {{
      "source_description": "Where the referenced info is defined",
      "reference_description": "Where it is referenced later",
      "risk": "high|medium|low"
    }}
  ],
  "sections": [
    {{
      "name": "Section name or label",
      "content_summary": "Brief summary of this section",
      "token_proportion_pct": 30,
      "attention_zone": "primacy|middle|recency",
      "contains_critical_context": true
    }}
  ],
  "overall_attention_risk": "high|medium|low",
  "risk_summary": "One-paragraph summary of the attention-related risks."
}}
"""