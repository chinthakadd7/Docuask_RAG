"""Step 6 check: is the right page in the top results, and are off-topic questions rejected?

Usage:
    python -m eval.check_retrieval                      # uses eval/retrieval_check.json
    python -m eval.check_retrieval path/to/file.json

Each item is {"question": ..., "file": "name.pdf" or null, "page": 14 or [3, 4] or null}.
Use page = null for a question that is NOT answered by your PDFs (an off-topic question).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from app.config import get_settings
from app.retrieval.retriever import retrieve

DEFAULT_FILE = Path(__file__).parent / "retrieval_check.json"


def _pages(value) -> set[int] | None:
    if value is None:
        return None
    return set(value) if isinstance(value, list) else {value}


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE
    items = json.loads(path.read_text(encoding="utf-8"))
    settings = get_settings()

    found_count = 0
    answerable = 0
    correct_scores: list[float] = []  # score of the first correct hit, per found question
    offtopic_best: list[float] = []   # best score for each off-topic question

    print(f"top_k={settings.top_k}, current MIN_SIMILARITY={settings.min_similarity}\n")

    for item in items:
        # min_similarity=0 returns raw results, so we can see the real scores.
        hits = retrieve(item["question"], top_k=settings.top_k, min_similarity=0.0)
        best = hits[0].score if hits else 0.0
        label = item["question"][:70]
        pages = _pages(item.get("page"))

        if pages is None:
            offtopic_best.append(best)
            flag = "REJECTED" if best < settings.min_similarity else "WRONGLY KEPT"
            print(f"[off-topic] best score {best:.2f}  {flag}  | {label}")
            continue

        answerable += 1
        rank = next(
            (
                i
                for i, h in enumerate(hits, start=1)
                if h.page_number in pages
                and (item.get("file") is None or h.file_name == item["file"])
            ),
            None,
        )
        if rank is None:
            print(f"[MISS]      best score {best:.2f}  not in top {settings.top_k}  | {label}")
            for h in hits[:3]:
                print(f"              got {h.file_name} p.{h.page_number} ({h.score:.2f})")
        else:
            found_count += 1
            correct_scores.append(hits[rank - 1].score)
            print(f"[ok]        rank {rank}, score {hits[rank - 1].score:.2f}  | {label}")

    print("\n--- Summary ---")
    if answerable:
        print(f"Right page in top {settings.top_k}: {found_count}/{answerable} "
              f"({found_count / answerable:.0%})")
    if correct_scores:
        print(f"Lowest score of a correct hit:   {min(correct_scores):.2f}")
    if offtopic_best:
        print(f"Highest best-score off-topic:    {max(offtopic_best):.2f}")
    if correct_scores and offtopic_best:
        low, high = min(correct_scores), max(offtopic_best)
        if high < low:
            print(f"Suggested MIN_SIMILARITY: about {(low + high) / 2:.2f}  "
                  f"(set it in .env, then run this check again)")
        else:
            print("Scores overlap: off-topic questions score as high as real ones. "
                  "A threshold alone can't separate them; see the tuning notes.")


if __name__ == "__main__":
    main()
