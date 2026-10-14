"""Thin wrapper around the OpenAI embeddings API (batching + one retry)."""
from __future__ import annotations

import logging
import time

from app.config import get_settings
from app.exceptions import ConfigError, EmbeddingError

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self, client=None, model: str | None = None, batch_size: int | None = None):
        settings = get_settings()
        self.model = model or settings.embedding_model
        self.batch_size = batch_size or settings.embed_batch_size
        if client is None:
            if not settings.openai_api_key:
                raise ConfigError("OPENAI_API_KEY is not set. Add it to your .env file.")
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
        self._client = client

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed many texts. Output order always matches input order."""
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            vectors.extend(self._embed_batch(texts[start : start + self.batch_size]))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in (1, 2):  # try once, then retry once
            try:
                response = self._client.embeddings.create(model=self.model, input=batch)
                ordered = sorted(response.data, key=lambda item: item.index)
                return [item.embedding for item in ordered]
            except Exception as exc:  # network, rate limit, bad key, ...
                last_error = exc
                logger.warning("Embedding attempt %d failed: %s", attempt, exc)
                if attempt == 1:
                    time.sleep(1.5)
        raise EmbeddingError("The embedding service failed. Please try again.") from last_error
