"""Vector database wrapper (Chroma). Search is added in the retrieval step."""
from __future__ import annotations

from app.config import get_settings
from app.ingestion.chunker import Chunk

_WRITE_BATCH = 500


class VectorStore:
    def __init__(self, path=None, collection_name: str | None = None):
        import chromadb

        settings = get_settings()
        self._client = chromadb.PersistentClient(path=str(path or settings.vectorstore_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection_name or settings.collection_name,
            metadata={"hnsw:space": "cosine"},  # cosine distance suits text embeddings
        )

    def has_document(self, doc_id: str) -> bool:
        found = self._collection.get(where={"doc_id": doc_id}, limit=1)
        return bool(found["ids"])

    def add_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        for start in range(0, len(chunks), _WRITE_BATCH):
            part = slice(start, start + _WRITE_BATCH)
            batch = chunks[part]
            self._collection.upsert(  # upsert = safe to run twice
                ids=[c.id for c in batch],
                embeddings=embeddings[part],
                documents=[c.text for c in batch],
                metadatas=[c.metadata() for c in batch],
            )

    def list_documents(self) -> list[dict]:
        data = self._collection.get(include=["metadatas"])
        documents: dict[str, dict] = {}
        for meta in data["metadatas"] or []:
            entry = documents.setdefault(
                meta["doc_id"],
                {"doc_id": meta["doc_id"], "file_name": meta["file_name"], "chunks": 0},
            )
            entry["chunks"] += 1
        return sorted(documents.values(), key=lambda d: d["file_name"].lower())

    def delete_document(self, doc_id: str) -> int:
        """Remove every chunk of a document. Returns how many were deleted."""
        found = self._collection.get(where={"doc_id": doc_id})
        ids = found["ids"]
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def count(self) -> int:
        return self._collection.count()
