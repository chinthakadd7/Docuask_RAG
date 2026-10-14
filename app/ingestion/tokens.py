"""Token counting. cl100k_base is the tokenizer used by OpenAI's embedding models."""
from __future__ import annotations

from functools import lru_cache
from typing import Callable

TokenCounter = Callable[[str], int]


@lru_cache(maxsize=1)
def get_token_counter(encoding_name: str = "cl100k_base") -> TokenCounter:
    import tiktoken  # imported lazily so the chunker can be tested without it

    encoding = tiktoken.get_encoding(encoding_name)

    def count(text: str) -> int:
        return len(encoding.encode(text, disallowed_special=()))

    return count
