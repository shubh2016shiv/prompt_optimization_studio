"""
Optimization services for APOST.
Exports the TextGrad optimizer and the kNN few-shot retriever.
"""

from .textgrad_optimizer import run_textgrad_optimization
from .knn_retriever import retrieve_k_nearest, precompute_corpus_embeddings

__all__ = [
    "run_textgrad_optimization",
    "retrieve_k_nearest",
    "precompute_corpus_embeddings",
]
