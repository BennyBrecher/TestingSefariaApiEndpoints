import time
import json
import requests

# Base URL for all Sefaria API calls
BASE = "https://www.sefaria.org"


def pretty(obj):
    """Helper: pretty-print JSON with UTF-8 Hebrew support."""
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def fetch_async_result(task_id: str, poll_interval=1, max_attempts=15):
    """
    Given a task_id returned from POST /api/find-refs,
    poll Sefaria's async endpoint until the job is done.

    Flow:
      1) POST /api/find-refs  ->  {"task_id": "..."}
      2) GET  /api/async/{task_id} repeatedly until:
           state == "SUCCESS" and result is present.

    If the task fails or times out, we raise an error.
    """
    url = f"{BASE}/api/async/{task_id}"

    for attempt in range(1, max_attempts + 1):
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        state = data.get("state")
        ready = data.get("ready")
        print(f"Attempt {attempt}: state={state}, ready={ready}")

        # SUCCESS: the final linker result lives under data["result"]
        if state == "SUCCESS" and data.get("result"):
            return data["result"]

        # HARD FAILURE: no point retrying
        if state in ("FAILURE", "REVOKED"):
            raise RuntimeError(f"Async task failed: {data}")

        # Otherwise (PENDING, STARTED, etc.) → wait and try again
        time.sleep(poll_interval)

    # If we exhaust all attempts, treat it as an error
    raise RuntimeError(f"Timed out waiting for async result for task_id={task_id}")


def find_explicit_refs(text: str, poll_interval=1, max_attempts=15):
    """
    High-level helper for MarehMakom.

    Input:
        text: OCR text of the sheet (Hebrew, possibly with citations).

    Output:
        List of dicts, each describing a citation candidate:

            {
                "raw": str,         # substring found in the text
                "ref": str|None,    # canonical Sefaria ref if resolved
                "start": int,       # start char index in `text`
                "end": int,         # end char index in `text`
                "status": "resolved" or "unresolved"
            }

    This abstracts away:
      - async task creation (/api/find-refs)
      - polling (/api/async/{task_id})
      - handling of linkFailed / null refs.
    """
    # 1) Kick off async job: POST /api/find-refs
    url = f"{BASE}/api/find-refs"
    payload = {
        "text": {
            "title": "",   # we ignore title for now
            "body": text
        }
    }
    params = {
        "with_text": 0,   # no need for full Torah text here, just spans + refs
        "debug": 0,
        "max_segments": 0
    }

    resp = requests.post(url, json=payload, params=params, timeout=30)
    resp.raise_for_status()
    initial = resp.json()

    task_id = initial.get("task_id")
    if not task_id:
        raise RuntimeError(f"Unexpected /api/find-refs response: {initial}")

    # 2) Poll async endpoint: GET /api/async/{task_id}
    result = fetch_async_result(task_id, poll_interval=poll_interval, max_attempts=max_attempts)

    # 3) Extract citation candidates from the "body" section
    output = []
    body = result.get("body", {})
    for r in body.get("results", []):
        raw_text = r.get("text")          # substring that looks like a ref
        start = r.get("startChar")        # char index in the original text
        end = r.get("endChar")
        link_failed = r.get("linkFailed")
        refs = r.get("refs") or []        # None → [] for iteration safety

        if refs:
            # One snippet can theoretically resolve to multiple refs
            for tref in refs:
                output.append({
                    "raw": raw_text,
                    "ref": tref,
                    "start": start,
                    "end": end,
                    "status": "resolved"
                })
        else:
            # Sefaria saw a citation-like pattern but could not resolve it
            output.append({
                "raw": raw_text,
                "ref": None,
                "start": start,
                "end": end,
                "status": "unresolved"
            })

    return output


def test_find_refs():
    sample_text = (
        'כתוב בבראשית א:א "בראשית ברא אלקים את השמים ואת הארץ". '
        'ובתהלים כג:א "מזמור לדוד ה׳ רועי לא אחסר". '
        'וכן נחלקו בזה הרמב"ם בהלכות תשובה ב:א והרמב"ן.'
    )

    results = find_explicit_refs(sample_text)

    print("=== EXPLICIT REF RESULTS ===")
    for r in results:
        print(
            f"{r['status'].upper():10} | "
            f"{r['raw']!r:30} | "
            f"{r['ref']} | "
            f"chars {r['start']}-{r['end']}"
        )


if __name__ == "__main__":
    test_find_refs()