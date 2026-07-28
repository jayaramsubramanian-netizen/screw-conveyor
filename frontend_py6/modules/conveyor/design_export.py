"""
modules/conveyor/design_export.py — copy a full design as JSON
═══════════════════════════════════════════════════════════════════════════
A design snapshot the user can copy to the clipboard (or save) and paste
back for review. Built to answer "why did the optimiser pick X" and "review
all my selections" without a screenshot round-trip: it captures the exact
inputs the engine saw, the results it returned, and the component picks, so
the whole state is reconstructable from one block of text.

This is intentionally separate from the design save/load feature (which
will be a richer, versioned, backend-migration-ready format). This is a
debug/review dump: flat, complete, human-readable, no schema promises.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


# The sidebar keys the optimiser holds FIXED while it varies D/N/P. Surfaced
# explicitly so a reviewer can see what baseline a geometry search inherited
# — a mismatch here is a prime suspect when the optimiser "won't converge"
# on a design the user found by hand.
_OPTIMIZER_FIXED_KEYS = [
    "shaft_mode", "shaft_type", "OD", "wall", "sallow", "supports",
    "brg", "gbx", "hangers", "bload", "duty",
]

# The three the optimiser is allowed to move in Phase 1.
_OPTIMIZER_VARIED_KEYS = ["D", "N", "P", "P_in", "P_out", "pct_in", "pct_out"]


def _pick(d: dict, keys: list[str]) -> dict:
    return {k: d.get(k) for k in keys}


def build_design_snapshot(payload: dict, results: dict) -> dict:
    """
    Assemble the full reviewable snapshot.

    Everything is plain JSON-serialisable. Results are included whole rather
    than summarised, because the point is to let a reviewer see exactly what
    the engine produced — a summary would hide the very field that explains
    an unexpected optimiser choice.
    """
    cap = (results or {}).get("cap", {}) or {}
    checks_pass = _summarise_checks(results)

    return {
        "_meta": {
            "kind": "vectrix_design_snapshot",
            "version": 1,
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": "Debug/review dump — inputs + results + component picks.",
        },
        "headline": {
            "capacity_req_tph": payload.get("cap"),
            "capacity_actual_tph": cap.get("Qt"),
            "meets_capacity": cap.get("ok"),
            "checks_passing": checks_pass,
        },
        "optimizer_view": {
            "varied_phase1": _pick(payload, _OPTIMIZER_VARIED_KEYS),
            "held_fixed": _pick(payload, _OPTIMIZER_FIXED_KEYS),
            "_hint": (
                "If a hand-found design beats the optimiser, compare "
                "held_fixed against that design's drive/shaft/hanger choices "
                "— Phase 1 only searches varied_phase1 and inherits the rest."
            ),
        },
        "inputs": dict(payload),
        "results": results or {},
    }


def _summarise_checks(results: dict) -> str:
    """A quick 'n of m passing' without re-deriving the full checks table."""
    if not results:
        return "no results"
    cap = (results.get("cap") or {})
    tor = (results.get("tor") or {})
    checks = [
        cap.get("ok"),
        tor.get("shOk"),
        results.get("deflection_ok"),
        (results.get("gbx_r") or {}).get("tOk"),
        (results.get("brg_r") or {}).get("ok"),
    ]
    known = [c for c in checks if c is not None]
    return f"{sum(1 for c in known if c)}/{len(known)} core checks"


def to_json(payload: dict, results: dict) -> str:
    """Pretty-printed JSON string, safe against non-serialisable values."""
    snap = build_design_snapshot(payload, results)

    def _default(o: Any) -> Any:
        # Engine occasionally returns numpy scalars etc.; coerce rather than
        # fail the whole export on one odd value.
        try:
            return float(o)
        except (TypeError, ValueError):
            return str(o)

    return json.dumps(snap, indent=2, default=_default)