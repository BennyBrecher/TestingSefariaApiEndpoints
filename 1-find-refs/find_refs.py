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

    The flow is:
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


def test_find_refs():
    """
    Demo of Sefaria's /api/find-refs endpoint.

    1) Sends a Hebrew sentence that contains a Rambam / Hilchot Teshuva-like citation.
    2) Receives a task_id (async job).
    3) Polls /api/async/{task_id} until the linker returns a result.
    4) Prints out each detected citation candidate:
         - If refs is a list → resolved to canonical Sefaria ref.
         - If refs is null and linkFailed=True → unresolved candidate.
    """
    url = f"{BASE}/api/find-refs"

    # Test input: Hebrew text with something that looks like a Rambam citation
    body_text = 'כמו שכתב הרמב"ם בהלכות תשובה ב:א על ענין התשובה...'

    payload = {
        "text": {
            # "title" is for matching references in the sheet title; we leave it empty here
            "title": "",
            # "body" is the main OCR text we want to scan for refs
            "body": body_text
        }
    }

    # Extra controls for the linker job
    params = {
        "with_text": 0,   # 0 = don't return actual verse/halacha text; only spans + refs
        "debug": 0,
        "max_segments": 0 # 0 = no limit on how many segments can be processed
    }

    # 1) Kick off async job: POST /api/find-refs
    resp = requests.post(url, json=payload, params=params, timeout=30)
    resp.raise_for_status()
    initial = resp.json()

    print("=== RAW INITIAL RESPONSE ===")
    pretty(initial)

    task_id = initial.get("task_id")
    if not task_id:
        # If this ever happens, Sefaria changed its behavior or we hit an error page
        print("No task_id in response, unexpected shape:")
        return

    print(f"\nGot task_id={task_id}, polling /api/async/{task_id}...\n")

    # 2) Poll async endpoint: GET /api/async/{task_id}
    result = fetch_async_result(task_id)

    print("\n=== FINAL RESULT (result object) ===")
    pretty(result)

    # 3) Simplify "body" results: this is where actual citation candidates live
    print("\n=== SIMPLIFIED RESULTS (body) ===")
    body = result.get("body", {})
    for r in body.get("results", []):
        text_snippet = r.get("text")          # the substring that looks like a ref
        start = r.get("startChar")            # char index in the original body text
        end = r.get("endChar")
        link_failed = r.get("linkFailed")     # True if Sefaria could NOT resolve the ref
        refs = r.get("refs") or []            # None → [] so we can iterate safely

        # If refs is empty/None: Sefaria saw a citation-like pattern but couldn't link it
        if not refs:
            print(
                f"UNRESOLVED candidate: '{text_snippet}' "
                f"(chars {start}-{end}, linkFailed={link_failed})"
            )
            # In MarehMakom, this is where you might:
            #   - store this for manual review, or
            #   - fall back to /api/search-wrapper on text_snippet.
            continue

        # If refs is a non-empty list: it resolved to one or more canonical refs
        for ref in refs:
            print(
                f"snippet='{text_snippet}' "
                f"chars {start}-{end} "
                f"→ ref={ref}"
            )
            # In MarehMakom, you'd persist:
            #   - sheet_id
            #   - raw snippet text
            #   - canonical ref
            #   - start/end spans


if __name__ == "__main__":
    test_find_refs()