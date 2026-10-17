"""Central settings. Every tunable value lives here, read from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:  # python-dotenv is optional: without it, real environment variables still work
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    embedding_model: str
    embedding_dimensions: int
    chunk_size_tokens: int
    chunk_overlap_tokens: int
    min_chunk_tokens: int
    max_file_mb: int
    embed_batch_size: int
    top_k: int
    min_similarity: float
    generation_model: str
    max_output_tokens: int
    vectorstore_dir: Path
    collection_name: str

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", ""),
            embedding_model=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
            embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "768")),
            chunk_size_tokens=int(os.getenv("CHUNK_SIZE_TOKENS", "500")),
            chunk_overlap_tokens=int(os.getenv("CHUNK_OVERLAP_TOKENS", "75")),
            min_chunk_tokens=int(os.getenv("MIN_CHUNK_TOKENS", "30")),
            max_file_mb=int(os.getenv("MAX_FILE_MB", "20")),
            embed_batch_size=int(os.getenv("EMBED_BATCH_SIZE", "100")),
            top_k=int(os.getenv("TOP_K", "5")),
            min_similarity=float(os.getenv("MIN_SIMILARITY", "0.30")),
            generation_model=os.getenv("GENERATION_MODEL", "gemini-3.8-flash"),
            max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "8192")),
            vectorstore_dir=Path(
                os.getenv("VECTORSTORE_DIR", str(ROOT_DIR / "data" / "vectorstore"))
            ),
            collection_name=os.getenv("COLLECTION_NAME", "docuask_chunks"),
        )
        if settings.chunk_overlap_tokens >= settings.chunk_size_tokens:
            raise ValueError("CHUNK_OVERLAP_TOKENS must be smaller than CHUNK_SIZE_TOKENS")
        if settings.top_k < 1:
            raise ValueError("TOP_K must be at least 1")
        if not 0.0 <= settings.min_similarity <= 1.0:
            raise ValueError("MIN_SIMILARITY must be between 0 and 1")
        return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()