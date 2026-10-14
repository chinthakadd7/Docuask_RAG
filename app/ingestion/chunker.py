"""Page-aware chunking.

Rules (from the design doc):
  * Split each page on its own, never across pages, so every chunk has one exact page.
  * Recursive split: paragraphs -> sentences -> words -> characters (last resort).
  * ~500 tokens per chunk with ~75 tokens of overlap between neighbours.
  * Drop chunks under ~30 tokens (headers, footers, stray page numbers).
  * Chunk IDs are deterministic, so re-ingesting a file never creates duplicates.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.ingestion.parser import Page
from app.ingestion.tokens import TokenCounter, get_token_counter

_SPLITTERS = (
    re.compile(r"\n\s*\n"),  # paragraphs
    re.compile(r"(?<=[.!?])\s+"),  # sentences
    re.compile(r"\s+"),  # words
)


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    file_name: str
    page_number: int
    chunk_index: int  # position within its page, starting at 0
    text: str
    token_count: int

    def metadata(self) -> dict:
        """Everything stored next to the vector. This is what powers citations."""
        return {
            "doc_id": self.doc_id,
            "file_name": self.file_name,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
        }


def make_chunk_id(doc_id: str, page_number: int, chunk_index: int) -> str:
    raw = f"{doc_id}:{page_number}:{chunk_index}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _hard_split(text: str, max_tokens: int, count: TokenCounter) -> list[str]:
    """Last resort for text with no usable separators (e.g. a huge unbroken string)."""
    pieces: list[str] = []
    while text:
        tokens = count(text)
        if tokens <= max_tokens:
            pieces.append(text)
            break
        step = max(1, int(len(text) * max_tokens / tokens * 0.9))
        pieces.append(text[:step])
        text = text[step:]
    return pieces


def _atomize(text: str, max_tokens: int, count: TokenCounter, level: int = 0) -> list[str]:
    """Break text into pieces that are each <= max_tokens, using the largest natural unit."""
    text = text.strip()
    if not text:
        return []
    if count(text) <= max_tokens:
        return [text]
    if level >= len(_SPLITTERS):
        return _hard_split(text, max_tokens, count)
    parts = _SPLITTERS[level].split(text)
    if len(parts) == 1:
        return _atomize(text, max_tokens, count, level + 1)
    pieces: list[str] = []
    for part in parts:
        pieces.extend(_atomize(part, max_tokens, count, level + 1))
    return pieces


def split_text(text: str, size: int, overlap: int, count: TokenCounter) -> list[str]:
    """Pack small pieces into chunks of up to `size` tokens, carrying `overlap` tokens forward."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    pieces = [(p, count(p)) for p in _atomize(text, size, count)]
    chunks: list[str] = []
    current: list[tuple[str, int]] = []
    current_tokens = 0

    for piece, tokens in pieces:
        if current and current_tokens + tokens > size:
            chunks.append(" ".join(p for p, _ in current))
            # Start the next chunk with the tail of this one (the overlap).
            carried: list[tuple[str, int]] = []
            carried_tokens = 0
            for p, t in reversed(current):
                if carried_tokens + t > overlap:
                    break
                carried.insert(0, (p, t))
                carried_tokens += t
            current, current_tokens = carried, carried_tokens
            # If the overlap plus the new piece is too big, shrink the overlap.
            while current and current_tokens + tokens > size:
                _, dropped = current.pop(0)
                current_tokens -= dropped
        current.append((piece, tokens))
        current_tokens += tokens

    if current:
        chunks.append(" ".join(p for p, _ in current))
    return chunks


def chunk_pages(
    pages: list[Page],
    *,
    doc_id: str,
    file_name: str,
    size: int = 500,
    overlap: int = 75,
    min_tokens: int = 30,
    count_tokens: TokenCounter | None = None,
) -> list[Chunk]:
    """Turn parsed pages into chunks that each remember their file and page number."""
    count = count_tokens or get_token_counter()
    chunks: list[Chunk] = []

    for page in pages:
        index = 0
        for text in split_text(page.text, size, overlap, count):
            tokens = count(text)
            if tokens < min_tokens:
                continue  # headers, footers, stray page numbers
            chunks.append(
                Chunk(
                    id=make_chunk_id(doc_id, page.number, index),
                    doc_id=doc_id,
                    file_name=file_name,
                    page_number=page.number,
                    chunk_index=index,
                    text=text,
                    token_count=tokens,
                )
            )
            index += 1
    return chunks
