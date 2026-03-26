"""
Concrete Strategy Implementations for APOST prompt optimizations.

This directory contains ALL 8 framework strategy classes that implement
the BaseOptimizerStrategy interface:

  1. kernel_optimizer.py              — KERNEL (Keep simple, Explicit, Narrow, Logical order)
  2. xml_structured_optimizer.py      — XML Structured Bounding (Anthropic-endorsed)
  3. create_optimizer.py              — CREATE (Character, Request, Examples, Adjustments, Type, Extras)
  4. progressive_disclosure_optimizer.py — Progressive Disclosure (3-Layer Agent Skills)
  5. reasoning_aware_optimizer.py     — Reasoning-Aware (for o-series / extended thinking models)
  6. cot_ensemble_optimizer.py        — CoT Ensemble / Medprompt (kNN few-shot + multi-path)
  7. tcrte_coverage_optimizer.py      — TCRTE Coverage-First (gap-filling for underspecified prompts)
  8. textgrad_iterative_optimizer.py  — TextGrad Iterative (evaluate→critique→rewrite loop)
"""
