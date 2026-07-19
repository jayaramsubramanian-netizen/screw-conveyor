"""
components/model_number.py — VECTOMEC™ model number generator
═══════════════════════════════════════════════════════════════════════════
Implements the schema from VECTOMEC_TODO.md §1.1:

    VM – [Series] – [Diameter mm] – [Length dm] – [Pitch code]
       – [Material code] – [Drive code]

    Example:  VM–VH–400–120–SP–HX–GM
      VM  = VECTOMEC (fixed brand prefix)
      VH  = Heavy Duty series
      400 = 400 mm diameter
      120 = 12.0 m length (decimetres)
      SP  = Standard Pitch
      HX  = Hardox trough
      GM  = Gearmotor drive

This is classification/formatting logic, not physics — it derives a
product code from values the engine has already computed. Reads only
the `result` dict every other panel already consumes; no payload or
extra backend call needed.

Pitch classification note: calc_engine() always computes mp["P_eff"]
as a blend of P_in/P/P_out regardless of the sidebar's use_multipitch
toggle, so the P_eff/D ratio alone is a sound, single-source-of-truth
signal for pitch character — no need to thread the raw payload flag
through the UI layer just for this.

Not yet backend-authoritative: if this needs to appear identically in
a future PDF report or a saved project record, it should eventually
move server-side so there's a single source of truth. Flagged here
rather than silently assumed.
"""

from __future__ import annotations

from typing import NamedTuple


# ── Series codes (VECTOMEC_TODO.md §1.1) ─────────────────────────────────
_SERIES_TABLE = {
    "VS": "Standard Duty",
    "VH": "Heavy Duty",
    "VM": "Mining Grade",
    "VF": "Food Grade",
    "VT": "Tubular",
    "VX": "Process (jacketed)",
    "VL": "Live Bottom Feeder",
}

# ── Material/trough codes, derived from result["cost"]["steel"] ──────────
_STEEL_CODE = {
    "Steel":            "CS",    # Carbon steel
    "Stainless 304":    "SS304",
    "Stainless 316":    "SS316",
    "WearLiner":        "WL",
    "Hardox 450":       "HX",
}
_STEEL_CODE_DEFAULT = "CS"


class ModelNumberBreakdown(NamedTuple):
    """Structured pieces, so a display widget can show a breakdown
    without re-deriving anything."""
    full_string:   str
    series_code:   str
    series_label:  str
    diameter_mm:   int
    length_dm:     int
    pitch_code:    str
    pitch_label:   str
    material_code: str
    drive_code:    str


def _classify_series(result: dict) -> str:
    """
    Series selection priority:
      1. Tubular (is_pipe) always wins — it's a distinct product line
         regardless of material abrasiveness.
      2. Material abrasion class / CEMA class → duty tier.
      3. Default to Standard Duty.

    Food Grade (VF), Process/jacketed (VX), and Live Bottom Feeder (VL)
    are not derivable from the conveyor calculator's inputs alone (no
    hygiene flag in the material DB, no process-module or feeder
    context here) — those require an explicit user selection, which
    isn't wired yet. Documented rather than guessed.
    """
    if bool(result.get("is_pipe", False)):
        return "VT"

    mat = result.get("mat", {}) or {}
    abr = mat.get("abr", "Medium")
    cls = mat.get("cls", "I")

    if abr in ("High", "Very High") or cls in ("III", "IV"):
        return "VM"
    if abr == "Medium" or cls == "II":
        return "VH"
    return "VS"


def _classify_pitch(result: dict) -> tuple[str, str]:
    """
    Returns (code, label), derived purely from the P_eff/D ratio that
    calc_engine() always computes — see module docstring for why this
    doesn't need the sidebar's use_multipitch flag threaded through.
    """
    D = result.get("D", 0.0) or 0.0
    P_eff = result.get("P_eff", D) or D
    ratio = (P_eff / D) if D > 0 else 1.0

    if ratio < 0.70:
        return "HP", "Half Pitch"
    if ratio > 1.10:
        return "LP", "Long Pitch"
    return "SP", "Standard Pitch"


def _classify_material(result: dict) -> str:
    steel = (result.get("cost", {}) or {}).get("steel", _STEEL_CODE_DEFAULT)
    return _STEEL_CODE.get(steel, _STEEL_CODE_DEFAULT)


def _classify_drive(result: dict) -> str:
    """
    Drive code. No VFD/soft-start field is wired into EngineInput yet
    (flagged as a gap in VECTOMEC_TODO.md §2.4), so this always
    resolves to Gearmotor for now — not silently wrong, just the only
    option currently modelled.
    """
    return "GM"


def generate_model_number(result: dict) -> ModelNumberBreakdown:
    """
    Build the full VECTOMEC™ model string plus a structured breakdown.

    Args:
        result   engine result dict (from fetch_design())

    Returns:
        ModelNumberBreakdown — full_string plus every component, so a
        UI widget can render "VM-VH-300-100-SP-CS-GM" as the headline
        and show each segment's meaning underneath.
    """
    series_code = _classify_series(result)
    series_label = _SERIES_TABLE.get(series_code, "Standard Duty")

    diameter_mm = round(float(result.get("D", 0.0)) * 1000)
    length_dm = round(float(result.get("L", 0.0)) * 10)

    pitch_code, pitch_label = _classify_pitch(result)
    material_code = _classify_material(result)
    drive_code = _classify_drive(result)

    full_string = (
        f"VM-{series_code}-{diameter_mm}-{length_dm}-"
        f"{pitch_code}-{material_code}-{drive_code}"
    )

    return ModelNumberBreakdown(
        full_string=full_string,
        series_code=series_code,
        series_label=series_label,
        diameter_mm=diameter_mm,
        length_dm=length_dm,
        pitch_code=pitch_code,
        pitch_label=pitch_label,
        material_code=material_code,
        drive_code=drive_code,
    )