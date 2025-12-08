#!/usr/bin/env python3
"""
4. GET COMMENTARIES & CROSS-REFERENCES

Endpoint:  /api/links/{ref}

This script:
- Calls Sefaria's links API for a given ref (e.g. "Genesis 1:1")
- Prints a small summary: how many links, categories, etc.
- Shows a few “Commentary” / “Midrash” / “Talmud” style related sources

This is the building block for a "Related Sources" panel in MarehMakom.
"""

import requests
import json
from collections import Counter, defaultdict

BASE = "https://www.sefaria.org"


def pretty(obj) -> None:
    """Debug helper: pretty-print JSON."""
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def get_links(ref: str) -> list[dict]:
    """
    Call Sefaria's /api/links/{ref}

    ref : e.g. "Genesis 1:1", "Berakhot 2a"

    Returns:
        A list of link objects. Each link is roughly like:
        {
          "category": "Commentary" | "Talmud" | "Midrash" | ...,
          "type": "commentary",
          "refs": ["Rashi on Genesis 1:1", "Genesis 1:1"],
          "sourceRef": "Rashi on Genesis 1:1",
          "anchorRef": "Genesis 1:1",
          ...
        }
    """
    ref_url = ref.replace(" ", "_")
    url = f"{BASE}/api/links/{ref_url}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def summarize_links(ref: str) -> None:
    links = get_links(ref)

    print("=== LINKS SUMMARY ===")
    print("ref:", ref)
    print("total links:", len(links))

    # 1) Count by category and type
    cat_counter = Counter()
    type_counter = Counter()

    for link in links:
        cat_counter[link.get("category", "Unknown")] += 1
        type_counter[link.get("type", "Unknown")] += 1

    print("\nBy category:")
    for cat, count in cat_counter.most_common():
        print(f"  {cat:12} : {count}")

    print("\nBy type:")
    for t, count in type_counter.most_common():
        print(f"  {t:12} : {count}")

    # 2) Group “related sources” by category for quick UI ideas
    grouped: dict[str, list[dict]] = defaultdict(list)
    for link in links:
        grouped[link.get("category", "Unknown")].append(link)

    print("\n=== SAMPLE RELATED SOURCES (for MM UI) ===")
    # Priority categories you probably care about first
    interesting_order = [
        "Commentary",
        "Midrash",
        "Talmud",
        "Tanakh",
        "Quoting Commentary",
        "Unknown",
    ]

    max_per_cat = 5  # just to keep terminal output small

    for cat in interesting_order:
        items = grouped.get(cat, [])
        if not items:
            continue

        print(f"\n[{cat}] (showing up to {max_per_cat})")
        for link in items[:max_per_cat]:
            # sourceRef = the “other” side of the link
            # anchorRef  = the original ref we asked about (usually)
            source = link.get("sourceRef") or ", ".join(link.get("refs", []))
            anchor = link.get("anchorRef") or ref
            ltype = link.get("type", "")
            print(f"  - ({ltype}) {source}  →  {anchor}")


def test_links_api():
    ref = "Genesis 1:1"
    print(f"=== Fetching links for: {ref} ===\n")
    summarize_links(ref)


if __name__ == "__main__":
    test_links_api()