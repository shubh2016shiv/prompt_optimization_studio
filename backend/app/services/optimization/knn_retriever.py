"""
Medprompt kNN Few-Shot Retriever — Gemini Embedding API + Cosine Similarity

Few-shot prompting works best when the demonstration examples are semantically close
to the current query. Random or static example selection ignores this and consistently
underperforms dynamic retrieval by 5-15% on reasoning benchmarks (Nori et al., 2023,
"Can Generalist Foundation Models Outcompete Special-Purpose Tuning?"). The Medprompt
pattern — originally developed to push GPT-4 to exceed specialist model performance
on medical licensing exams — makes few-shot selection adaptive: for each new query,
find the k training examples most similar to it in embedding space and inject them as
demonstrations. The model then sees examples whose transformations are structurally
analogous to the task at hand, rather than generic examples that may introduce
irrelevant patterns.

This module implements that retrieval using the Gemini Embedding API
(models/gemini-embedding-001, the GA production model confirmed working on this
account). The model uses Matryoshka Representation Learning (MRL), which means the
first N dimensions of its 3072-dimensional output are a valid, high-quality embedding
at that reduced size. We request output_dimensionality=768, which gives vectors that
are 4× smaller than the default (reducing memory and cosine similarity compute time)
while retaining strong semantic fidelity.

Corpus embeddings for all task types are pre-computed once at server startup and
stored in memory (see precompute_corpus_embeddings). Each subsequent inference
request needs only one embedding call — for the query prompt — before doing a
fast in-memory cosine similarity against the pre-computed corpus vectors.

The Gemini API is called via the existing httpx client using the GOOGLE_API_KEY
already present in .env. No new Python dependencies beyond numpy (for vector math).

Use this module when framework == "cot_ensemble". The retrieved examples with their
reasoning traces are injected into the optimizer prompt in a structured XML block so
the main LLM can pattern-match its transformation against real examples rather than
generating from scratch.

Do NOT call this module if the GOOGLE_API_KEY is absent or the corpus is not
pre-computed (app.state.few_shot_corpus is None). The optimizer_builder.py checks
this and falls back to LLM-generated examples gracefully.

Cost: 1 Gemini embedding API call per optimize request (query only; corpus is cached).
Each call is approximately 1,000-5,000 input tokens depending on prompt length,
billed at Gemini embedding rates (very low — embedding models are cheaper than chat).
Latency: ~200-500ms for the embedding call + negligible compute for cosine similarity.

Pre-computation cost: 1 embedding call per corpus entry at startup. With the default
corpus of ~25 entries this is ~25 calls, completing in under 10 seconds.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx
import numpy as np

from app.observability.usage_tracking import record_usage

from .few_shot_corpus import CorpusEntry, get_corpus_for_task, CORPUS

logger = logging.getLogger(__name__)

# Gemini Embedding API — GA model with MRL support
_EMBED_MODEL = "models/gemini-embedding-001"
_EMBED_BASE_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/{_EMBED_MODEL}:embedContent"
)
# 768 dims: 4× smaller than default 3072, strong semantic quality retained via MRL
_OUTPUT_DIMENSIONALITY = 768


@dataclass
class EmbeddedEntry:
    """A corpus entry with its precomputed embedding vector."""
    entry: CorpusEntry
    embedding: np.ndarray = field(repr=False)


async def _embed_text(text: str, api_key: str) -> np.ndarray:
    """
    Call the Gemini Embedding API for a single text string.
    Returns a numpy float32 array of shape (_OUTPUT_DIMENSIONALITY,).
    """
    payload = {
        "model": _EMBED_MODEL,
        "content": {"parts": [{"text": text}]},
        "output_dimensionality": _OUTPUT_DIMENSIONALITY,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{_EMBED_BASE_URL}?key={api_key}",
            json=payload,
        )
        response.raise_for_status()

    response_payload = response.json()
    usage = response_payload.get("usageMetadata", {})
    record_usage(
        prompt_tokens=(
            usage.get("promptTokenCount", 0)
            or usage.get("totalTokenCount", 0)
        ),
        completion_tokens=0,
        call_count=1,
    )

    values = response_payload["embedding"]["values"]
    return np.array(values, dtype=np.float32)


async def precompute_corpus_embeddings(
    google_api_key: str,
) -> dict[str, list[EmbeddedEntry]]:
    """
    Pre-compute embeddings for every entry in the few-shot corpus.

    Called once at server startup (see main.py lifespan). The result is stored in
    app.state.few_shot_corpus and reused for all subsequent requests.

    Returns a dict[task_type -> list[EmbeddedEntry]].
    Raises on network errors so startup fails visibly rather than silently degrading.
    """
    logger.info("Pre-computing corpus embeddings for %d task types...", len(CORPUS))
    embedded: dict[str, list[EmbeddedEntry]] = {}

    for task_type, entries in CORPUS.items():
        embedded[task_type] = []
        for entry in entries:
            vec = await _embed_text(entry["raw_prompt"], google_api_key)
            embedded[task_type].append(EmbeddedEntry(entry=entry, embedding=vec))
            # Small delay to avoid rate limiting on startup burst
            await asyncio.sleep(0.05)

    total = sum(len(v) for v in embedded.values())
    logger.info("Corpus embeddings ready — %d entries across %d task types.", total, len(embedded))
    return embedded


async def retrieve_k_nearest(
    query: str,
    task_type: str,
    google_api_key: str,
    precomputed_corpus: dict[str, list[EmbeddedEntry]],
    k: int = 3,
) -> list[CorpusEntry]:
    """
    Retrieve the k most semantically similar corpus examples for a given query.

    Uses the pre-computed corpus embeddings (from precompute_corpus_embeddings)
    to avoid re-embedding the entire corpus on every request. Only the query
    requires a live API call.

    Falls back to the first k entries of the corpus if embedding fails (rare).
    Returns at most k entries; may return fewer if the corpus is small.
    """
    corpus_for_task: list[EmbeddedEntry] = precomputed_corpus.get(
        task_type, precomputed_corpus.get("reasoning", [])
    )

    if not corpus_for_task:
        logger.warning("No corpus entries for task_type=%s; returning empty list.", task_type)
        return []

    try:
        query_vec = await _embed_text(query, google_api_key)
    except Exception as exc:
        logger.warning("Query embedding failed (%s); falling back to first %d entries.", exc, k)
        return [e.entry for e in corpus_for_task[:k]]

    # Stack corpus embeddings into a matrix for vectorised cosine similarity
    corpus_matrix = np.stack([e.embedding for e in corpus_for_task])  # (N, D)

    # Cosine similarity: dot product of unit vectors
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)
    corpus_norms = corpus_matrix / (
        np.linalg.norm(corpus_matrix, axis=1, keepdims=True) + 1e-8
    )
    similarities = corpus_norms @ query_norm  # (N,)

    # Top-k descending
    top_k_indices = np.argsort(similarities)[-k:][::-1]
    results = [corpus_for_task[i].entry for i in top_k_indices]

    logger.debug(
        "kNN retrieval: task=%s, k=%d, top similarity=%.3f",
        task_type, k, float(similarities[top_k_indices[0]]) if len(top_k_indices) else 0,
    )
    return results
