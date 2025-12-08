import requests
import json
import re
import html

BASE = "https://www.sefaria.org"


# ---------- utils ----------

def pretty(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# very forgiving HTML tag-stripper: <...>
TAG_RE = re.compile(r"<.*?>", flags=re.DOTALL)


def clean_he_string(raw: str) -> str:
    """
    Clean a single Hebrew (or English) string from Sefaria:
      - decode HTML entities (&thinsp;, &nbsp;, etc.)
      - strip HTML tags (<big>, <span>, etc.)
      - normalize whitespace
    """
    s = html.unescape(raw)
    s = TAG_RE.sub("", s)
    s = s.replace("\u00a0", " ")  # NBSP → space
    s = " ".join(s.split())
    return s


# ---------- Sefaria API wrappers (texts, links, topics) ----------

def get_text(ref: str, lang: str = "he", context: int = 0, version: str | None = None):
    """
    Wrapper around /api/texts/{ref}
    """
    ref_url = ref.replace(" ", "_")
    url = f"{BASE}/api/texts/{ref_url}"

    params = {
        "lang": lang,
        "commentary": 0,
        "context": context,
    }
    if version:
        params["version"] = version

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_links(ref: str):
    """
    Wrapper around /api/links/{ref}
    """
    ref_url = ref.replace(" ", "_")
    url = f"{BASE}/api/links/{ref_url}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_ref_topics(ref: str):
    """
    Wrapper around /api/ref-topic-links/{ref}
    """
    ref_url = ref.replace(" ", "_")
    url = f"{BASE}/api/ref-topic-links/{ref_url}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------- link simplification ----------

def simplify_link(link: dict, anchor_ref: str) -> dict:
    """
    Turn a raw link entry into a small, MM-friendly object.
    """
    category = link.get("category", "Unknown")
    link_type = link.get("type", "")

    anchor = link.get("anchorRef") or anchor_ref
    refs = link.get("refs") or []

    # Try to find the "other side" of the link (the thing commenting / related to anchor)
    source_ref = link.get("sourceRef")
    if not source_ref:
        candidates = [r for r in refs if r != anchor]
        if candidates:
            source_ref = candidates[0]
        elif refs:
            source_ref = refs[0]
        else:
            source_ref = anchor

    return {
        "category": category,
        "type": link_type,
        "sourceRef": source_ref,
        "anchorRef": anchor,
    }


def build_related_by_category(links: list[dict], anchor_ref: str, max_per_cat: int = 5) -> dict:
    """
    Group simplified links by category, truncating each category to max_per_cat.
    """
    grouped: dict[str, list[dict]] = {}

    for raw in links:
        simplified = simplify_link(raw, anchor_ref)
        cat = simplified["category"]

        if cat not in grouped:
            grouped[cat] = []

        # enforce per-category cap
        if len(grouped[cat]) < max_per_cat:
            grouped[cat].append(simplified)

    return grouped


# ---------- topic simplification (endpoint 5) ----------

BLACKLISTED_TOPIC_IDS = {"ai"}


def extract_topic_slugs(raw_topics) -> list[str]:
    """
    Normalize the ref-topic response to a flat list of topic ids (slugs).
    Filters out obviously useless tags like 'ai'.
    """
    slugs: list[str] = []

    if not isinstance(raw_topics, list):
        return slugs

    for item in raw_topics:
        if not isinstance(item, dict):
            continue
        topic_id = item.get("topic")
        if not isinstance(topic_id, str):
            continue
        if topic_id in BLACKLISTED_TOPIC_IDS:
            continue
        slugs.append(topic_id)

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

      { "id": "creation-of-heavens-and-earth",
        "title": "In the Beginning",
        "source": "learning-team" }
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
        if topic_id in BLACKLISTED_TOPIC_IDS:
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
        tid = t.get("id")
        if tid not in seen:
            seen.add(tid)
            uniq.append(t)

    return uniq


# ---------- main "ref summary" builder ----------

def build_ref_summary(
    ref: str,
    lang: str = "he",
    context: int = 0,
    version: str | None = None,
    max_links_per_category: int = 5,
) -> dict:
    """
    High-level helper for MM:

    Given a canonical ref (e.g. "Genesis 1:1" or "Berakhot 2a"),
    return a compact JSON blob with:

      - metadata (titles, version info, next/prev, etc.)
      - cleaned text lines
      - related sources grouped by category
      - topic ids + topic objects (for tagging / filtering)
    """
    text_data = get_text(ref, lang=lang, context=context, version=version)
    links_data = get_links(ref)
    topics_raw = get_ref_topics(ref)

    # ---- title handling (Sefaria sometimes omits "title") ----
    title = (
        text_data.get("title")
        or text_data.get("book")
        or text_data.get("indexTitle")
        or (ref.split()[0] if ref else None)
    )

    # ---- choose the right text field ----
    if lang == "he":
        raw_lines = text_data.get("he", [])
    else:
        # Sefaria uses "text" for non-Hebrew
        raw_lines = text_data.get("text", [])

    # Normalize to list of strings
    if isinstance(raw_lines, str):
        raw_lines = [raw_lines]
    elif not isinstance(raw_lines, list):
        raw_lines = []

    # Clean lines (works for HE + EN)
    cleaned_lines = [clean_he_string(line) for line in raw_lines if line]

    related_by_cat = build_related_by_category(
        links_data,
        anchor_ref=text_data.get("ref", ref),
        max_per_cat=max_links_per_category,
    )

    topic_ids = extract_topic_slugs(topics_raw)
    topic_objs = extract_topic_objects(topics_raw)

    summary = {
        "ref": text_data.get("ref", ref),
        "title": title,
        "heTitle": text_data.get("heTitle"),
        "sectionNames": text_data.get("sectionNames"),
        "sections": text_data.get("sections"),
        "versionTitle": text_data.get("versionTitle"),
        "heVersionTitle": text_data.get("heVersionTitle"),
        "next": text_data.get("next"),
        "prev": text_data.get("prev"),
        "text": {
            "lang": lang,
            "raw": raw_lines,
            "cleaned": cleaned_lines,
        },
        "relatedSourcesByCategory": related_by_cat,
        "topics": {
            "ids": topic_ids,
            "objects": topic_objs,
        },
    }

    return summary


# ---------- quick CLI test ----------

if __name__ == "__main__":
    test_ref = "Genesis 1:1"
    print(f"=== Building ref summary for: {test_ref} ===")
    ref_summary = build_ref_summary(test_ref, lang="en", context=0)
    pretty(ref_summary)