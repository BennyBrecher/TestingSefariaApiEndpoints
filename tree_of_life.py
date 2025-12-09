"""
tree_of_life.py

Build a structured representation of the Sefaria library "Tree of Life"
from the /api/index endpoint.

Exports:
    - fetch_full_library_index()
    - build_library_tree()
    - build_flat_book_list()
    - build_title_lookup()
    - count_nodes()

You can:
    - Run this file directly for a CLI preview & stats.
    - Import it into FastAPI and return `build_library_tree()` as JSON.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

SEFARIA_INDEX_URL = "https://www.sefaria.org/api/index"
CACHE_FILE = Path(__file__).with_name("sefaria_index.json")


# ------------------------------------------------------------
# Fetch + cache raw Sefaria index
# ------------------------------------------------------------

def fetch_full_library_index(force_refresh: bool = False) -> Any:
    """
    Fetch the full Sefaria Table of Contents from /api/index.

    - Uses a JSON file cache alongside this script.
    - Set force_refresh=True to ignore cache and refetch.
    """
    if CACHE_FILE.exists() and not force_refresh:
        logger.info("Loading Sefaria index from cache: %s", CACHE_FILE)
        with CACHE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)

    logger.info("Fetching full Sefaria library index from %s", SEFARIA_INDEX_URL)
    resp = requests.get(SEFARIA_INDEX_URL)
    resp.raise_for_status()
    data = resp.json()

    logger.info("Saving Sefaria index cache to %s", CACHE_FILE)
    with CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return data


# ------------------------------------------------------------
# Tree normalization
# ------------------------------------------------------------

TreeNode = Dict[str, Any]


def _make_category_node(
    title: str,
    he_title: Optional[str],
    path: List[str],
    children: List[TreeNode],
) -> TreeNode:
    return {
        "title": title,
        "heTitle": he_title,
        "type": "category",
        "path": path,
        "children": children,
    }


def _make_book_node(
    title: str,
    he_title: Optional[str],
    path: List[str],
) -> TreeNode:
    return {
        "title": title,
        "heTitle": he_title,
        "type": "book",
        "path": path,
        "children": [],
    }


def _normalize_node(raw: Dict[str, Any], parent_path: List[str]) -> Optional[TreeNode]:
    """
    Convert a single raw /api/index node into our normalized TreeNode.

    /api/index returns a mixed structure:
      - Category nodes usually have keys like:
        { "category": "Tanakh", "heCategory": "...", "contents": [...] }

      - Book (Index) nodes usually have:
        { "title": "Genesis", "heTitle": "בראשית", "categories": ["Tanakh","Torah"], ... }

    We normalize both into our uniform "title / heTitle / type / path / children" shape.
    """

    # Category node
    if "category" in raw:
        title = raw["category"]
        he_title = raw.get("heCategory")
        path = parent_path + [title]

        children_raw = raw.get("contents", []) or []
        children: List[TreeNode] = []
        for child_raw in children_raw:
            child_node = _normalize_node(child_raw, path)
            if child_node is not None:
                children.append(child_node)

        return _make_category_node(title, he_title, path, children)

    # Book (Index) node
    if "title" in raw:
        title = raw["title"]
        he_title = raw.get("heTitle")

        # Prefer explicit categories list if present
        categories = raw.get("categories")
        if isinstance(categories, list) and categories:
            path = categories[:]  # copy
        else:
            path = parent_path + [title]

        return _make_book_node(title, he_title, path)

    # Unknown / unsupported node type: skip it
    return None


def build_library_tree(index_data: Optional[Any] = None) -> TreeNode:
    """
    Build a normalized tree for the entire Sefaria library.

    Root shape:
        {
            "title": "root",
            "heTitle": None,
            "type": "root",
            "path": [],
            "children": [ ...top-level categories... ]
        }

    You can serialize this directly to JSON for FastAPI, etc.
    """
    if index_data is None:
        index_data = fetch_full_library_index()

    if not isinstance(index_data, list):
        raise ValueError("Expected /api/index to return a list at the top level.")

    root: TreeNode = {
        "title": "root",
        "heTitle": None,
        "type": "root",
        "path": [],
        "children": [],
    }

    for raw in index_data:
        node = _normalize_node(raw, parent_path=[])
        if node is not None:
            root["children"].append(node)

    return root


# ------------------------------------------------------------
# Flattening & lookups
# ------------------------------------------------------------

def build_flat_book_list(tree: TreeNode) -> List[Dict[str, Any]]:
    """
    Flatten all book nodes from the tree into a list:
        [
          { "title": "Genesis", "heTitle": "בראשית", "path": ["Tanakh","Torah"] },
          ...
        ]
    """

    books: List[Dict[str, Any]] = []

    def walk(node: TreeNode) -> None:
        node_type = node.get("type")
        if node_type == "book":
            books.append(
                {
                    "title": node["title"],
                    "heTitle": node.get("heTitle"),
                    "path": node.get("path", []),
                }
            )
        for child in node.get("children", []):
            walk(child)

    walk(tree)
    return books


def build_title_lookup(flat_books: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Build a dict mapping BOTH English and Hebrew titles → book record.

    Example:
        lookup["Genesis"] -> {...}
        lookup["בראשית"] -> {...}
    """
    lookup: Dict[str, Dict[str, Any]] = {}
    for b in flat_books:
        title = b.get("title")
        he_title = b.get("heTitle")
        if title:
            lookup[title] = b
        if he_title:
            lookup[he_title] = b
    return lookup


