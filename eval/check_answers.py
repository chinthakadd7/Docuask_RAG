"""Step 7 check: does every answer cite the right page, and are off-topic questions refused?

Usage:
    python -m eval.check_answers                      # uses eval/retrieval_check.json
    python -m eval.check_answers path/to/file.json    # same format as the retrieval check
    python -m eval.check_answers --delay 20           # seconds to wait between questions

The free Gemini tier allows only a few requests per minute, so the default delay is 13s.
If you see "429" warnings, raise --delay. Each answerable question makes one Gemini call.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from app.exceptions import DocuAskError
from app.generation.answerer import answer_question

DEFAULT_FILE = Path(__file__).parent / "retrieval_check.json"


def _pages(value) -> set[int] | None:
    if value is None:
        return None
    return set(value) if isinstance(value, list) else {value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(DEFAULT_FILE))
    parser.add_argument("--delay", type=float, default=13.0, help="seconds between questions")
    args = parser.parse_args()

    items = json.loads(Path(args.path).read_text(encoding="utf-8"))
    answerable = correct = offtopic = refused = uncited = errors = 0

    for i, item in enumerate(items):
        if i:
            time.sleep(args.delay)
        pages = _pages(item.get("page"))
        label = item["question"][:70]
        try:
            answer = answer_question(item["question"])
        except DocuAskError as exc:  # keep going: one failure shouldn't stop the whole check
            errors += 1
            print(f"[ERROR] {exc} | {label}")
            continue
        cited_pages = {s.page_number for s in answer.sources
                       if item.get("file") is None or s.file_name == item["file"]}

        if pages is None:
            offtopic += 1
            ok = not answer.found
            refused += ok
            print(f"[{'REFUSED' if ok else 'ANSWERED (should refuse)'}] {label}")
            if not ok:
                print(f"      -> {answer.text[:120]}")
            continue

        answerable += 1
        if not answer.found:
            print(f"[NOT FOUND] {label}")
        elif not answer.cited:
            uncited += 1
            print(f"[NO CITATION] {label}")
        elif cited_pages & pages:
            correct += 1
            print(f"[ok] cited p.{sorted(cited_pages)} | {label}")
        else:
            print(f"[WRONG PAGE] cited p.{sorted(cited_pages)}, expected {sorted(pages)} | {label}")
            print(f"      -> {answer.text[:160]}")

    print("\n--- Summary ---")
    if answerable:
        print(f"Correct citation: {correct}/{answerable} ({correct / answerable:.0%})")
        print(f"Answers with no valid citation: {uncited}")
    if offtopic:
        print(f"Off-topic refused: {refused}/{offtopic}")
    if errors:
        print(f"Questions that failed (API errors, not counted above): {errors}")


if __name__ == "__main__":
    main()