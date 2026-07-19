"""
api_client.py — VECTRIX™ Screw Conveyor HTTP client
═══════════════════════════════════════════════════════════════════════════
Single module that owns every network call from the PySide6 frontend to
the FastAPI backend.  Mirrors the bucket-elevator fetch_design() pattern
exactly — one synchronous requests.post() per calculation, returns a plain
dict, never raises into the UI layer.

Backend base URL: http://127.0.0.1:8000
Router mount:      app.include_router(router, prefix="/api/v1")   [backend/main.py]

Confirmed routes (from backend/api/routes.py):
    POST /api/v1/calculate            → main conveyor calc     (core/engine.py)
    POST /api/v1/axial-profile        → axial profile segments (core/axial.py)
    POST /api/v1/family               → family designer sweep
    POST /api/v1/calculate-multi      → CEMA/DIN/Custom side-by-side
    GET  /api/v1/materials            → material list
    GET  /api/v1/materials/{name}     → single material
    GET  /api/v1/bearings             → bearing list
    GET  /api/v1/gearboxes            → gearbox list
    GET  /api/v1/motors               → motor list
    GET  /api/v1/drives                → drive list
    GET  /api/v1/costs                → cost item list
    POST /api/v1/process/{module}     → process module calc
         module ∈ {mixer, dryer, cooler, separator, reactor, compactor, feeder}
         NOTE: exact spelling — "separator" and "compactor" in full,
         not "sep"/"compact". Payload is posted as-is (no wrapper key).
    GET  /                            → root health ping (unprefixed)

NOT YET MOUNTED:
    backend/api/project_meta.py exists per the project file tree but its
    router is not included in backend/main.py's app.include_router() calls.
    save_project()/load_project() below will 404 until that router is
    wired in — flagging here rather than guessing its shape.

All functions return a plain dict on success.
On connection error / timeout / non-200 they return an error dict:
    {"error": True, "message": "<human-readable>"}
so the UI can display a status message without crashing.
"""

from __future__ import annotations

from typing import Optional
import requests

BASE_URL   = "http://127.0.0.1:8000"
API_PREFIX = "/api/v1"
TIMEOUT_S  = 10          # seconds — same as bucket elevator

# Process module id → route segment.
# Kept as an explicit map (not identity passthrough) so a future rename
# of either the frontend page id or the backend route segment doesn't
# silently break the other side.
_PROCESS_ROUTES = {
    "mixer":     "mixer",
    "dryer":     "dryer",
    "cooler":    "cooler",
    "separator": "separator",
    "reactor":   "reactor",
    "compactor": "compactor",
    "feeder":    "feeder",
}


# ── internal helpers ──────────────────────────────────────────────────────

def _post(endpoint: str, payload: dict) -> dict:
    try:
        resp = requests.post(
            f"{BASE_URL}{endpoint}",
            json=payload,
            timeout=TIMEOUT_S,
        )
        resp.raise_for_status()
        return resp.json()                          # type: ignore[no-any-return]
    except requests.exceptions.ConnectionError:
        return {
            "error": True,
            "message": (
                f"Cannot reach backend at {BASE_URL} — "
                "is the FastAPI server running?\n"
                "Run:  uvicorn backend.main:app --reload"
            ),
        }
    except requests.exceptions.Timeout:
        return {
            "error": True,
            "message": f"Backend request timed out after {TIMEOUT_S}s.",
        }
    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "?"
        body = ""
        try:
            if exc.response is not None:
                body = exc.response.text[:300]
        except Exception:
            pass
        return {
            "error": True,
            "message": f"Backend returned HTTP {code}. {body}".strip(),
        }
    except Exception as exc:
        return {"error": True, "message": str(exc)}


