"""PDF parsing: bytes in, a list of pages (number + clean text) out.

Page numbers are the PDF's physical pages (1 = first page), not the numbers
printed on the page. This is what makes citations verifiable.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.exceptions import EncryptedPDFError, FileTooLargeError, InvalidPDFError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Page:
    number: int  # 1-based physical page number
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    total_pages: int
    pages: list[Page]  # only pages that contain text

    @property
    def empty_pages(self) -> int:
        return self.total_pages - len(self.pages)


def validate_pdf_bytes(data: bytes, max_bytes: int) -> None:
    """Cheap checks before we spend any time parsing."""
    if len(data) > max_bytes:
        raise FileTooLargeError(f"File is larger than {max_bytes // (1024 * 1024)} MB.")
    if b"%PDF-" not in data[:1024]:
        raise InvalidPDFError("This file does not look like a PDF.")


def clean_text(raw: str) -> str:
    """Tidy extracted text while keeping paragraph breaks (blank lines)."""
    text = raw.replace("\x00", "")
    # Join words split by a line-break hyphen: "inter-\nnational" -> "international".
    # Lowercase-only keeps real hyphens such as "Well-\nKnown" untouched.
    text = re.sub(r"([a-z])-\n([a-z])", r"\1\2", text)
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    paragraphs = re.split(r"\n\s*\n", text)
    # Single line breaks inside a paragraph are just PDF line wrapping.
    paragraphs = [re.sub(r"\s*\n\s*", " ", p).strip() for p in paragraphs]
    return "\n\n".join(p for p in paragraphs if p)


def extract_pages(data: bytes) -> ParsedDocument:
    """Read a PDF page by page. Pages without text are skipped (and counted)."""
    try:
        import pymupdf as fitz  # PyMuPDF >= 1.24.3
    except ImportError:  # pragma: no cover
        import fitz  # older PyMuPDF

    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise InvalidPDFError("Could not open this PDF. It may be corrupted.") from exc

    with document:
        if document.needs_pass:
            raise EncryptedPDFError("This PDF is password protected.")

        pages: list[Page] = []
        for index, page in enumerate(document, start=1):
            text = clean_text(page.get_text("text", sort=True))
            if text:
                pages.append(Page(number=index, text=text))
            else:
                logger.warning("Page %d has no extractable text (scanned page?)", index)
        return ParsedDocument(total_pages=document.page_count, pages=pages)
