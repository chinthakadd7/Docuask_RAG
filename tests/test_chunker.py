from app.ingestion.chunker import chunk_pages, make_chunk_id, split_text
from app.ingestion.parser import Page


def words(text: str) -> int:
    """Simple token counter so tests run offline: 1 word = 1 token."""
    return len(text.split())


def make_text(sentences: int, words_per_sentence: int = 10) -> str:
    return " ".join(
        " ".join(f"w{s}x{w}" for w in range(words_per_sentence - 1)) + f" end{s}."
        for s in range(sentences)
    )


def test_chunks_never_exceed_size():
    chunks = split_text(make_text(200), size=100, overlap=15, count=words)
    assert len(chunks) > 1
    assert all(words(c) <= 100 for c in chunks)


def test_neighbouring_chunks_overlap():
    chunks = split_text(make_text(200), size=100, overlap=15, count=words)
    for first, second in zip(chunks, chunks[1:]):
        last_sentence = first.split(".")[-2].strip() + "."
        assert last_sentence in second


def test_no_content_is_lost():
    text = make_text(120)
    joined = " ".join(split_text(text, size=100, overlap=15, count=words))
    for s in range(120):
        assert f"end{s}." in joined


def test_short_text_is_one_chunk():
    assert split_text("Just one short sentence.", 500, 75, words) == ["Just one short sentence."]


def test_huge_unbroken_string_is_hard_split():
    blob = "x" * 5000
    count = lambda t: len(t) // 4 + 1
    chunks = split_text(blob, size=50, overlap=10, count=count)
    assert len(chunks) > 1
    assert all(count(c) <= 50 for c in chunks)


def test_page_numbers_are_kept_and_never_mixed():
    pages = [Page(1, make_text(30)), Page(2, make_text(30)), Page(5, make_text(30))]
    chunks = chunk_pages(pages, doc_id="d1", file_name="a.pdf",
                         size=100, overlap=15, min_tokens=5, count_tokens=words)
    assert {c.page_number for c in chunks} == {1, 2, 5}
    for c in chunks:
        assert c.file_name == "a.pdf"
        assert c.chunk_index >= 0


def test_tiny_pages_are_dropped():
    pages = [Page(1, "Page 3"), Page(2, make_text(30))]
    chunks = chunk_pages(pages, doc_id="d1", file_name="a.pdf",
                         size=100, overlap=15, min_tokens=30, count_tokens=words)
    assert {c.page_number for c in chunks} == {2}


def test_ids_are_unique_and_deterministic():
    pages = [Page(1, make_text(60)), Page(2, make_text(60))]
    kwargs = dict(doc_id="d1", file_name="a.pdf", size=100, overlap=15,
                  min_tokens=5, count_tokens=words)
    first = chunk_pages(pages, **kwargs)
    second = chunk_pages(pages, **kwargs)
    assert [c.id for c in first] == [c.id for c in second]
    assert len({c.id for c in first}) == len(first)
    assert first[0].id == make_chunk_id("d1", 1, 0)
