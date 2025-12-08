import json
import re
import requests

BASE = "https://www.sefaria.org"


def pretty(obj):
    """Helper: pretty-print JSON with UTF-8 Hebrew support."""
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def _strip_html(s: str) -> str:
    """Very simple HTML tag stripper for snippets."""
    return re.sub(r"<[^>]+>", "", s)


def search_implicit_refs(query: str, size: int = 5, debug: bool = False):
    """
    Neat helper for MarehMakom using /api/search-wrapper.

    Input:
        query: phrase to search for (Heb/Eng)
        size : number of top hits to return

    Output:
        List[dict]:
            {
                "doc_id": str,        # raw Sefaria _id
                "title": str,         # shorter title (doc_id chopped before '(')
                "score": float,
                "snippet_html": str|None,
                "snippet": str|None   # plain text, HTML stripped
            }
    """
    url = f"{BASE}/api/search-wrapper"

    payload = {
        "query": query,
        "type": "text",
        "size": size,
    }

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if debug:
        print("=== RAW RESPONSE FROM /api/search-wrapper ===")
        pretty(data)

    results = []

    hits_block = data.get("hits", {})
    inner_hits = hits_block.get("hits", []) if isinstance(hits_block, dict) else hits_block

    if not isinstance(inner_hits, list):
        return results

    for hit in inner_hits:
        if not isinstance(hit, dict):
            continue

        doc_id = hit.get("_id")
        score = hit.get("_score")

        # highlight → first "exact" snippet, if present
        highlight_html = None
        highlight = hit.get("highlight") or {}
        if isinstance(highlight, dict):
            exact_list = highlight.get("exact") or []
            if isinstance(exact_list, list) and exact_list:
                highlight_html = exact_list[0]

        # shorter title: cut off edition info in parentheses
        title = doc_id.split("(")[0].strip() if isinstance(doc_id, str) else doc_id

        snippet_plain = _strip_html(highlight_html) if isinstance(highlight_html, str) else None

        results.append({
            "doc_id": doc_id,
            "title": title,
            "score": score,
            "snippet_html": highlight_html,
            "snippet": snippet_plain,
        })

    return results


def test_search_wrapper():
    """
    Standalone demo for this file only.
    Not used by MarehMakom core; just for manual testing.
    """
    query = "שובה ישראל עד ה׳ אלקיך"

    results = search_implicit_refs(query, size=5, debug=True)

    print(f"\n=== PARSED SEARCH-WRAPPER results for query: {query!r} ===")
    if not results:
        print("(no hits parsed)")
        return

    for r in results:
        snippet = (r["snippet"] or "")[:80]
        print(
            f"score={r['score']:6.2f} | "
            f"title={r['title']} | "
            f"snippet={snippet}..."
        )


if __name__ == "__main__":
    test_search_wrapper()