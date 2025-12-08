import json
import requests

BASE = "https://www.sefaria.org"


def pretty(obj):
    """Helper: pretty-print JSON with UTF-8 Hebrew support."""
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def search_implicit_refs(query: str, size: int = 5, debug: bool = True):
    """
    High-level helper for MarehMakom using /api/search-wrapper.

    What it actually does (based on real response):

      - Sends a full-text search query over the Sefaria library.
      - Returns a list of "hits", each with:
          * _id      : which work/section it's from (e.g., a sefer + location)
          * _score   : how good the match is
          * highlight: HTML snippet showing the match in context

    This is **not** a direct "canonical ref for a pasuk" API.
    It's a general text search engine that can answer:
        "Where in the library does this phrase appear?"

    Output:
        List[dict]:
            {
                "doc_id": str,           # hit["_id"]
                "score": float,          # hit["_score"]
                "highlight_html": str|None  # first highlight snippet (HTML)
            }
    """
    url = f"{BASE}/api/search-wrapper"

    payload = {
        "query": query,
        "type": "text",   # text search across the library
        "size": size
    }

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if debug:
        print("=== RAW RESPONSE FROM /api/search-wrapper ===")
        pretty(data)

    results = []

    # Real shape:
    # data["hits"] is a dict with:
    #   { "total": ..., "max_score": ..., "hits": [ ...hit dicts... ] }
    hits_block = data.get("hits", {})

    # If hits_block is a dict, drill into "hits" list.
    # If they ever change to a direct list, we still handle that.
    if isinstance(hits_block, dict):
        inner_hits = hits_block.get("hits", [])
    else:
        inner_hits = hits_block

    if not isinstance(inner_hits, list):
        return results  # unexpected shape; return empty list

    for hit in inner_hits:
        if not isinstance(hit, dict):
            continue

        doc_id = hit.get("_id")
        score = hit.get("_score")

        # highlight is usually:
        # "highlight": { "exact": ["<b>שובה</b> ..."] }
        highlight_html = None
        highlight = hit.get("highlight") or {}
        if isinstance(highlight, dict):
            # Prefer "exact" key if present
            exact_list = highlight.get("exact") or []
            if isinstance(exact_list, list) and exact_list:
                highlight_html = exact_list[0]

        results.append({
            "doc_id": doc_id,
            "score": score,
            "highlight_html": highlight_html,
        })

    return results


def test_search_wrapper():
    """
    Demo for /api/search-wrapper.

    We send a short pasuk fragment and print the top matches.
    """
    query = "שובה ישראל עד ה׳ אלקיך"

    results = search_implicit_refs(query, size=5, debug=True)

    print(f"\n=== PARSED SEARCH-WRAPPER results for query: {query!r} ===")
    if not results:
        print("(no hits parsed)")
        return

    for r in results:
        snippet = r["highlight_html"] or ""
        print(
            f"score={r['score']:6.2f} | "
            f"doc_id={r['doc_id']} | "
            f"snippet={snippet[:80]}..."
        )



if __name__ == "__main__":
    test_search_wrapper()