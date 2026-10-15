"""Question in, cited answer out.

Flow: retrieve -> (nothing found? say so, skip the LLM) -> ask the LLM with numbered
excerpts -> map the [1], [2] markers back to real file + page sources.

The model only ever sees excerpt NUMBERS. We attach the real file and page ourselves,
so it cannot invent a page reference, and any number it makes up is dropped.
"""
from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache

from app.exceptions import DocuAskError
from app.generation.prompts import (
    NOT_FOUND_MESSAGE,
    SYSTEM_PROMPT,
    build_user_message,
)
from app.retrieval.retriever import retrieve
from app.retrieval.store import Hit

logger = logging.getLogger(__name__)

# Matches [1], [12] and also lists like [1, 2]
_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


@dataclass(frozen=True)
class Source:
    number: int  # the [n] used in the answer text
    file_name: str
    page_number: int
    text: str  # the full excerpt, for a "show source" view
    score: float


@dataclass(frozen=True)
class Answer:
    text: str
    sources: list[Source] = field(default_factory=list)
    found: bool = True  # False = "not found" answer
    cited: bool = True  # False = the model answered without a valid citation


@lru_cache(maxsize=1)
def _default_generator():
    from app.generation.generator import Generator

    return Generator()


def process_citations(text: str, max_number: int) -> tuple[str, list[int]]:
    """Keep only citation numbers that exist. Returns (clean text, sorted cited numbers).

    "[2, 3]" becomes "[2][3]"; numbers outside 1..max_number are removed.
    """
    cited: set[int] = set()

    def keep_valid(match: re.Match) -> str:
        numbers = [int(n) for n in re.split(r"\s*,\s*", match.group(1))]
        valid = [n for n in numbers if 1 <= n <= max_number]
        cited.update(valid)
        return "".join(f"[{n}]" for n in valid)

    cleaned = _CITATION.sub(keep_valid, text)
    cleaned = re.sub(r"[ \t]+([.,;:!?])", r"\1", cleaned)  # space left before punctuation
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned, sorted(cited)


def _is_not_found(text: str) -> bool:
    normalised = text.replace("\u2019", "'").lower()
    return "couldn't find this in the uploaded documents" in normalised


def _not_found() -> Answer:
    return Answer(text=NOT_FOUND_MESSAGE, sources=[], found=False, cited=False)


def answer_question(
    question: str,
    *,
    doc_ids: list[str] | None = None,
    retrieve_fn=None,
    generator=None,
) -> Answer:
    retrieve_fn = retrieve_fn or retrieve
    hits: list[Hit] = retrieve_fn(question, doc_ids=doc_ids)

    if not hits:  # nothing close enough: skip the LLM (cheaper and safer)
        return _not_found()

    generator = generator or _default_generator()
    raw = generator.generate(SYSTEM_PROMPT, build_user_message(question.strip(), hits))

    text, cited_numbers = process_citations(raw, max_number=len(hits))
    if _is_not_found(text):
        return _not_found()

    sources = [
        Source(
            number=n,
            file_name=hits[n - 1].file_name,
            page_number=hits[n - 1].page_number,
            text=hits[n - 1].text,
            score=hits[n - 1].score,
        )
        for n in cited_numbers
    ]
    if not sources:
        logger.warning("Answer had no valid citation: %r", text[:120])
    return Answer(text=text, sources=sources, found=True, cited=bool(sources))


def format_answer(answer: Answer) -> str:
    """Plain-text version for the terminal."""
    lines = [answer.text]
    if answer.sources:
        lines += ["", "Sources:"]
        for s in answer.sources:
            preview = " ".join(s.text.split())[:150]
            lines.append(f"  [{s.number}] {s.file_name}, p. {s.page_number} (score {s.score:.2f})")
            lines.append(f"      \"{preview}...\"")
    elif answer.found:
        lines += ["", "(Warning: no valid citation in this answer. Treat it with caution.)"]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question about your ingested PDFs.")
    parser.add_argument("question", nargs="*", help="Leave empty for an interactive prompt")
    args = parser.parse_args()

    def ask(q: str) -> None:
        try:
            print("\n" + format_answer(answer_question(q)) + "\n")
        except DocuAskError as exc:
            print(f"\n[error] {exc}\n")

    if args.question:
        ask(" ".join(args.question))
        return
    while True:
        q = input("Question (blank to quit)> ").strip()
        if not q:
            break
        ask(q)


if __name__ == "__main__":
    main()