def count_nodes(tree: TreeNode) -> Tuple[int, int]:
    """
    Count (category-like nodes, book nodes).

    Returns:
        (category_count_incl_root, book_count)
    """
    cat_count = 0
    book_count = 0

    def walk(node: TreeNode) -> None:
        nonlocal cat_count, book_count
        node_type = node.get("type")
        if node_type in ("root", "category"):
            cat_count += 1
        elif node_type == "book":
            book_count += 1

        for child in node.get("children", []):
            walk(child)

    walk(tree)
    return cat_count, book_count


# ------------------------------------------------------------
# ASCII preview helpers (for CLI use)
# ------------------------------------------------------------

def _print_top_level_preview(tree: TreeNode, max_children: int = 6) -> None:
    print("=== Tree preview (top-level categories) ===")
    for cat in tree.get("children", []):
        if cat.get("type") != "category":
            # top-level might theoretically include non-category, but usually not
            continue

        children = cat.get("children", [])
        print(f"- {cat['title']} ({len(children)} items)")
        for child in children[:max_children]:
            label = "[Book]" if child.get("type") == "book" else "[Category]"
            print(f"    ▸ {label} {child['title']}")
        if len(children) > max_children:
            print("    ...")


def _find_child_by_title(tree: TreeNode, title: str) -> Optional[TreeNode]:
    for child in tree.get("children", []):
        if child.get("title") == title:
            return child
    return None


def _print_ascii_tree(node: TreeNode, max_depth: int = 3) -> None:
    print(node["title"])
    children = node.get("children", [])
    for idx, child in enumerate(children):
        is_last = (idx == len(children) - 1)
        _print_ascii_recursive(child, prefix="", is_last=is_last, depth=1, max_depth=max_depth)


def _print_ascii_recursive(
    node: TreeNode,
    prefix: str,
    is_last: bool,
    depth: int,
    max_depth: int,
) -> None:
    if depth > max_depth:
        return

    connector = "└─ " if is_last else "├─ "
    print(prefix + connector + node["title"])

    if depth == max_depth:
        return

    child_prefix = prefix + ("   " if is_last else "│  ")
    children = node.get("children", [])
    for idx, child in enumerate(children):
        child_is_last = (idx == len(children) - 1)
        _print_ascii_recursive(
            child,
            prefix=child_prefix,
            is_last=child_is_last,
            depth=depth + 1,
            max_depth=max_depth,
        )


# ------------------------------------------------------------
# Script entrypoint (mirrors your old CLI behavior)
# ------------------------------------------------------------

def main() -> None:
    # 1) Fetch + build tree
    index_data = fetch_full_library_index()
    tree = build_library_tree(index_data)

    # 2) Preview top-level
    _print_top_level_preview(tree)

    # 3) ASCII tree for Tanakh (if present)
    print("\n=== ASCII tree (Tanakh subtree, depth 3) ===")
    tanakh = _find_child_by_title(tree, "Tanakh")
    if tanakh:
        _print_ascii_tree(tanakh, max_depth=3)
    else:
        print("(Tanakh category not found in tree)")

    # 4) Stats
    cat_count, book_count = count_nodes(tree)
    flat_books = build_flat_book_list(tree)
    lookup = build_title_lookup(flat_books)

    print("\n=== Stats ===")
    # cat_count includes root; if you want exactly "top-level categories",
    # that's just len(tree["children"])
    print(f"Total categories tree nodes: {len(tree['children'])}")
    print(f"Total books flattened:       {len(flat_books)}")
    print(f"Total lookup keys:           {len(lookup)}")

    # 5) Sample first 10
    print("\n=== First 10 books ===")
    for b in flat_books[:10]:
        path_str = " > ".join(b["path"])
        he = b.get("heTitle")
        if he:
            print(f"- {b['title']} ({he}) [{path_str}]")
        else:
            print(f"- {b['title']} [{path_str}]")

    # 6) Sample lookups
    print("\n=== Sample lookups ===")
    for key in ["Genesis", "בראשית", "Shabbat", "Berakhot"]:
        val = lookup.get(key)
        print(f"'{key}' -> {val}")


if __name__ == "__main__":
    main()
