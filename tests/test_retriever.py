import pytest

from app.exceptions import EmptyQuestionError
from app.retrieval.retriever import retrieve
from app.retrieval.store import Hit


def make_hit(score, page=1, name="a.pdf"):
    return Hit(chunk_id=f"c{page}", doc_id="d1", file_name=name, page_number=page,
               chunk_index=0, text=f"text on page {page}", score=score)


class FakeEmbedder:
    def __init__(self):
        self.questions = []

    def embed_query(self, text):
        self.questions.append(text)
        return [0.1, 0.2, 0.3]


class FakeStore:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def search(self, embedding, top_k=5, doc_ids=None):
        self.calls.append((embedding, top_k, doc_ids))
        return self.hits[:top_k]


def test_keeps_hits_at_or_above_threshold_in_order():
    store = FakeStore([make_hit(0.80, 1), make_hit(0.50, 2), make_hit(0.20, 3)])
    hits = retrieve("question?", min_similarity=0.30, embedder=FakeEmbedder(), store=store)
    assert [h.page_number for h in hits] == [1, 2]


def test_returns_empty_list_when_nothing_is_close_enough():
    store = FakeStore([make_hit(0.25), make_hit(0.10)])
    assert retrieve("off topic", min_similarity=0.30, embedder=FakeEmbedder(), store=store) == []


def test_returns_empty_list_when_store_is_empty():
    assert retrieve("anything", embedder=FakeEmbedder(), store=FakeStore([])) == []


def test_threshold_boundary_is_inclusive():
    store = FakeStore([make_hit(0.30)])
    assert len(retrieve("q", min_similarity=0.30, embedder=FakeEmbedder(), store=store)) == 1


def test_question_is_trimmed_and_top_k_and_filter_are_passed_on():
    embedder, store = FakeEmbedder(), FakeStore([make_hit(0.9)])
    retrieve("  hello  ", top_k=3, min_similarity=0.0, doc_ids=["d1"], embedder=embedder, store=store)
    assert embedder.questions == ["hello"]
    assert store.calls[0][1:] == (3, ["d1"])


def test_empty_question_raises_friendly_error():
    with pytest.raises(EmptyQuestionError):
        retrieve("   ", embedder=FakeEmbedder(), store=FakeStore([]))
