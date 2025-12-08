import requests
import json

BASE = "https://www.sefaria.org"


def pretty(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# ---------- 1) Raw library index ----------

def get_library_index() -> list[dict]:
    """
    Wrapper around /api/index

    Returns the full Sefaria library tree:
    [
      {
        "category": "Tanakh",
        "contents": [ ... ]
      },
      ...
    ]
    """
    url = f"{BASE}/api/index"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


# ---------- 2) Flatten tree into books ----------

def flatten_library_tree(tree: list[dict]) -> list[dict]:
    """
    Turn the nested 'categories + contents' structure into a flat list of books.

    Each book dict looks like:
      {
        "title": "Genesis",
        "heTitle": "בראשית",
        "categories": ["Tanakh", "Torah"]
      }
    """

    books: list[dict] = []

    def _walk(node_list: list[dict], trail: list[str]):
        for node in node_list:
            # category node (has 'category' + 'contents')
            if "category" in node and "contents" in node:
                new_trail = trail + [node["category"]]
                _walk(node["contents"], new_trail)
            # book / index node (has 'title')
            elif "title" in node:
                books.append(
                    {
                        "title": node["title"],
                        "heTitle": node.get("heTitle"),
                        "categories": trail[:],  # copy
                    }
                )

    _walk(tree, [])
    return books


# ---------- 3) Build lookup helper ----------

def build_book_lookup(books: list[dict]) -> dict[str, dict]:
    """
    Build a case-insensitive lookup dict from titles/heTitles → book info.

    Example entry:
      "genesis" -> {
        "title": "Genesis",
        "heTitle": "בראשית",
        "categories": ["Tanakh", "Torah"]
      }
    """
    lookup: dict[str, dict] = {}

    for b in books:
        title = b.get("title")
        he_title = b.get("heTitle")

        if isinstance(title, str):
            lookup[title.lower()] = b
        if isinstance(he_title, str):
            # Hebrew we keep as-is, not lowercased
            lookup[he_title] = b

    return lookup


# ---------- 4) Tree-ish printing helpers ----------

def print_tree_preview(tree: list[dict], max_categories: int = 3, max_children: int = 5):
    """
    Just for quick debugging: show a small, indented top-level preview.
    """
    print("=== Tree preview (top-level categories) ===")
    for cat in tree[:max_categories]:
        cat_name = cat.get("category", "<no category>")
        contents = cat.get("contents") or []
        print(f"- {cat_name} ({len(contents)} items)")

        # show first few children under each category
        for child in contents[:max_children]:
            if "category" in child:
                print(f"    ▸ [Category] {child['category']}")
            elif "title" in child:
                print(f"    • [Book] {child['title']} ({child.get('heTitle', '')})")
        if len(contents) > max_children:
            print("    ...")


def print_ascii_tree(node: dict, prefix: str = "", max_depth: int = 3, max_children: int = 10):
    """
    Pretty ASCII tree printer for ONE subtree (category node).

    Example:

    Tanakh
    ├─ Torah
    │  ├─ Genesis
    │  ├─ Exodus
    │  └─ ...
    └─ Prophets
       ├─ Joshua
       └─ ...
    """
    if max_depth < 0:
        return

    # root label
    if "category" in node:
        label = node["category"]
    elif "title" in node:
        label = node["title"]
    else:
        label = "<node>"

    print(prefix + label)

    contents = node.get("contents") or []
    if max_depth == 0 or not contents:
        return

    # only show first N children so we don't dump 6K lines
    shown = contents[:max_children]
    last_index = len(shown) - 1

    for i, child in enumerate(shown):
        is_last = (i == last_index)
        branch = "└─ " if is_last else "├─ "
        child_prefix = prefix + ("   " if is_last else "│  ")

        # child label:
        if "category" in child:
            label = child["category"]
        elif "title" in child:
            label = child["title"]
        else:
            label = "<node>"

        print(prefix + branch + label)

        # if this child has its own contents, recurse one level deeper
        if "contents" in child and child["contents"] and max_depth > 1:
            print_ascii_tree(child, child_prefix, max_depth=max_depth - 1, max_children=max_children)


# ---------- 5) Demo ----------

def demo():
    print("=== Fetching full Sefaria library index ===")
    tree = get_library_index()

    # 1) Show small top-level preview (like before)
    print_tree_preview(tree, max_categories=3, max_children=5)

    # 2) Show an actual ASCII tree for the Tanakh subtree
    print("\n=== ASCII tree (Tanakh subtree, depth 3) ===")
    tanakh_node = next((n for n in tree if n.get("category") == "Tanakh"), None)
    if tanakh_node:
        print_ascii_tree(tanakh_node, prefix="", max_depth=3, max_children=10)
    else:
        print("(Tanakh category not found?)")

    # 3) Flatten + lookup, like before
    flat_books = flatten_library_tree(tree)
    book_lookup = build_book_lookup(flat_books)

    print("\n=== Stats ===")
    print(f"Total categories tree nodes: {len(tree)}")
    print(f"Total books flattened:       {len(flat_books)}")
    print(f"Total lookup keys:           {len(book_lookup)}")

    print("\n=== First 10 books ===")
    for b in flat_books[:10]:
        cats = " > ".join(b["categories"])
        print(f"- {b['title']} ({b.get('heTitle')}) [{cats}]")

    print("\n=== Sample lookups ===")
    for key in ["Genesis", "בראשית", "Shabbat", "Berakhot"]:
        # English keys use .lower(), Hebrew stays raw
        if key.isascii():
            data = book_lookup.get(key.lower())
        else:
            data = book_lookup.get(key)
        print(f"'{key}' -> {data}")


if __name__ == "__main__":
    demo()