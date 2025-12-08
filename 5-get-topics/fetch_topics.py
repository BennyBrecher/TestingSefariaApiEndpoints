import requests
import json

BASE = "https://www.sefaria.org"


# ---------- utils ----------

def pretty(obj):
    """Nice JSON print helper."""
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# ---------- API wrapper ----------

def get_ref_topics(ref: str):
    """
    Wrapper around /api/ref-topic-links/{ref}.

    Returns the raw list Sefaria gives, where each item is a dict
    containing at least a "topic" field (e.g. "creation", "earth"...).
    """
    ref_url = ref.replace(" ", "_")
    url = f"{BASE}/api/ref-topic-links/{ref_url}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------- topic normalization ----------

def extract_topic_slugs(raw_topics) -> list[str]:
    """
    Normalize the response into a flat list of topic ids
    (what we’ll store on refs for tagging/search).

    Example: ["creation", "heavens", "creation-of-heavens-and-earth"]
    """
    slugs: list[str] = []

    if not isinstance(raw_topics, list):
        return slugs

    for item in raw_topics:
        if not isinstance(item, dict):
            continue
        slug = item.get("topic")   # <-- Sefaria field name
        if isinstance(slug, str):
            slugs.append(slug)

    # dedupe while preserving order
    seen = set()
    uniq: list[str] = []
    for s in slugs:
        if s not in seen:
            seen.add(s)
            uniq.append(s)

    return uniq


def extract_topic_objects(raw_topics) -> list[dict]:
    """
    Return compact topic objects for UI / DB:

    {
      "id": "creation-of-heavens-and-earth",
      "title": "In the Beginning",
      "source": "learning-team"
    }
    """
    topics: list[dict] = []

    if not isinstance(raw_topics, list):
        return topics

    for item in raw_topics:
        if not isinstance(item, dict):
            continue

        topic_id = item.get("topic")
        if not isinstance(topic_id, str):
            continue

        data_source = item.get("dataSource") or {}
        source_slug = data_source.get("slug")

        descriptions = item.get("descriptions") or {}
        en_desc = descriptions.get("en") or {}
        title = en_desc.get("title") or en_desc.get("ai_title")

        topics.append({
            "id": topic_id,
            "title": title,
            "source": source_slug,
        })

    # dedupe by id while preserving order
    seen = set()
    uniq: list[dict] = []
    for t in topics:
        if t["id"] not in seen:
            seen.add(t["id"])
            uniq.append(t)

    return uniq


# ---------- quick CLI test ----------

def test_topics_api():
    ref = "Genesis 1:1"
    print(f"=== Fetching topics for: {ref} ===")

    raw = get_ref_topics(ref)

    topic_ids = extract_topic_slugs(raw)
    topic_objs = extract_topic_objects(raw)

    print("\n=== RAW TOPIC LINKS (first 5, for debugging) ===")
    pretty(raw[:5])

    print("\n=== TOPIC IDS (for MM tagging / search) ===")
    for s in topic_ids:
        print("-", s)

    print("\n=== TOPIC OBJECTS (for UI) ===")
    pretty(topic_objs[:5])


if __name__ == "__main__":
    test_topics_api()