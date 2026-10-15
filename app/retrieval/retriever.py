"""Retrieval: question in, relevant chunks out.

An empty list is a meaningful answer: nothing in the documents is close enough
to the question, so the app should say "I couldn't find this" without calling the LLM.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.config import get_settings
from app.exceptions import EmptyQuestionError
from app.retrieval.store import Hit

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _default_embedder():
    from app.retrieval.embedder import Embedder

    return Embedder()


@lru_cache(maxsize=1)
def _default_store():
    from app.retrieval.store import VectorStore

    return VectorStore()


def retrieve(
    question: str,
    *,
    top_k: int | None = None,
    min_similarity: float | None = None,
    doc_ids: list[str] | None = None,
    embedder=None,
    store=None,
) -> list[Hit]:
    """Find the chunks most relevant to `question`.

    Steps: embed the question -> search the vector DB -> drop weak matches.
    Returns hits best-first. May return an empty list.
    """
    question = question.strip()
    if not question:
        raise EmptyQuestionError("Please type a question.")

    settings = get_settings()
    top_k = top_k if top_k is not None else settings.top_k
    threshold = min_similarity if min_similarity is not None else settings.min_similarity

    embedder = embedder or _default_embedder()
    store = store or _default_store()

    vector = embedder.embed_query(question)
    hits = store.search(vector, top_k=top_k, doc_ids=doc_ids)
    kept = [hit for hit in hits if hit.score >= threshold]

    logger.info(
        "Retrieved %d/%d hits above %.2f (best score: %s)",
        len(kept), len(hits), threshold, f"{hits[0].score:.2f}" if hits else "n/a",
    )
    return kept
