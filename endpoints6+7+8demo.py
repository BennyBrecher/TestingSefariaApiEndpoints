"""
endpoints6+7+8.py

Demo of three Sefaria endpoints:

6) /api/topics                → Topic browser + autocomplete
7) /api/index                 → Library tree + book lookup
8) /api/v2/raw/index/{title}  → Per-book structure metadata
"""

import requests
import json

BASE = "https://www.sefaria.org"


# ---------- shared utils ----------

def pretty(obj):
    """Nicely print JSON-able objects."""
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# =====================================================================
#  6. GET ALL TOPICS  (/api/topics)
# =====================================================================

def get_all_topics_raw():
    """
    Wrapper around /api/topics.

    Returns whatever Sefaria gives us (usually a list of topic objects).
    """
    url = f"{BASE}/api/topics"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def simplify_topics(raw_topics):
    """
    Turn raw topics into a simple list:

      { "slug": "...", "en": "...", "he": "..." }

    Sefaria's topic schema has many more fields; for MM we mostly need:
      - slug: stable id to store/filter on
      - en/he: labels to display in UI

    If labels are missing we just leave them as None.
    """
    simple = []

    if not isinstance(raw_topics, list):
        return simple

    for t in raw_topics:
        if not isinstance(t, dict):
            continue

        slug = t.get("slug")
        if not isinstance(slug, str):
            continue

        # Best effort: different topic objects may store labels differently.
        en_label = (
            t.get("en") or
            t.get("title") or
            (t.get("displayName") if isinstance(t.get("displayName"), str) else None)
        )

        he_label = (
            t.get("he") or
            t.get("heTitle") or
            (t.get("heDisplayName") if isinstance(t.get("heDisplayName"), str) else None)
        )

        simple.append({
            "slug": slug,
            "en": en_label,
            "he": he_label,
        })

    return simple


def build_topic_lookup(simple_topics):
    """
    Build slug → {en, he} lookup for autocomplete / display.

    Example:
      lookup["teshuvah"]  → {"en": "Repentance", "he": "תשובה"}
    """
    lookup = {}
    for t in simple_topics:
        slug = t["slug"]
        lookup[slug] = {"en": t["en"], "he": t["he"]}
    return lookup


def demo_topics():
    print("=== Fetching ALL topics from Sefaria ===\n")
    raw = get_all_topics_raw()
    simple = simplify_topics(raw)
    lookup = build_topic_lookup(simple)

    print(f"Total raw topics:    {len(raw)}")
    print(f"Total simple topics: {len(simple)}\n")

    print("=== First 10 simplified topics ===")
    for t in simple[:10]:
        print(f"- {t['slug']}: {t['en']} / {t['he']}")

    print("\n=== Sample lookup entries ===")
    sample_slugs = [t["slug"] for t in simple[:5]]
    for slug in sample_slugs:
        print(f"{slug!r} -> {lookup.get(slug)}")


# =====================================================================
#  7. GET LIBRARY TREE  (/api/index)
# =====================================================================

def get_library_index():
    """
    Wrapper around /api/index.

    Returns the full Sefaria category/index tree.
    """
    url = f"{BASE}/api/index"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def flatten_library(tree, parent_categories=None):
    """
    Flatten the library tree into a list of book entries.

    Each returned book looks like:
      {
        "title": "Genesis",
        "heTitle": "בראשית",
        "categories": ["Tanakh", "Torah"]
      }
    """
    if parent_categories is None:
        parent_categories = []

    flat_books = []

    if not isinstance(tree, list):
        return flat_books

    for node in tree:
        if not isinstance(node, dict):
            continue

        # Category node
        if "category" in node:
            cat_name = node["category"]
            new_parent = parent_categories + [cat_name]
            contents = node.get("contents", [])
            flat_books.extend(flatten_library(contents, new_parent))

        # Leaf book (index) node
        elif "title" in node:
            title = node.get("title")
            he_title = node.get("heTitle")
            cats = node.get("categories") or parent_categories

            flat_books.append({
                "title": title,
                "heTitle": he_title,
                "categories": cats,
            })

        # Some nodes may be weird / other types; ignore them

    return flat_books


