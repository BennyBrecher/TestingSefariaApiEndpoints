import requests
import json

BASE = "https://www.sefaria.org"


def pretty(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def get_all_topics():
    """
    Wrapper around /api/topics
    Returns the raw list Sefaria gives us.
    """
    url = f"{BASE}/api/topics"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def simplify_topics(raw_topics):
    """
    Turn raw topic objects into a simpler structure:

      [
        { "slug": "teshuvah", "en": "Repentance", "he": "תשובה" },
        ...
      ]

    We pull labels from the 'titles' array (primary titles if possible).
    """
    simple = []
    for item in raw_topics:
        if not isinstance(item, dict):
            continue

        slug = item.get("slug")
        if not isinstance(slug, str):
            continue

        titles = item.get("titles") or []

        en_title = None
        he_title = None

        # First pass: primary titles
        for t in titles:
            if not isinstance(t, dict):
                continue
            text = t.get("text")
            lang = t.get("lang")
            primary = t.get("primary", False)

            if not isinstance(text, str):
                continue

            if primary and lang == "en" and en_title is None:
                en_title = text
            if primary and lang == "he" and he_title is None:
                he_title = text

        # Second pass: any titles (fallback if no primary was found)
        if en_title is None or he_title is None:
            for t in titles:
                if not isinstance(t, dict):
                    continue
                text = t.get("text")
                lang = t.get("lang")

                if not isinstance(text, str):
                    continue

                if en_title is None and lang == "en":
                    en_title = text
                if he_title is None and lang == "he":
                    he_title = text

        simple.append(
            {
                "slug": slug,
                "en": en_title,
                "he": he_title,
            }
        )

    return simple


def build_topic_lookup(simple_topics):
    """
    Build a dict mapping slug → {en, he} to use as a lookup table.
    """
    lookup = {}
    for t in simple_topics:
        slug = t["slug"]
        lookup[slug] = {"en": t["en"], "he": t["he"]}
    return lookup


def demo():
    print("=== Fetching ALL topics from Sefaria ===\n")
    raw = get_all_topics()
    simple = simplify_topics(raw)
    lookup = build_topic_lookup(simple)

    print(f"Total raw topics:    {len(raw)}")
    print(f"Total simple topics: {len(simple)}\n")

    print("=== First 10 simplified topics ===")
    for t in simple[:10]:
        print(f"- {t['slug']}: {t['en']} / {t['he']}")

    print("\n=== Sample lookup entries ===")
    for slug in [t["slug"] for t in simple[:5]]:
        print(slug, "->", lookup[slug])


if __name__ == "__main__":
    demo()