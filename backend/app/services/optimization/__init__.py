"""
Optimization services for APOST.

Exports the OptimizerFactory (which resolves all 8 framework strategy classes),
the kNN few-shot retriever for CoT Ensemble, and the shared enhancement utilities.

MODULE STRUCTURE:
  optimization/
    __init__.py                      ← This file (public exports)
    base.py                          ← Abstract Strategy + Factory
    optimizer_configuration.py       ← Central config (models, tokens, thresholds)
    enhancements.py                  ← Shared utilities (CoRe, RAL-Writer, Prefill, etc.)
    knn_retriever.py                 ← Gemini embedding kNN for CoT Ensemble
    few_shot_corpus.py               ← Curated few-shot example corpus
    frameworks/                      ← ALL 8 concrete Strategy classes
      kernel_optimizer.py
      xml_structured_optimizer.py
      create_optimizer.py
      progressive_disclosure_optimizer.py
      reasoning_aware_optimizer.py
      cot_ensemble_optimizer.py      ← NEW
      tcrte_coverage_optimizer.py    ← NEW
      textgrad_iterative_optimizer.py← NEW
"""

from .knn_retriever import retrieve_k_nearest, precompute_corpus_embeddings
from .base import OptimizerFactory, BaseOptimizerStrategy

__all__ = [
    "retrieve_k_nearest",
    "precompute_corpus_embeddings",
    "OptimizerFactory",
    "BaseOptimizerStrategy",
]
