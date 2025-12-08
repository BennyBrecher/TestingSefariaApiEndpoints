import requests
import json

BASE = "https://www.sefaria.org"


def pretty(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def get_related_content(ref: str):
    """
    Wrapper around /api/related/{ref}
    Returns:
      {
        "links": [...],
        "topics": [...],
        "sheets": [...],
        "media": [...]
      }
    """
    ref_url = ref.replace(" ", "_")
    url = f"{BASE}/api/related/{ref_url}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def demo_related(ref="Genesis 1:1"):
    print(f"=== Fetching related content for: {ref} ===")

    data = get_related_content(ref)

    # Show stats
    print("\n=== Counts ===")
    print("Links :", len(data.get("links", [])))
    print("Topics:", len(data.get("topics", [])))
    print("Sheets:", len(data.get("sheets", [])))
    print("Media :", len(data.get("media", [])))

    # Preview a sample of each
    print("\n=== Sample Links ===")
    pretty(data.get("links", [])[:3])

    print("\n=== Sample Topics ===")
    pretty(data.get("topics", [])[:3])

    print("\n=== Sample Sheets ===")
    pretty(data.get("sheets", [])[:3])

    print("\n=== Sample Media ===")
    pretty(data.get("media", [])[:3])


if __name__ == "__main__":
    demo_related()