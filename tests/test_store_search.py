"""Tests the real Chroma store. Skipped automatically if chromadb isn't installed."""
import pytest

pytest.importorskip("chromadb")

from app.ingestion.chunker import Chunk  # noqa: E402
from app.retrieval.store import VectorStore  # noqa: E402


def make_chunk(i, doc_id="d1", page=1):
    return Chunk(id=f"c{i}", doc_id=doc_id, file_name=f"{doc_id}.pdf", page_number=page,
                 chunk_index=i, text=f"chunk {i}", token_count=5)


@pytest.fixture
def store(tmp_path):
    s = VectorStore(path=tmp_path, collection_name="test_chunks")
    s.add_chunks(
        [make_chunk(0, "d1", 1), make_chunk(1, "d1", 2), make_chunk(2, "d2", 7)],
        [[1.0, 0.0, 0.0], [0.9, 0.1, 0.0], [0.0, 1.0, 0.0]],
    )
    return s


def test_search_orders_by_similarity_and_scores_are_cosine(store):
    hits = store.search([1.0, 0.0, 0.0], top_k=3)
    assert [h.chunk_id for h in hits] == ["c0", "c1", "c2"]
    assert hits[0].score == pytest.approx(1.0, abs=1e-3)
    assert hits[2].score == pytest.approx(0.0, abs=1e-3)
    assert hits[0].page_number == 1 and hits[0].file_name == "d1.pdf"


def test_search_respects_top_k_and_never_asks_for_more_than_exists(store):
    assert len(store.search([1.0, 0.0, 0.0], top_k=1)) == 1
    assert len(store.search([1.0, 0.0, 0.0], top_k=50)) == 3


def test_search_can_be_limited_to_some_documents(store):
    hits = store.search([1.0, 0.0, 0.0], top_k=5, doc_ids=["d2"])
    assert [h.doc_id for h in hits] == ["d2"]


def test_search_on_empty_store_returns_nothing(tmp_path):
    empty = VectorStore(path=tmp_path, collection_name="empty")
    assert empty.search([1.0, 0.0, 0.0]) == []
