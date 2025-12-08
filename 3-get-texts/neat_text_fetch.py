import requests
import json
import re
import html

BASE = "https://www.sefaria.org"

# Same canonical Hebrew base text as in basic_text_fetch.py
DEFAULT_HE_VERSION = "Miqra according to the Masorah"


def pretty(obj):
    """Debug helper: pretty-print JSON."""
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def get_text(ref: str, lang: str = "he", context: int = 0, version: str | None = None):
    """
    Small wrapper around /api/texts/{ref}.

    ref     : e.g. "Genesis 1:1"
    lang    : "he" or "en"
    context : 0 = just that ref, 1 = surrounding section, etc.
    version : optional specific versionTitle / heVersionTitle
    """
    ref_url = ref.replace(" ", "_")
    url = f"{BASE}/api/texts/{ref_url}"

    params: dict[str, object] = {
        "lang": lang,
        "commentary": 0,
        "context": context,
    }
    if version is not None:
        params["version"] = version

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


# very forgiving tag-stripper: <...>
TAG_RE = re.compile(r"<.*?>", flags=re.DOTALL)


def clean_he_string(raw: str) -> str:
    """
    Take a raw Hebrew string from Sefaria and return a cleaned version:

      - HTML entities decoded (&thinsp;, &nbsp;, &amp;, etc.)
      - HTML tags (<big>, <span>, etc.) stripped
      - whitespace normalized
    """
    # 1) Decode HTML entities
    s = html.unescape(raw)

    # 2) Strip HTML tags
    s = TAG_RE.sub("", s)

    # 3) Normalize whitespace (spaces, newlines, NBSP, etc.)
    s = s.replace("\u00a0", " ")   # NBSP → space
    s = " ".join(s.split())        # collapse whitespace

    return s


def test_texts_api():
    ref = "Genesis 1:1"

    data = get_text(ref, lang="he", context=0, version=DEFAULT_HE_VERSION)

    print("=== BASIC METADATA ===")
    print("ref            :", data.get("ref"))
    print("heTitle        :", data.get("heTitle"))
    print("sectionNames   :", data.get("sectionNames"))
    print("sections       :", data.get("sections"))
    print("versionTitle   :", data.get("versionTitle"))
    print("heVersionTitle :", data.get("heVersionTitle"))
    print("next           :", data.get("next"))
    print("prev           :", data.get("prev"))

    he_raw_list = data.get("he", [])

    # Some refs return a list of full lines; some weirdly come as a list of chars.
    if he_raw_list and all(isinstance(ch, str) and len(ch) == 1 for ch in he_raw_list):
        raw_hebrew = "".join(he_raw_list)
    elif isinstance(he_raw_list, list):
        # Fallback: join with spaces if they’re longer chunks
        raw_hebrew = " ".join(he_raw_list)
    elif isinstance(he_raw_list, str):
        raw_hebrew = he_raw_list
    else:
        raw_hebrew = ""

    print("\n=== RAW HEBREW (he) FROM API (repr) ===")
    print(repr(raw_hebrew))

    cleaned = clean_he_string(raw_hebrew)

    print("\n=== CLEANED HEBREW (no HTML, compact) ===")
    print(cleaned)


if __name__ == "__main__":
    test_texts_api()