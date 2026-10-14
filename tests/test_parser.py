import pytest

from app.exceptions import FileTooLargeError, InvalidPDFError
from app.ingestion.parser import clean_text, extract_pages, validate_pdf_bytes


def test_clean_text_joins_hyphenated_words():
    assert clean_text("inter-\nnational law") == "international law"


def test_clean_text_keeps_paragraph_breaks_and_unwraps_lines():
    raw = "First line\nsecond line\n\nNew paragraph"
    assert clean_text(raw) == "First line second line\n\nNew paragraph"


def test_validate_rejects_non_pdf_and_big_files():
    with pytest.raises(InvalidPDFError):
        validate_pdf_bytes(b"hello world", max_bytes=1000)
    with pytest.raises(FileTooLargeError):
        validate_pdf_bytes(b"%PDF-" + b"0" * 2000, max_bytes=1000)


def test_extract_pages_keeps_page_numbers_and_counts_empty_pages():
    fitz = pytest.importorskip("pymupdf")
    doc = fitz.open()
    for text in ["Alpha content on page one.", "", "Gamma content on page three."]:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    parsed = extract_pages(doc.tobytes())
    assert parsed.total_pages == 3
    assert [p.number for p in parsed.pages] == [1, 3]
    assert parsed.empty_pages == 1
    assert "Alpha" in parsed.pages[0].text