def build_book_lookup(flat_books):
    """
    Build a simple title → book-info lookup.

    For now we only index by English title as Sefaria uses it
    in many APIs, e.g. "Genesis", "Shabbat", "Berakhot".
    """
    lookup = {}
    for b in flat_books:
        title = b.get("title")
        if isinstance(title, str):
            lookup[title] = {
                "title": b["title"],
                "heTitle": b["heTitle"],
                "categories": b["categories"],
            }
    return lookup


def print_tree_preview(index_tree, max_categories=3, max_children=5):
    """
    Print a small human-readable preview of the top of the library tree:
      - first few top-level categories
      - their first few sub-categories
    """
    print("=== Tree preview (top-level categories) ===")
    count = 0
    for node in index_tree:
        if not isinstance(node, dict) or "category" not in node:
            continue

        cat_name = node["category"]
        contents = node.get("contents", [])
        print(f"- {cat_name} ({len(contents)} items)")

        # show only first few children that are themselves categories
        shown = 0
        for child in contents:
            if not isinstance(child, dict):
                continue
            if "category" in child:
                print(f"    ▸ [Category] {child['category']}")
                shown += 1
                if shown >= max_children:
                    print("    ...")
                    break

        count += 1
        if count >= max_categories:
            break


def demo_library():
    print("=== Fetching full Sefaria library index ===")
    index_tree = get_library_index()

    # Flatten and build lookup
    flat_books = flatten_library(index_tree)
    book_lookup = build_book_lookup(flat_books)

    print_tree_preview(index_tree)

    print("\n=== Stats ===")
    print(f"Total categories tree nodes: {len(index_tree)}")
    print(f"Total books flattened:       {len(flat_books)}")
    print(f"Total lookup keys:           {len(book_lookup)}")

    print("\n=== First 10 books ===")
    for b in flat_books[:10]:
        cats = " > ".join(b["categories"])
        print(f"- {b['title']} ({b['heTitle']}) [{cats}]")

    print("\n=== Sample lookups ===")
    for title in ["Genesis", "Shabbat", "Berakhot"]:
        print(f"{title!r} -> {book_lookup.get(title)}")


# =====================================================================
#  8. GET RAW BOOK METADATA  (/api/v2/raw/index/{title})
# =====================================================================

def get_book_metadata(title: str):
    """
    Wrapper around /api/v2/raw/index/{title}.

    Returns a simplified structure:

      {
        "title": ...,
        "heTitle": ...,
        "categories": [...],
        "depth": ...,
        "sectionNames": [...],
        "addressTypes": [...]
      }
    """
    # Sefaria expects spaces as underscores in the URL path
    title_url = title.replace(" ", "_")
    url = f"{BASE}/api/v2/raw/index/{title_url}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    raw = resp.json()

    schema = raw.get("schema") or {}

    depth = schema.get("depth")
    section_names = schema.get("sectionNames")
    address_types = schema.get("addressTypes")

    return {
        "title": raw.get("title"),
        "heTitle": raw.get("heTitle"),
        "categories": raw.get("categories"),
        "depth": depth,
        "sectionNames": section_names,
        "addressTypes": address_types,
    }


def demo_book_structure():
    print("=== Fetching raw book metadata examples ===")

    examples = [
        "Genesis",
        "Mishneh Torah, Repentance",
    ]

    for title in examples:
        meta = get_book_metadata(title)
        print(f"\n=== Structure for: {title} ===")
        pretty(meta)

    print("\nDone.")


# =====================================================================
#  Combined demo runner
# =====================================================================

def main():
    # 6) Topics
    demo_topics()
    print("\n" + "=" * 80 + "\n")

    # 7) Library tree
    demo_library()
    print("\n" + "=" * 80 + "\n")

    # 8) Book metadata
    demo_book_structure()


if __name__ == "__main__":
    main()