def _get(endpoint: str, params: Optional[dict] = None) -> dict:
    """
    Always returns a dict — either the parsed JSON response (which may
    itself be a list wrapped under a key) or an error dict.
    If the backend returns a bare JSON array we wrap it as
    {"items": [...]} so callers always receive a dict.
    """
    try:
        resp = requests.get(
            f"{BASE_URL}{endpoint}",
            params=params,
            timeout=TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return {"items": data}
        return data                                 # type: ignore[no-any-return]
    except requests.exceptions.ConnectionError:
        return {
            "error": True,
            "message": (
                f"Cannot reach backend at {BASE_URL} — "
                "is the FastAPI server running?"
            ),
        }
    except Exception as exc:
        return {"error": True, "message": str(exc)}


# ── public API ────────────────────────────────────────────────────────────

def fetch_design(payload: dict) -> dict:
    """
    Main conveyor calculation.

    Calls POST /api/v1/calculate → backend/core/engine.py → calc_engine().

    Expected payload keys (all optional — backend supplies defaults):
        mat, D, L, N, P, P_in, P_out, pct_in, pct_out,
        ang, cap, surge, type, shaft_mode, shtype, pod, pwall,
        sallow, ft, wa, bload, brg, gbx, hangers, temp_c, lam_factor,
        support_cond, contAFact, use_multipitch, use_fill_coupling, duty

    Returns dict with backend schema keys on success, or error dict.
    """
    return _post(f"{API_PREFIX}/calculate", payload)


def fetch_process(module: str, payload: dict) -> dict:
    """
    Process module calculation.

    Calls POST /api/v1/process/{module} → backend/core/process_engine.py.
    The payload is posted exactly as given — each route handler
    (run_mixer, run_dryer, ...) accepts a raw dict, not a wrapped one.

    Args:
        module  one of "mixer","dryer","cooler","separator",
                "reactor","compactor","feeder"
        payload module-specific input fields

    Returns dict with module results, or error dict if the module name
    is not recognised or the request fails.
    """
    route = _PROCESS_ROUTES.get(module)
    if route is None:
        return {
            "error": True,
            "message": (
                f"Unknown process module '{module}'. "
                f"Expected one of: {', '.join(_PROCESS_ROUTES)}"
            ),
        }
    return _post(f"{API_PREFIX}/process/{route}", payload)


def fetch_axial_profile(payload: dict) -> dict:
    """
    Axial profile segments (fill%, torque, wear along conveyor length).

    Calls POST /api/v1/axial-profile.
    payload shape: {"inp": <EngineInput fields>, "segments": <int, 10-200>}

    Returns {"segments": [...]} on success, or error dict.
    """
    return _post(f"{API_PREFIX}/axial-profile", payload)


def fetch_family(payload: dict) -> dict:
    """
    Family designer sweep (D × L × N combinations).

    Calls POST /api/v1/family.
    Returns {"pts": [...]} on success, or error dict.
    """
    return _post(f"{API_PREFIX}/family", payload)


def fetch_calculate_multi(payload: dict) -> dict:
    """
    CEMA / DIN / Custom standards comparison in one call.

    Calls POST /api/v1/calculate-multi.
    Returns {"CEMA": {...}, "DIN": {...}, "Custom": {...}} or error dict.
    """
    return _post(f"{API_PREFIX}/calculate-multi", payload)


def fetch_materials() -> dict:
    """
    Fetch the full material list.

    Calls GET /api/v1/materials.
    Returns {"items": [...]} on success, or error dict.
    Callers access the list via result.get("items", []).
    """
    return _get(f"{API_PREFIX}/materials")


def fetch_bearings() -> dict:
    """Calls GET /api/v1/bearings. Returns {"items": [...]} or error dict."""
    return _get(f"{API_PREFIX}/bearings")


def fetch_gearboxes() -> dict:
    """Calls GET /api/v1/gearboxes. Returns {"items": [...]} or error dict."""
    return _get(f"{API_PREFIX}/gearboxes")


def fetch_motors() -> dict:
    """Calls GET /api/v1/motors. Returns {"items": [...]} or error dict."""
    return _get(f"{API_PREFIX}/motors")


def fetch_drives() -> dict:
    """Calls GET /api/v1/drives. Returns {"items": [...]} or error dict."""
    return _get(f"{API_PREFIX}/drives")


def fetch_costs() -> dict:
    """Calls GET /api/v1/costs. Returns {"items": [...]} or error dict."""
    return _get(f"{API_PREFIX}/costs")


def save_project(meta: dict) -> dict:
    """
    Save project metadata.

    NOT YET MOUNTED on the backend — api/project_meta.py exists per the
    project file tree but its router is not included in backend/main.py.
    Calling this today will return a connection-level 404 error dict.
    Kept here so the frontend call site doesn't need to change once the
    backend route is wired in.
    """
    return _post(f"{API_PREFIX}/projects", meta)


def load_project(project_id: int) -> dict:
    """
    Load a saved project by id.

    NOT YET MOUNTED — see save_project() note above.
    """
    return _get(f"{API_PREFIX}/projects/{project_id}")


def health_check() -> bool:
    """
    Returns True if the backend is reachable, False otherwise.
    Calls GET / — the unprefixed root route in backend/main.py.
    Used by ShellWindow on startup to show the status dot colour.
    """
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=3)
        return resp.status_code < 500
    except Exception:
        return False