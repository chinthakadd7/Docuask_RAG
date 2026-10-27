"""Thin wrapper around Groq text generation (retries, empty-answer check)."""
from __future__ import annotations

import logging
import os
import time

from app.config import get_settings
from app.exceptions import ConfigError, GenerationError
from app.utils.retry import retry_delay

logger = logging.getLogger(__name__)

_ATTEMPTS = 4  # first try + 3 retries (free-tier limits and busy servers are common)


class Generator:
    def __init__(self, client=None, model: str | None = None, max_output_tokens: int | None = None):
        settings = get_settings()
        self.model = model or settings.generation_model
        self.max_output_tokens = max_output_tokens or settings.max_output_tokens
        if client is None:
            if not os.environ.get("GROQ_API_KEY"):
                raise ConfigError("GROQ_API_KEY is not set. Add it to your .env file.")
            from groq import Groq

            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self._client = client

    def generate(self, system_prompt: str, user_message: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, _ATTEMPTS + 1):
            try:
                response = self._client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    model=self.model,
                    temperature=0.0,  # factual and repeatable
                    max_tokens=self.max_output_tokens,
                )
                text = (response.choices[0].message.content or "").strip()
                if not text:
                    raise ValueError("The model returned an empty answer")
                return text
            except Exception as exc:  # network, rate limit (429), safety block, ...
                last_error = exc
                logger.warning("Generation attempt %d/%d failed: %s", attempt, _ATTEMPTS, exc)
                if attempt < _ATTEMPTS:
                    time.sleep(retry_delay(exc, attempt))
        raise GenerationError("The answer service failed. Please try again.") from last_error