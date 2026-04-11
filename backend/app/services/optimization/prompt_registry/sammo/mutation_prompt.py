TEMPLATE = """
Mutate this prompt graph using the requested operator while preserving task intent.

<mutation_operator>
{mutation_operator}
</mutation_operator>

<current_graph_json>
{graph_json}
</current_graph_json>

Operator semantics:
- compression: aggressively compress context_blocks while preserving critical facts.
- restructure: reorder sections and remove one low-value rule if safe.
- syntactical: rewrite instruction for maximal imperative clarity.

Return ONLY valid JSON with the same schema:
{{
  "instruction": "core instruction",
  "context_blocks": ["context block 1", "context block 2"],
  "rules": ["rule 1", "rule 2"],
  "few_shot": ["few-shot or exemplar block"],
  "output_format": "required output format and schema guidance"
}}
""".strip()