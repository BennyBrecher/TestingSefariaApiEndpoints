import requests
import json

BASE = "https://www.sefaria.org"


def pretty(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# ---------- 1) Raw wrapper around /api/v2/raw/index/{title} ----------

def get_raw_index(title: str) -> dict:
    """
    Wrapper around /api/v2/raw/index/{title}

    'title' is a Sefaria index title, e.g.:
      - "Genesis"
      - "Mishneh Torah, Repentance"
      - "Mishnah Berakhot"
      - "Berakhot"

    Spaces are converted to underscores for the URL.
    """
    title_url = title.replace(" ", "_")
    url = f"{BASE}/api/v2/raw/index/{title_url}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------- 2) Extract just the structure MM cares about ----------

def extract_book_structure(raw_index: dict) -> dict:
    """
    Normalize the raw index object into a compact structure
    MarehMakom can use to:
      - understand how many levels (depth) a book has
      - see the names of each level (sectionNames)
      - see category path (Tanakh / Halakhah / etc.)

    Typical Sefaria raw index has:
      - "title"
      - "heTitle"
      - "categories": ["Halakhah", "Mishneh Torah", ...]
      - "schema": {
            "depth": 3,
            "sectionNames": ["Sefer", "Perek", "Halakha"],
            "addressTypes": ["Integer", "Integer", "Integer"],
            ...
        }
    """
    schema = raw_index.get("schema") or {}

    depth = schema.get("depth")
    section_names = schema.get("sectionNames")
    address_types = schema.get("addressTypes")

    # Be defensive if something is missing
    if not isinstance(section_names, list):
        section_names = []
    if not isinstance(address_types, list):
        address_types = []

    return {
        "title": raw_index.get("title"),
        "heTitle": raw_index.get("heTitle"),
        "categories": raw_index.get("categories", []),
        "depth": depth,
        "sectionNames": section_names,
        "addressTypes": address_types,
    }


# ---------- 3) Demo / CLI ----------

def demo_one(title: str):
    print(f"\n=== Structure for: {title} ===")
    raw = get_raw_index(title)
    struct = extract_book_structure(raw)
    pretty(struct)


def demo():
    print("=== Fetching raw book metadata examples ===")

    # 1) Simple Tanakh book
    demo_one("Genesis")

    # 2) Classic halakhic work with deeper structure
    #    (If this 404s, just change the title to something you know exists.)
    try:
        demo_one("Mishneh Torah, Repentance")
    except requests.HTTPError as e:
        print(f"\n(Mishneh Torah, Repentance lookup failed: {e})")

    print("\nDone.")


if __name__ == "__main__":
    demo()