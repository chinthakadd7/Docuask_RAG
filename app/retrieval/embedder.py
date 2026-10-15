"""Thin wrapper around the Gemini embeddings API (batching + retries).

Gemini embeddings work best when you say what the text is for:
  * RETRIEVAL_DOCUMENT for the chunks we store
  * RETRIEVAL_QUERY    for the user's question
"""
from __future__ import annotations

import logging
import time

from app.config import get_settings
from app.exceptions import ConfigError, EmbeddingError
from app.utils.retry import retry_delay

logger = logging.getLogger(__name__)

DOCUMENT_TASK = "RETRIEVAL_DOCUMENT"
QUERY_TASK = "RETRIEVAL_QUERY"
_ATTEMPTS = 3  # first try + 2 retries (free-tier rate limits are common)


class Embedder:
    def __init__(
        self,
        client=None,
        model: str | None = None,
        batch_size: int | None = None,
        dimensions: int | None = None,
    ):
        settings = get_settings()
        self.model = model or settings.embedding_model
        self.batch_size = batch_size or settings.embed_batch_size
        self.dimensions = dimensions or settings.embedding_dimensions
        if client is None:
            if not settings.gemini_api_key:
                raise ConfigError("GEMINI_API_KEY is not set. Add it to your .env file.")
            from google import genai

            client = genai.Client(api_key=settings.gemini_api_key)
        self._client = client

    def embed_texts(
        self, texts: list[str], task_type: str = DOCUMENT_TASK
    ) -> list[list[float]]:
        """Embed many texts. Output order always matches input order."""
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            vectors.extend(self._embed_batch(batch, task_type))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text], task_type=QUERY_TASK)[0]

    def _embed_batch(self, batch: list[str], task_type: str) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in range(1, _ATTEMPTS + 1):
            try:
                response = self._client.models.embed_content(
                    model=self.model,
                    contents=batch,
                    config={
                        "task_type": task_type,
                        "output_dimensionality": self.dimensions,
                    },
                )
                vectors = [list(e.values) for e in response.embeddings]
                if len(vectors) != len(batch):
                    raise ValueError(
                        f"Expected {len(batch)} embeddings, got {len(vectors)}"
                    )
                return vectors
            except Exception as exc:  # network, rate limit (429), bad key, ...
                last_error = exc
                logger.warning("Embedding attempt %d/%d failed: %s", attempt, _ATTEMPTS, exc)
                if attempt < _ATTEMPTS:
                    time.sleep(retry_delay(exc, attempt))
        raise EmbeddingError("The embedding service failed. Please try again.") from last_error