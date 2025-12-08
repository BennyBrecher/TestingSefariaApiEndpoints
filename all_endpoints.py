import json
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ---------- Shared session with retries ----------

def make_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,  # 1s, 2s, 4s
        status_forcelist=[502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


session = make_session()
BASE = "https://www.sefaria.org"


def pretty(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# ---------- 1) POST /api/find-refs  (explicit refs) ----------

def test_find_refs():
    url = f"{BASE}/api/find-refs"
    body_text = 'כמו שכתב הרמב"ם בהלכות תשובה ב:א על ענין התשובה...'

    payload = {
        "text": {
            "title": "",
            "body": body_text
        }
    }
    params = {
        "with_text": 0,
        "debug": 0,
        "max_segments": 0
    }

    resp = session.post(url, json=payload, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    print("=== FIND-REFS raw ===")
    pretty(data)

    # Flatten out body results into a simple list
    print("\n=== Simplified results ===")
    for r in data.get("body", {}).get("results", []):
        for ref in r.get("refs", []):
            print(
                f"text='{r.get('text')}' "
                f"→ ref={ref} "
                f"(chars {r['startChar']}–{r['endChar']})"
            )


# ---------- 2) POST /api/search-wrapper  (implicit refs) ----------

def test_search_wrapper():
    url = f"{BASE}/api/search-wrapper"

    payload = {
        "query": "שובה ישראל עד ה׳ אלקיך",
        "type": "text",
        "size": 5  # top 5 hits
    }

    resp = session.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    print("=== SEARCH-WRAPPER raw ===")
    pretty(data)

    print("\n=== Top hits (ref + score) ===")
    for hit in data.get("hits", []):
        fields = hit.get("fields", {})
        print(
            f"ref={fields.get('ref')} "
            f"score={hit.get('score')} "
            f"he={fields.get('he')}"
        )


# ---------- 3) GET /api/v3/texts/{ref}  (Torah text) ----------

def test_texts_v3():
    tref = "Mishneh Torah, Repentance 2:1"
    url = f"{BASE}/api/v3/texts/{quote(tref, safe='')}"

    params = {
        "context": 0,      # 0 = only this ref, >0 = include neighbors
        "commentary": 0
    }

    resp = session.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    print("=== TEXTS v3 raw ===")
    pretty(data)

    print("\n=== Simple view ===")
    print("Ref:", data.get("ref"))
    print("HE:", data.get("he"))
    print("EN:", data.get("en"))


# ---------- 4) GET /api/links/{ref}  (commentaries / cross-refs) ----------

def test_links():
    tref = "Genesis 1:1"
    url = f"{BASE}/api/links/{quote(tref, safe='')}"

    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    print("=== LINKS raw (first 5) ===")
    pretty(data[:5])

    print("\n=== Simple commentary view ===")
    for link in data[:10]:
        print(
            f"type={link.get('type')}  "
            f"sourceRef={link.get('sourceRef')}  "
            f"ref={link.get('ref')}"
        )


# ---------- 5) GET /api/ref-topic-links/{ref}  (topics per ref) ----------

def test_ref_topic_links():
    tref = "Genesis 1:1"
    url = f"{BASE}/api/ref-topic-links/{quote(tref, safe='')}"

    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    print("=== REF-TOPIC-LINKS raw ===")
    pretty(data)

    print("\n=== Simplified topics ===")
    for t in data:
        print(
            "topic_slug=", t.get("slug"),
            " | ref:", t.get("ref"),
            " | linkType:", t.get("linkType")
        )


# ---------- 6) GET /api/topics  (all topics – topic browser) ----------

def test_topics():
    url = f"{BASE}/api/topics"

    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    topics = resp.json()

    print(f"=== TOPICS: got {len(topics)} topics, showing first 5 ===")
    for t in topics[:5]:
        print(
            "slug=", t.get("slug"),
            "| en=", t.get("en"),
            "| he=", t.get("he")
        )


# ---------- 7) GET /api/index  (full library tree) ----------

def test_index():
    url = f"{BASE}/api/index"

    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    print("=== INDEX: top-level categories ===")
    for cat in data[:10]:
        print("- category:", cat.get("category"))

    print("\nExample: first category full structure:")
    pretty(data[0])


# ---------- 8) GET /api/v2/raw/index/{title}  (book metadata / levels) ----------

def test_raw_index():
    title = "Mishneh Torah"
    url = f"{BASE}/api/v2/raw/index/{quote(title, safe='')}"

    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    print("=== RAW INDEX ===")
    print("Title:", data.get("title"))
    print("Categories:", data.get("categories"))

    schema = data.get("schema", {})
    print("\nSchema:")
    pretty(schema)

    print("\nDepth:", schema.get("depth"))
    print("Section names:", schema.get("sectionNames"))


# ---------- 9) GET /api/related/{ref}  (related links / topics / media) ----------

def test_related():
    tref = "Genesis 1:1"
    url = f"{BASE}/api/related/{quote(tref, safe='')}"

    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    print(f"Reference: {tref}\n")
    print("Top-level keys:", list(data.keys()), "\n")

    # LINKS
    print("=== LINKS (first 5) ===")
    for link in data.get("links", [])[:5]:
        print(
            "-", link.get("sourceRef"),
            "→", link.get("ref"),
            "| type:", link.get("type")
        )

    # TOPICS
    topics = data.get("topics", [])
    print("\n=== TOPICS (first 5, simplified) ===")
    for t in topics[:5]:
        title = t.get("title") or {}
        print(
            "-", t.get("topic"),
            "|", title.get("en"),
            "|", title.get("he")
        )

    # MEDIA
    media = data.get("media", [])
    print("\n=== MEDIA (first 3, simplified) ===")
    for m in media[:3]:
        print(
            "-", m.get("source"), "/", m.get("source_he"),
            "\n   URL:", m.get("media_url"),
            "\n   Desc:", (m.get("description") or "")[:80], "..."
        )


# ---------- MAIN ----------

if __name__ == "__main__":
    # Uncomment ONE at a time to play:

    # test_find_refs()
    # test_search_wrapper()
    # test_texts_v3()
    # test_links()
    # test_ref_topic_links()
    # test_topics()
    # test_index()
    # test_raw_index()
    # test_related()

    # Example: start with this:
    test_find_refs()