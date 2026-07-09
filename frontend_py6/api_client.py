"""
api_client.py — VECTRIX™ Screw Conveyor HTTP client
═══════════════════════════════════════════════════════════════════════════
Single module that owns every network call from the PySide6 frontend to
the FastAPI backend.  Mirrors the bucket-elevator fetch_design() pattern
exactly — one synchronous requests.post() per calculation, returns a plain
dict, never raises into the UI layer.

Backend base URL: http://127.0.0.1:8000
Routes (from backend/api/routes.py):
    POST /api/calculate         → main conveyor calc  (engine.py)
    POST /api/calculate/process → process module calc  (process_engine.py)
    GET  /api/materials         → material list        (database.py)
    POST /api/projects          → save project meta    (project_meta.py)
    GET  /api/projects/{id}     → load project meta    (project_meta.py)

All functions return a plain dict on success.
On connection error / timeout / non-200 they return an error dict:
    {"error": True, "message": "<human-readable>"}
so the UI can display a status message without crashing.
"""

from __future__ import annotations

from typing import Optional
import requests

BASE_URL  = "http://127.0.0.1:8000"
TIMEOUT_S = 10          # seconds — same as bucket elevator


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
        # exc.response may be None for manually-raised HTTPError; guard it.
        code = exc.response.status_code if exc.response is not None else "?"
        return {
            "error": True,
            "message": f"Backend returned HTTP {code}.",
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

    Calls POST /api/calculate → backend/core/engine.py → calc_engine().

    Expected payload keys (all optional — backend supplies defaults):
        mat, D, L, N, P, P_in, P_out, pct_in, pct_out,
        ang, cap, surge, type, shaft_mode, shtype, pod, pwall,
        sallow, ft, wa, bload, brg, gbx, hangers, temp_c

    Returns dict with backend schema keys on success, or error dict.
    """
    return _post("/api/calculate", payload)


def fetch_process(module: str, payload: dict) -> dict:
    """
    Process module calculation.

    Calls POST /api/calculate/process → backend/core/process_engine.py.

    Args:
        module  "mixer"|"dryer"|"cooler"|"sep"|"reactor"|"compact"
        payload module-specific input fields

    Returns dict with module results, or error dict.
    """
    return _post("/api/calculate/process", {"module": module, **payload})


def fetch_materials() -> dict:
    """
    Fetch the full material list.

    Calls GET /api/materials → backend/db/database.py.
    Returns {"items": [...]} on success, or error dict.
    Callers access the list via result.get("items", []).
    """
    return _get("/api/materials")


def save_project(meta: dict) -> dict:
    """
    Save project metadata.

    Calls POST /api/projects → backend/api/project_meta.py.
    Returns saved record with generated id, or error dict.
    """
    return _post("/api/projects", meta)


def load_project(project_id: int) -> dict:
    """
    Load a saved project by id.

    Calls GET /api/projects/{project_id}.
    Returns project dict or error dict.
    """
    return _get(f"/api/projects/{project_id}")


def health_check() -> bool:
    """
    Returns True if the backend is reachable, False otherwise.
    Used by ShellWindow on startup to show the status dot colour.
    """
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=3)
        return resp.status_code < 500
    except Exception:
        return False