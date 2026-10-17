"""DocuAsk API.

Run:   uvicorn app.main:app --reload
Docs:  http://localhost:8000/docs
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from functools import lru_cache

from fastapi import Depends, FastAPI, File, Request, Response, UploadFile
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import http_status_for, public_message
from app.exceptions import DocumentNotFoundError, DocuAskError
from app.generation.answerer import Answer, answer_question
from app.ingestion.pipeline import ingest_pdf
from app.retrieval.embedder import Embedder
from app.retrieval.retriever import retrieve
from app.retrieval.store import VectorStore
from app.schemas import (
    AskRequest,
    AskResponse,
    DeleteResponse,
    DocumentOut,
    ErrorResponse,
    HealthResponse,
    SourceOut,
    UploadResponse,
)
from app.utils.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DocuAsk",
    version="0.1.0",
    description="Upload PDFs, ask questions in plain English, get answers with page citations.",
)

_ERRORS = {
    400: {"model": ErrorResponse}, 404: {"model": ErrorResponse},
    413: {"model": ErrorResponse}, 422: {"model": ErrorResponse},
    429: {"model": ErrorResponse}, 503: {"model": ErrorResponse},
}


# ---- Shared objects (created once, reused by every request) ----

@lru_cache(maxsize=1)
def get_store() -> VectorStore:
    return VectorStore()


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return Embedder()


# ---- Errors: one JSON shape for everything ----

def _error_response(error: Exception) -> JSONResponse:
    status = http_status_for(error)
    if status >= 500:
        logger.error("Server-side error: %s", error, exc_info=error)
    return JSONResponse(
        status_code=status,
        content={"error": {"type": type(error).__name__, "message": public_message(error)}},
    )


@app.exception_handler(DocuAskError)
async def handle_docuask_error(request: Request, exc: DocuAskError) -> JSONResponse:
    return _error_response(exc)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(exc)


# ---- Routes ----
# Plain `def` (not `async def`) on purpose: these call slow, blocking APIs, so FastAPI
# runs them in worker threads and the server stays responsive.

@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post(
    "/documents",
    response_model=UploadResponse,
    status_code=201,
    responses=_ERRORS,
    tags=["documents"],
    summary="Upload a PDF and index it",
)
def upload_document(
    response: Response,
    file: UploadFile = File(..., description="A PDF file"),
    store: VectorStore = Depends(get_store),
    embedder: Embedder = Depends(get_embedder),
) -> UploadResponse:
    settings = get_settings()
    # Read one byte more than the limit, so oversized files are caught without loading them all.
    data = file.file.read(settings.max_file_bytes + 1)
    result = ingest_pdf(data, file.filename or "upload.pdf", embedder=embedder, store=store)
    if result.status == "duplicate":
        response.status_code = 200  # already there: nothing new was created
    return UploadResponse(**asdict(result))


@app.get("/documents", response_model=list[DocumentOut], tags=["documents"])
def list_documents(store: VectorStore = Depends(get_store)) -> list[dict]:
    return store.list_documents()


@app.delete(
    "/documents/{doc_id}",
    response_model=DeleteResponse,
    responses=_ERRORS,
    tags=["documents"],
    summary="Delete a document and all its chunks",
)
def delete_document(doc_id: str, store: VectorStore = Depends(get_store)) -> DeleteResponse:
    deleted = store.delete_document(doc_id)
    if deleted == 0:
        raise DocumentNotFoundError("No document with that ID was found.")
    return DeleteResponse(doc_id=doc_id, deleted_chunks=deleted)


def _to_ask_response(answer: Answer) -> AskResponse:
    return AskResponse(
        answer=answer.text,
        found=answer.found,
        cited=answer.cited,
        sources=[
            SourceOut(
                number=s.number,
                file_name=s.file_name,
                page_number=s.page_number,
                text=s.text,
                score=round(s.score, 4),
            )
            for s in answer.sources
        ],
    )


@app.post(
    "/ask",
    response_model=AskResponse,
    responses=_ERRORS,
    tags=["questions"],
    summary="Ask a question about the uploaded documents",
)
def ask(
    body: AskRequest,
    store: VectorStore = Depends(get_store),
    embedder: Embedder = Depends(get_embedder),
) -> AskResponse:
    def retrieve_fn(question: str, doc_ids: list[str] | None = None):
        # Same store and embedder objects as the upload route (one Chroma client only).
        return retrieve(question, doc_ids=doc_ids, embedder=embedder, store=store)

    doc_ids = body.doc_ids or None
    for doc_id in doc_ids or []:  # a wrong ID would silently return "not found", so say so instead
        if not store.has_document(doc_id):
            raise DocumentNotFoundError(f"No document with ID '{doc_id}' was found.")

    answer = answer_question(body.question, doc_ids=doc_ids, retrieve_fn=retrieve_fn)
    return _to_ask_response(answer)