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
            lookup[he_title] = b   # don't .lower() Hebrew

    return lookup


# ---------- 4) Debug / demo ----------

def print_tree_preview(tree: list[dict], max_categories: int = 3, max_children: int = 5):
    """
    Just for debugging: show a small, indented tree preview so it "feels" like a tree.
    """
    print("=== Tree preview (top-level categories) ===")
    for cat in tree[:max_categories]:
        cat_name = cat.get("category", "<no category>")
        contents = cat.get("contents") or []
        print(f"- {cat_name} ({len(contents)} items)")

        # show first few children under each category
        for child in contents[:max_children]:
            # child can be a subcategory or a book
            if "category" in child:
                print(f"    ▸ [Category] {child['category']}")
            elif "title" in child:
                print(f"    • [Book] {child['title']} ({child.get('heTitle', '')})")
        if len(contents) > max_children:
            print("    ...")


def demo():
    print("=== Fetching full Sefaria library index ===")
    tree = get_library_index()

    # 1) Show a small tree preview so you see the hierarchy
    print_tree_preview(tree, max_categories=3, max_children=5)

    # 2) Flatten + lookup, like before
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
    for key in ["Genesis", "Bereshit", "Shabbat", "Berakhot"]:
        data = book_lookup.get(key.lower()) if key != "בראשית" else book_lookup.get(key)
        print(f"'{key}' -> {data}")


if __name__ == "__main__":
    demo()