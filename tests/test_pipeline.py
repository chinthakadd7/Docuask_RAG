import pytest

from app.exceptions import NoExtractableTextError
from app.ingestion.pipeline import ingest_pdf

fitz = pytest.importorskip("pymupdf")


class FakeEmbedder:
    def embed_texts(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeStore:
    def __init__(self):
        self.chunks = []

    def has_document(self, doc_id):
        return any(c.doc_id == doc_id for c in self.chunks)

    def add_chunks(self, chunks, embeddings):
        assert len(chunks) == len(embeddings)
        self.chunks.extend(chunks)


def words(text):
    return len(text.split())


def make_pdf(pages: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_textbox(fitz.Rect(40, 40, 550, 800), text, fontsize=10)
    return doc.tobytes()


LONG = " ".join(f"Sentence number {i} talks about leave policy and holidays." for i in range(40))


def test_ingest_stores_chunks_with_correct_pages():
    store = FakeStore()
    data = make_pdf([LONG, "", LONG])
    result = ingest_pdf(data, "folder/handbook.pdf", embedder=FakeEmbedder(),
                        store=store, count_tokens=words)
    assert result.status == "ingested"
    assert result.file_name == "handbook.pdf"  # path stripped
    assert result.total_pages == 3 and result.empty_pages == 1
    assert {c.page_number for c in store.chunks} == {1, 3}


def test_same_file_twice_is_skipped():
    store = FakeStore()
    data = make_pdf([LONG])
    ingest_pdf(data, "a.pdf", embedder=FakeEmbedder(), store=store, count_tokens=words)
    again = ingest_pdf(data, "renamed.pdf", embedder=FakeEmbedder(), store=store, count_tokens=words)
    assert again.status == "duplicate"


def test_scanned_pdf_gives_friendly_error():
    data = make_pdf(["", ""])
    with pytest.raises(NoExtractableTextError):
        ingest_pdf(data, "scan.pdf", embedder=FakeEmbedder(), store=FakeStore(), count_tokens=words)
