# all_topics.py

import json
from pathlib import Path
import requests

BASE = "https://www.sefaria.org"

def get_all_topics():
    resp = requests.get(f"{BASE}/api/topics", timeout=30)
    resp.raise_for_status()
    return resp.json()

def simplify_topics(raw_topics):
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

        # primary titles
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

        # fallback: any titles
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

        simple.append({"slug": slug, "en": en_title, "he": he_title})

    return simple

def main():
    print("=== Fetching ALL topics from Sefaria ===")
    raw = get_all_topics()
    simple = simplify_topics(raw)

    print(f"Total raw topics:    {len(raw)}")
    print(f"Total simple topics: {len(simple)}")

    # Save for MM backend to use
    out_path = Path(__file__).parent / "topics_simple.json"
    out_path.write_text(json.dumps(simple, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote simplified topics to {out_path}")

if __name__ == "__main__":
    main()