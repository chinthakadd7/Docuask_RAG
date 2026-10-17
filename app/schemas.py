"""Request and response shapes for the API. FastAPI turns these into the /docs page."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=2000, examples=["What is the notice period?"])
    doc_ids: list[str] | None = Field(
        default=None, description="Only search inside these documents. Leave empty to search all."
    )


class SourceOut(BaseModel):
    number: int = Field(description="The [n] used in the answer text")
    file_name: str
    page_number: int
    text: str = Field(description="The excerpt the answer was based on")
    score: float = Field(description="Cosine similarity, closer to 1 is more similar")


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    found: bool = Field(description="False when the answer is 'not found'")
    cited: bool = Field(description="False when the model answered without a valid citation")


class UploadResponse(BaseModel):
    doc_id: str
    file_name: str
    status: str = Field(description="'ingested' or 'duplicate'")
    total_pages: int
    empty_pages: int
    chunk_count: int


class DocumentOut(BaseModel):
    doc_id: str
    file_name: str
    chunks: int


class DeleteResponse(BaseModel):
    doc_id: str
    deleted_chunks: int


class HealthResponse(BaseModel):
    status: str


class ErrorBody(BaseModel):
    type: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
