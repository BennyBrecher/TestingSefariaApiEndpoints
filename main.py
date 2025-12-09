# main.py            Run With: uvicorn main:app --reload      and look up http://127.0.0.1:8000/library/browser
# main.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


from tree_of_life import build_library_tree, build_flat_book_list

SEFARIA_BASE = "https://www.sefaria.org"

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Build library tree once at startup
LIBRARY_TREE = build_library_tree()
FLAT_BOOKS = build_flat_book_list(LIBRARY_TREE)


# ---------------- basic library endpoints ----------------

@app.get("/library/tree")
def get_library_tree():
    """
    Full normalized Sefaria library tree (categories + books).
    """
    return LIBRARY_TREE


@app.get("/library/book-structure/{title}")
async def get_book_structure(title: str):
    """
    Wraps Sefaria /api/v2/raw/index/{title}

    You will use this to build the inside-book box navigation.
    """
    url = f"{SEFARIA_BASE}/api/v2/raw/index/{title}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code,
                            detail=f"Failed to fetch book structure for {title}")
    return r.json()


import httpx
from fastapi import HTTPException

SEFARIA_BASE = "https://www.sefaria.org"

@app.get("/library/ref-info")
async def get_ref_info(ref: str):
    """
    Bundles deep-dive endpoints for a ref.

    - Always tries /api/v3/texts/{ref}
    - If that returns no he/en, falls back to legacy /api/texts/{ref}
    - links/topics/related are best-effort (timeouts ignored)
    """
    timeout = httpx.Timeout(10.0, connect=5.0, read=10.0)

    async with httpx.AsyncClient(base_url=SEFARIA_BASE, timeout=timeout) as client:
        # --- texts (required) ---
        texts_resp = await client.get(f"/api/v3/texts/{ref}")
        if texts_resp.status_code != 200:
            raise HTTPException(
                status_code=texts_resp.status_code,
                detail=f"Failed to fetch texts for ref {ref}",
            )
        texts = texts_resp.json() or {}
        he = texts.get("he")
        en = texts.get("en") or texts.get("text")

        # Fallback: legacy /api/texts if both are empty/None
        if (not he) and (not en):
            try:
                legacy_resp = await client.get(f"/api/texts/{ref}")
                if legacy_resp.status_code == 200:
                    legacy = legacy_resp.json() or {}
                    # legacy usually has arrays
                    he_legacy = legacy.get("he")
                    en_legacy = legacy.get("text") or legacy.get("en")
                    if he_legacy or en_legacy:
                        texts["he"] = he_legacy
                        texts["en"] = en_legacy
            except httpx.HTTPError:
                # ignore, keep original (empty) texts
                pass

        # --- optional helpers: tolerate timeouts/failures ---
        try:
            links_resp = await client.get(f"/api/links/{ref}")
            links = links_resp.json() if links_resp.status_code == 200 else []
        except httpx.HTTPError:
            links = []

        try:
            topics_resp = await client.get(f"/api/ref-topic-links/{ref}")
            topics = topics_resp.json() if topics_resp.status_code == 200 else []
        except httpx.HTTPError:
            topics = []

        try:
            related_resp = await client.get(f"/api/related/{ref}")
            related = related_resp.json() if related_resp.status_code == 200 else {}
        except httpx.HTTPError:
            related = {}

    return {
        "ref": ref,
        "texts": texts,
        "links": links,
        "topics": topics,
        "related": related,
    }


@app.get("/library/browser", response_class=HTMLResponse)
def library_browser(request: Request):
    """
    Sefaria-style box navigator page.
    """
    return templates.TemplateResponse("library_browser.html", {"request": request})