import requests
import json
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def make_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = make_session()

def test_related(tref: str):
    base = "https://www.sefaria.org/api/related/"
    url = base + quote(tref, safe='')

    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    print(f"Reference: {tref}\n")
    print("Top-level keys:", list(data.keys()), "\n")

    # 1) LINKS
    print("=== LINKS (textual connections) ===")
    for link in data.get("links", [])[:5]:
        print("-", link.get("sourceRef"), "→", link.get("ref"), "| type:", link.get("type"))

    # 2) Peek at raw structure for topics and media
    topics = data.get("topics", [])
    media  = data.get("media", [])

    if topics:
        print("\nRAW TOPIC EXAMPLE:\n", json.dumps(topics[0], indent=2, ensure_ascii=False))
    else:
        print("\n(no topics returned)")

    if media:
        print("\nRAW MEDIA EXAMPLE:\n", json.dumps(media[0], indent=2, ensure_ascii=False))
    else:
        print("\n(no media returned)")

    # 3) Now, try a best-guess pretty print for topics/media based on common shapes
    print("\n=== TOPICS (best-effort) ===")
    for t in topics[:5]:
        # common structures: {"slug": "...", "primaryTitle": {"en": "...", "he": "..."}} or similar
        slug = t.get("slug")
        en = (
            t.get("en")
            or (t.get("primaryTitle") or {}).get("en")
            or (t.get("title") or {}).get("en")
        )
        he = (
            t.get("he")
            or (t.get("primaryTitle") or {}).get("he")
            or (t.get("title") or {}).get("he")
        )
        print("-", slug, "|", en, "|", he)

    print("\n=== MEDIA (best-effort) ===")
    for m in media[:5]:
        title = m.get("title") or m.get("enTitle")
        mtype = m.get("mediaType")
        link  = m.get("link") or m.get("url")
        print("-", title, "| type:", mtype, "| url:", link)


if __name__ == "__main__":
    test_related("Genesis 1:1")


''' A realistic MM wrapper would be:
from urllib.parse import quote
import requests

def mm_related_summary(tref: str):
    url = "https://www.sefaria.org/api/related/" + quote(tref, safe='')
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # keep only commentaries
    commentaries = [
        l for l in data.get("links", [])
        if l.get("type") == "commentary"
    ]

    topics_out = []
    for t in data.get("topics", []):
        slug = t.get("topic")
        title = t.get("title") or {}
        topics_out.append({
            "slug": slug,
            "en": title.get("en"),
            "he": title.get("he")
        })

    media_out = []
    for m in data.get("media", []):
        media_out.append({
            "source_en": m.get("source"),
            "source_he": m.get("source_he"),
            "url": m.get("media_url"),
            "description": m.get("description")
        })

    return {
        "commentaries": commentaries,
        "topics": topics_out,
        "media": media_out
    }
    '''