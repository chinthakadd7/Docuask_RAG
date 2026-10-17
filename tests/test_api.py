"""HTTP-level tests. Skipped automatically if FastAPI or httpx isn't installed."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app.exceptions import (  # noqa: E402
    FileTooLargeError,
    NoExtractableTextError,
    QuotaExceededError,
)
from app.generation.answerer import Answer, Source  # noqa: E402
from app.ingestion.pipeline import IngestResult  # noqa: E402


class FakeStore:
    def __init__(self):
        self.docs = {"d1": {"doc_id": "d1", "file_name": "a.pdf", "chunks": 3}}

    def has_document(self, doc_id):
        return doc_id in self.docs

    def list_documents(self):
        return list(self.docs.values())

    def delete_document(self, doc_id):
        return 3 if self.docs.pop(doc_id, None) else 0


@pytest.fixture
def client():
    main.app.dependency_overrides[main.get_store] = lambda: FakeStore()
    main.app.dependency_overrides[main.get_embedder] = lambda: object()
    yield TestClient(main.app, raise_server_exceptions=False)
    main.app.dependency_overrides.clear()


def pdf_upload():
    return {"file": ("a.pdf", b"%PDF-1.4 fake", "application/pdf")}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_upload_returns_201_and_the_summary(client, monkeypatch):
    monkeypatch.setattr(main, "ingest_pdf", lambda *a, **k: IngestResult("d1", "a.pdf", "ingested", 3, 0, 9))
    r = client.post("/documents", files=pdf_upload())
    assert r.status_code == 201 and r.json()["chunk_count"] == 9


def test_duplicate_upload_returns_200(client, monkeypatch):
    monkeypatch.setattr(main, "ingest_pdf", lambda *a, **k: IngestResult("d1", "a.pdf", "duplicate", 0, 0, 0))
    r = client.post("/documents", files=pdf_upload())
    assert r.status_code == 200 and r.json()["status"] == "duplicate"


def test_scanned_pdf_gives_422_with_a_clear_message(client, monkeypatch):
    def boom(*a, **k):
        raise NoExtractableTextError("This looks like a scanned PDF.")
    monkeypatch.setattr(main, "ingest_pdf", boom)
    r = client.post("/documents", files=pdf_upload())
    assert r.status_code == 422
    assert r.json()["error"] == {"type": "NoExtractableTextError", "message": "This looks like a scanned PDF."}


def test_oversized_file_gives_413(client, monkeypatch):
    def boom(*a, **k):
        raise FileTooLargeError("too big")
    monkeypatch.setattr(main, "ingest_pdf", boom)
    assert client.post("/documents", files=pdf_upload()).status_code == 413


def test_list_documents(client):
    assert client.get("/documents").json() == [{"doc_id": "d1", "file_name": "a.pdf", "chunks": 3}]


def test_delete_existing_and_missing_documents(client):
    ok = client.delete("/documents/d1")
    assert ok.status_code == 200 and ok.json() == {"doc_id": "d1", "deleted_chunks": 3}
    missing = client.delete("/documents/nope")
    assert missing.status_code == 404 and missing.json()["error"]["type"] == "DocumentNotFoundError"


def test_ask_returns_answer_and_sources(client, monkeypatch):
    answer = Answer("Leave is 20 days [1].", [Source(1, "a.pdf", 14, "excerpt", 0.8123456)], True, True)
    monkeypatch.setattr(main, "answer_question", lambda *a, **k: answer)
    r = client.post("/ask", json={"question": "How much leave?"})
    body = r.json()
    assert r.status_code == 200 and body["found"] is True
    assert body["sources"][0] == {"number": 1, "file_name": "a.pdf", "page_number": 14,
                                  "text": "excerpt", "score": 0.8123, "chunk_index": 0}


def test_empty_question_is_rejected(client):
    assert client.post("/ask", json={"question": "   "}).status_code == 422


def test_quota_error_gives_429(client, monkeypatch):
    def boom(*a, **k):
        raise QuotaExceededError("Daily quota used up.")
    monkeypatch.setattr(main, "answer_question", boom)
    r = client.post("/ask", json={"question": "Anything?"})
    assert r.status_code == 429 and "quota" in r.json()["error"]["message"].lower()


def test_ask_with_an_unknown_doc_id_gives_404_instead_of_a_silent_not_found(client, monkeypatch):
    monkeypatch.setattr(main, "answer_question", lambda *a, **k: Answer("x", [], True, True))
    r = client.post("/ask", json={"question": "Anything?", "doc_ids": ["string"]})
    assert r.status_code == 404 and "string" in r.json()["error"]["message"]


def test_config_reports_the_upload_limit(client):
    r = client.get("/config")
    assert r.status_code == 200 and isinstance(r.json()["max_file_mb"], int)
