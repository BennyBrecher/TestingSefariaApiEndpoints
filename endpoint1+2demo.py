import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "1-find-refs"))
sys.path.append(os.path.join(CURRENT_DIR, "2-search-wrapper"))

from neat_helper import find_explicit_refs
from implicit_neat import search_implicit_refs


def demo():
    ocr_text = (
        'כתוב בבראשית א:א "בראשית ברא אלקים את השמים ואת הארץ". '
        'וכן נחלקו בזה הרמב"ם בהלכות תשובה ב:א והרמב"ן.'
    )

    # ---------- 1) Explicit finder ----------
    print("=== EXPLICIT (find-refs) RESULTS ===")
    explicit = find_explicit_refs(ocr_text)
    if not explicit:
        print("(no explicit matches)")
    else:
        for r in explicit:
            print(
                f"{r['status'].upper():10} | "
                f"{r['raw']!r:30} | "
                f"ref={r['ref']} | "
                f"chars {r['start']}-{r['end']}"
            )

    # ---------- 2) Implicit search ----------
    phrase = "שובה ישראל עד ה׳ אלקיך"

    print(f"\n=== IMPLICIT (search-wrapper) RESULTS for {phrase!r} ===")
    implicit_hits = search_implicit_refs(phrase, size=5, debug=False)
    if not implicit_hits:
        print("(no implicit hits)")
        return

    for r in implicit_hits:
        snippet = (r["snippet"] or "")[:60]
        print(
            f"{r['title']}  "
            f"(score={r['score']:.2f})  "
            f"→ {snippet}..."
        )


if __name__ == "__main__":
    demo()