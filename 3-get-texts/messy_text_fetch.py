import requests
import json

BASE = "https://www.sefaria.org"

def pretty(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))

def get_text(ref: str, lang="he", commentary=False):
    """
    Call Sefaria's /api/texts/{ref}

    Parameters:
        ref: canonical ref, e.g. "Genesis 1:1", "Berakhot 2a"
        lang: "he" or "en"
        commentary: include or exclude meforshim

    Returns:
        dict with keys:
        - 'he' / 'text' etc depending on response
        - 'lang'
        - metadata
    """

    ref_url = ref.replace(" ", "_")  # Sefaria convention: spaces → underscores
    url = f"{BASE}/api/texts/{ref_url}"

    params = {
        "lang": lang,           # he/en
        "commentary": "1" if commentary else "0"
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    return resp.json()


def test_texts_api():
    ref = "Genesis 1:1"

    print(f"=== Fetching text for: {ref} ===")
    data = get_text(ref, lang="he", commentary=False)

    pretty(data)

    print("\n=== Plain Hebrew Lines ===")
    for line in data.get("he", []):
        print(line)


if __name__ == "__main__":
    test_texts_api()