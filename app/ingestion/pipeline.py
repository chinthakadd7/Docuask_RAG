"""Ingestion pipeline: validate -> parse -> chunk -> embed -> store.

Run from the command line:
    python -m app.ingestion.pipeline data/sample_pdfs/handbook.pdf
"""
from __future__ import annotations

import argparse
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.exceptions import DocuAskError, NoExtractableTextError
from app.ingestion.chunker import chunk_pages
from app.ingestion.parser import extract_pages, validate_pdf_bytes
from app.ingestion.tokens import TokenCounter
from app.utils.logging import setup_logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    doc_id: str
    file_name: str
    status: str  # "ingested" or "duplicate"
    total_pages: int
    empty_pages: int
    chunk_count: int


def compute_doc_id(data: bytes) -> str:
    """Hash of the file's content: the same file always gets the same ID, whatever its name."""
    return hashlib.sha256(data).hexdigest()[:12]


def ingest_pdf(
    data: bytes,
    file_name: str,
    *,
    embedder=None,
    store=None,
    count_tokens: TokenCounter | None = None,
) -> IngestResult:
    settings = get_settings()
    file_name = Path(file_name).name  # never trust a path from an upload

    validate_pdf_bytes(data, settings.max_file_bytes)
    doc_id = compute_doc_id(data)

    if store is None:
        from app.retrieval.store import VectorStore

        store = VectorStore()

    if store.has_document(doc_id):
        logger.info("%s already ingested (doc_id=%s), skipping", file_name, doc_id)
        return IngestResult(doc_id, file_name, "duplicate", 0, 0, 0)

    parsed = extract_pages(data)
    chunks = chunk_pages(
        parsed.pages,
        doc_id=doc_id,
        file_name=file_name,
        size=settings.chunk_size_tokens,
        overlap=settings.chunk_overlap_tokens,
        min_tokens=settings.min_chunk_tokens,
        count_tokens=count_tokens,
    )
    if not chunks:
        raise NoExtractableTextError(
            "This looks like a scanned PDF. OCR isn't supported yet."
        )

    if embedder is None:
        from app.retrieval.embedder import Embedder

        embedder = Embedder()

    embeddings = embedder.embed_texts([c.text for c in chunks])
    store.add_chunks(chunks, embeddings)

    logger.info(
        "Ingested %s: %d pages (%d empty) -> %d chunks",
        file_name, parsed.total_pages, parsed.empty_pages, len(chunks),
    )
    return IngestResult(
        doc_id=doc_id,
        file_name=file_name,
        status="ingested",
        total_pages=parsed.total_pages,
        empty_pages=parsed.empty_pages,
        chunk_count=len(chunks),
    )


def ingest_file(path: str | Path, **kwargs) -> IngestResult:
    path = Path(path)
    return ingest_pdf(path.read_bytes(), path.name, **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one or more PDFs into DocuAsk.")
    parser.add_argument("paths", nargs="+", help="PDF file(s) to ingest")
    args = parser.parse_args()
    setup_logging()

    for path in args.paths:
        try:
            result = ingest_file(path)
            print(f"[{result.status}] {result.file_name}: "
                  f"{result.chunk_count} chunks from {result.total_pages} pages "
                  f"(doc_id={result.doc_id})")
        except DocuAskError as exc:
            print(f"[error] {path}: {exc}")


if __name__ == "__main__":
    main()
