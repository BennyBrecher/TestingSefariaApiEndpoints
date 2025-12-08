import requests
import json

BASE = "https://www.sefaria.org"

# Pick ONE canonical Hebrew base text for your project.
# This matches the "heVersionTitle" field from Sefaria's response.
DEFAULT_HE_VERSION = "Miqra according to the Masorah"


def pretty(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def get_text(ref: str, lang: str = "he", commentary: bool = False, version: str | None = None):
    """
    Call Sefaria's /api/texts/{ref}

    Parameters:
        ref        : canonical ref, e.g. "Genesis 1:1", "Berakhot 2a"
        lang       : "he" or "en"
        commentary : include or exclude meforshim
        version    : optional specific versionTitle / heVersionTitle to pin

    Returns:
        dict with keys from Sefaria's API, including:
          - 'he' / 'text'
          - metadata like 'versionTitle', 'heVersionTitle', 'next', 'prev', etc.
    """

    ref_url = ref.replace(" ", "_")  # Sefaria convention: spaces → underscores
    url = f"{BASE}/api/texts/{ref_url}"

    params: dict[str, object] = {
        "lang": lang,
        "commentary": "1" if commentary else "0",
    }

    if version is not None:
        # Pin a specific edition instead of "whatever Sefaria's default is"
        params["version"] = version

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    return resp.json()


def test_texts_api():
    ref = "Genesis 1:1"

    print(f"=== Fetching text for: {ref} ===")
    data = get_text(ref, lang="he", commentary=False, version=DEFAULT_HE_VERSION)

    print("\n=== VERSION INFO ===")
    print("versionTitle   :", data.get("versionTitle"))
    print("heVersionTitle :", data.get("heVersionTitle"))

    print("\n=== BASIC METADATA ===")
    print("ref        :", data.get("ref"))
    print("heTitle    :", data.get("heTitle"))
    print("sectionNames:", data.get("sectionNames"))
    print("sections   :", data.get("sections"))

    print("\n=== Plain Hebrew Lines (raw from API) ===")
    for line in data.get("he", []):
        print(line)


if __name__ == "__main__":
    test_texts_api()