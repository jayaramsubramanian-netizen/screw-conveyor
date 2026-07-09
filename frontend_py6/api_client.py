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

import requests

BASE_URL  = "http://127.0.0.1:8000"
TIMEOUT_S = 10          # seconds — same as bucket elevator


# ── internal helper ───────────────────────────────────────────────────────
def _post(endpoint: str, payload: dict) -> dict:
    try:
        resp = requests.post(
            f"{BASE_URL}{endpoint}",
            json=payload,
            timeout=TIMEOUT_S,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {
            "error": True,
            "message": (
                "Cannot reach backend at "
                f"{BASE_URL} — is the FastAPI server running?\n"
                "Run:  uvicorn backend.main:app --reload"
            ),
        }
    except requests.exceptions.Timeout:
        return {
            "error": True,
            "message": f"Backend request timed out after {TIMEOUT_S}s.",
        }
    except requests.exceptions.HTTPError as exc:
        return {
            "error": True,
            "message": f"Backend returned HTTP {exc.response.status_code}.",
        }
    except Exception as exc:
        return {"error": True, "message": str(exc)}


def _get(endpoint: str, params: dict = None) -> dict | list:
    try:
        resp = requests.get(
            f"{BASE_URL}{endpoint}",
            params=params,
            timeout=TIMEOUT_S,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {
            "error": True,
            "message": (
                "Cannot reach backend at "
                f"{BASE_URL} — is the FastAPI server running?"
            ),
        }
    except Exception as exc:
        return {"error": True, "message": str(exc)}


# ── public API ────────────────────────────────────────────────────────────

def fetch_design(payload: dict) -> dict:
    """
    Main conveyor calculation.

    Calls POST /api/calculate with the standard conveyor payload.
    The backend routes this to backend/core/engine.py → calc_engine().

    Expected payload keys (all optional — backend supplies defaults):
        mat         str     material name e.g. "Cement"
        D           float   trough diameter (m)
        L           float   conveyor length (m)
        N           float   speed (RPM)
        P           float   body pitch (m)
        P_in        float   inlet pitch (m)
        P_out       float   outlet pitch (m)
        pct_in      float   inlet pitch zone % of total length
        pct_out     float   outlet pitch zone % of total length
        ang         float   inclination angle (°)
        cap         float   required capacity (t/h)
        surge       float   surge factor (e.g. 1.2)
        type        str     "screw" | "pipe"
        shaft_mode  str     "auto" | "manual"
        shtype      str     "bar" | "pipe"   (manual mode only)
        pod         float   pipe OD (mm)     (manual mode only)
        pwall       float   pipe wall (mm)   (manual mode only)
        sallow      float   allowable shear stress (MPa)
        ft          float   flight thickness (m)
        wa          float   wear allowance (m)
        bload       float   bearing radial load (kN)
        brg         str     bearing model e.g. "UC210"
        gbx         str     gearbox model e.g. "GB-20k"
        hangers     int     hanger bearing count (0 = auto)
        temp_c      float   operating temperature (°C)

    Returns:
        On success — dict with keys matching backend schema (schemas.py):
            Qt, Qv, fill, Pe, Pm, Pi, Ps, Pt, motor,
            Tr, Ts, tau, tau_ok, shaft_od, shaft_id,
            shaft_sel_mm, shaft_sf,
            L10, brg_ok,
            wrate_mm_h, life_h, life_t,
            eff_score, kWh_t, cap_ok,
            checks: [{type, label, value, limit, ok}]
            …and all other fields from calcEngine()
        On error — {"error": True, "message": str}
    """
    return _post("/api/calculate", payload)


def fetch_process(module: str, payload: dict) -> dict:
    """
    Process module calculation (Mixer, Dryer, Cooler, Separator,
    Reactor, Compactor).

    Calls POST /api/calculate/process.
    The backend routes this to backend/core/process_engine.py.

    Args:
        module  str   "mixer"|"dryer"|"cooler"|"sep"|"reactor"|"compact"
        payload dict  module-specific input fields

    Returns dict with module results, or {"error": True, "message": str}.
    """
    return _post("/api/calculate/process", {"module": module, **payload})


def fetch_materials() -> list:
    """
    Fetch the full material list from the database.

    Calls GET /api/materials.
    Returns list of material dicts, or {"error": True, "message": str}.
    """
    return _get("/api/materials")


def save_project(meta: dict) -> dict:
    """
    Save project metadata to the backend database.

    Calls POST /api/projects with the ProjectMeta fields:
        project, tagNo, client, engineer,
        approved, rev, docNo, site, notes

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
    Used by ShellWindow on startup to show a status indicator.
    """
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=3)
        return resp.status_code < 500
    except Exception:
        return False