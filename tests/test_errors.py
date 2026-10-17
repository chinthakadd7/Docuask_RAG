from app.errors import http_status_for, public_message
from app.exceptions import (
    ConfigError,
    DocumentNotFoundError,
    EmbeddingError,
    EmptyQuestionError,
    EncryptedPDFError,
    FileTooLargeError,
    GenerationError,
    InvalidPDFError,
    NoExtractableTextError,
    QuotaExceededError,
)


def test_each_error_maps_to_the_expected_status():
    expected = {
        FileTooLargeError: 413, InvalidPDFError: 400, EmptyQuestionError: 400,
        EncryptedPDFError: 422, NoExtractableTextError: 422, DocumentNotFoundError: 404,
        QuotaExceededError: 429, EmbeddingError: 503, GenerationError: 503, ConfigError: 500,
    }
    for error_type, status in expected.items():
        assert http_status_for(error_type("x")) == status, error_type.__name__


def test_unknown_errors_are_500():
    assert http_status_for(RuntimeError("boom")) == 500


def test_config_errors_never_leak_details():
    message = public_message(ConfigError("GEMINI_API_KEY is not set"))
    assert "GEMINI" not in message


def test_user_facing_errors_keep_their_message():
    assert public_message(NoExtractableTextError("scanned PDF")) == "scanned PDF"


def test_unexpected_errors_get_a_generic_message():
    assert "boom" not in public_message(RuntimeError("boom"))
