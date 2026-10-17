"""Turns our custom errors into HTTP status codes and safe messages.

Kept free of FastAPI imports so it can be tested on its own.
"""
from __future__ import annotations

from app.exceptions import (
    ConfigError,
    DocumentNotFoundError,
    DocuAskError,
    EmbeddingError,
    EmptyQuestionError,
    EncryptedPDFError,
    FileTooLargeError,
    GenerationError,
    InvalidPDFError,
    NoExtractableTextError,
    QuotaExceededError,
)

# Checked in order; the first match wins.
_STATUS_BY_ERROR: list[tuple[type[DocuAskError], int]] = [
    (FileTooLargeError, 413),       # Payload Too Large
    (InvalidPDFError, 400),         # Bad Request
    (EmptyQuestionError, 400),
    (EncryptedPDFError, 422),       # Unprocessable: we can't read it
    (NoExtractableTextError, 422),
    (DocumentNotFoundError, 404),
    (QuotaExceededError, 429),      # Too Many Requests
    (EmbeddingError, 503),          # Service Unavailable: upstream API failed
    (GenerationError, 503),
    (ConfigError, 500),             # our own misconfiguration
]


def http_status_for(error: Exception) -> int:
    for error_type, status in _STATUS_BY_ERROR:
        if isinstance(error, error_type):
            return status
    return 400 if isinstance(error, DocuAskError) else 500


def public_message(error: Exception) -> str:
    """Message that is safe to show to a user (never leaks settings or stack traces)."""
    if isinstance(error, ConfigError):
        return "The server is not configured correctly. Please contact the administrator."
    if isinstance(error, DocuAskError):
        return str(error) or "Something went wrong."
    return "Unexpected server error. Please try again."
