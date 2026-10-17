"""Custom errors. Each one carries a message that is safe to show to a user."""


class DocuAskError(Exception):
    """Base class for all expected, user-facing errors."""


class ConfigError(DocuAskError):
    """A required setting (for example the API key) is missing or invalid."""


class FileTooLargeError(DocuAskError):
    """The uploaded file is bigger than MAX_FILE_MB."""


class InvalidPDFError(DocuAskError):
    """The file is not a readable PDF."""


class EncryptedPDFError(DocuAskError):
    """The PDF is password protected."""


class NoExtractableTextError(DocuAskError):
    """No text could be extracted (usually a scanned PDF)."""


class EmbeddingError(DocuAskError):
    """The embedding API failed, even after a retry."""


class EmptyQuestionError(DocuAskError):
    """The question was empty."""


class GenerationError(DocuAskError):
    """The language model failed to produce an answer, even after retries."""


class QuotaExceededError(DocuAskError):
    """The daily free quota is used up. Retrying now will not help."""


class DocumentNotFoundError(DocuAskError):
    """No document with that ID exists."""
