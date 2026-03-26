"""
Shared calculation utilities for screw conveyor design.
All SI units (m, kg, kW, Nm, MPa) unless noted.
"""
import math
from typing import Tuple, List, Dict

MOTOR_EFFICIENCY = 0.90
STEEL_DENSITY    = 7850.0
G                = 9.81

# ─── Geometry ────────────────────────────────────────────────────────────────

def volumetric_capacity(D: float, pitch: float, N: float, fill: float) -> float:
    return (math.pi / 4.0) * D**2 * pitch * N * fill * 60.0

def shaft_diameter_estimate(D_screw: float) -> float:
    """Solid bar shaft — 20% of screw diameter (CEMA rule of thumb)."""
    return max(0.03, D_screw * 0.20)

def shaft_section_modulus(shaft_type: str, trough_d_m: float,
                           pipe_od_mm: float = 80.0, pipe_wall_mm: float = 8.0):
    """
    Returns (Wt_m3, od_mm, id_mm, is_pipe)
    Wt_m3 = torsional section modulus [m³]
    """
    if shaft_type == "pipe" and pipe_od_mm > 0:
        ro = pipe_od_mm / 2000.0
        ri = max(0.0, (pipe_od_mm / 2.0 - pipe_wall_mm)) / 1000.0
        Wt = (math.pi * (ro**4 - ri**4)) / (2.0 * ro) if ro > 0 else 1e-12
        od_mm = pipe_od_mm
        id_mm = pipe_od_mm - 2.0 * pipe_wall_mm
        return Wt, od_mm, id_mm, True
    else:
        d = shaft_diameter_estimate(trough_d_m)
        Wt = math.pi * d**3 / 16.0
        return Wt, d * 1000.0, 0.0, False

# ─── Power ────────────────────────────────────────────────────────────────────

def power_incline(Q_t_h: float, L: float, angle_deg: float) -> float:
    sin_a = math.sin(math.radians(angle_deg))
    return Q_t_h * G * L * sin_a / 3600.0

def power_empty_friction(D: float, L: float, N: float,
                          hanger_count: int, Ce: float = 0.06) -> float:
    base = Ce * N * math.sqrt(D) * L / 1000.0
    return base * (1.0 + 0.05 * hanger_count)

# ─── Torque & stress ──────────────────────────────────────────────────────────

def shaft_torque(P_kW: float, N: float) -> float:
    if N <= 0:
        return 0.0
    return P_kW * 9550.0 / N

def shaft_shear_stress_from_Wt(T_Nm: float, Wt_m3: float) -> float:
    """τ = T / Wt  [MPa]"""
    if Wt_m3 <= 0:
        return 0.0
    return T_Nm / Wt_m3 / 1e6

# ─── Bearing ─────────────────────────────────────────────────────────────────

def bearing_L10(C_kN: float, P_kN: float, p: float, N: float) -> Tuple[float, float]:
    if P_kN <= 0 or N <= 0:
        return (1e6, 1e6)
    ratio = C_kN / P_kN
    L10_mr = ratio ** p
    L10_h  = L10_mr * 1e6 / (60.0 * N)
    return (L10_h, L10_mr)

# ─── Wear ────────────────────────────────────────────────────────────────────

def wear_life(flight_thickness: float, wear_allowance: float,
              wear_coeff: float, N: float, Q_t_h: float) -> Tuple[float, float]:
    usable = max(1e-6, flight_thickness - wear_allowance)
    wear_rate = wear_coeff * (N / 6000.0)
    if wear_rate <= 0:
        return (1e6, 1e6)
    hours = (usable * 1000.0) / wear_rate
    tons  = hours * Q_t_h
    return (hours, tons)

# ─── Cost ────────────────────────────────────────────────────────────────────

def steel_mass(D: float, L: float, flight_thickness: float, pitch: float) -> float:
    n_turns = L / pitch if pitch > 0 else 0
    d_shaft = shaft_diameter_estimate(D)
    flight_area = n_turns * (math.pi / 4.0) * (D**2 - d_shaft**2)
    flight_mass = flight_area * flight_thickness * STEEL_DENSITY
    t_trough    = 0.004
    trough_mass = math.pi * D * L * 0.75 * t_trough * STEEL_DENSITY
    return flight_mass + trough_mass

def angle_capacity_factor(angle_deg: float) -> float:
    a = abs(angle_deg)
    if   a <= 5:  return 1.00
    elif a <= 10: return 0.90
    elif a <= 15: return 0.80
    elif a <= 20: return 0.70
    elif a <= 25: return 0.60
    else:         return 0.50

def next_standard_motor(P_kW: float, sizes: List[float]) -> float:
    for s in sorted(sizes):
        if s >= P_kW:
            return s
    return sizes[-1]

# ─── Efficiency ───────────────────────────────────────────────────────────────

def calc_efficiency(Qt_achieved: float, Qt_required: float,
                    Pt_kW: float, fill_pct: float) -> Dict:
    cap_util = min(100.0, (Qt_required / max(Qt_achieved, 0.001)) * 100.0)
    kWh_t    = Pt_kW / max(Qt_achieved, 0.001)
    energy_score = 40 if kWh_t < 1 else 25 if kWh_t < 3 else 10
    score = min(100, round(fill_pct * 0.6 + energy_score))
    return {
        "cap_util_pct": round(cap_util, 1),
        "kWh_per_tonne": round(kWh_t, 4),
        "fill_fraction_pct": round(fill_pct, 1),
        "design_score": score,
    }

# ─── Material Recommendations ────────────────────────────────────────────────

def get_material_recs(mat: dict) -> Dict:
    w     = mat.get("wear_coeff", 1.0)
    abr   = mat.get("abrasive", "Low")
    rho   = mat.get("bulk_density", 1.0)
    moist = mat.get("moisture_pct", 0.0)
    psz   = mat.get("particle_size_mm", 5.0)

    trough, flight, shaft, treatments, notes = [], [], [], [], []

    # Trough
    if abr == "Very High" or w >= 4:
        trough.append("Hardox 450 or Creusabro 4800 (≥12 mm)")
        trough.append("Full ceramic tile lining (Al₂O₃ 92%) for wet abrasives")
    elif abr == "High" or w >= 2:
        trough.append("Hardox 400 / AR400 wear-resistant plate (8–10 mm)")
        trough.append("Replaceable wear liners on lower section")
    elif abr == "Medium":
        trough.append("Carbon steel S355 / ASTM A572 (6–8 mm)")
        if moist > 15:
            trough.append("304L stainless or epoxy lining for moisture protection")
    else:
        trough.append("Stainless 304L (3 mm) — food/hygiene grade" if moist > 5 else "Carbon steel S235 (4–6 mm)")
    if rho > 2.0:
        trough.append("Increase trough gauge +2 mm for high-density material loading")

    # Flight
    if abr == "Very High" or w >= 4:
        flight.append("Chromium carbide overlay (CCO) plate — 6+6 mm")
        flight.append("Tungsten carbide hard-face weld on outer 30% of flight OD")
    elif abr == "High" or w >= 2:
        flight.append("Hardox 400 flights — 8–10 mm thick")
        flight.append("Hard-band flight edge with Stoody or Lincoln ChromeCarbide")
    elif abr == "Medium":
        flight.append("Carbon steel S355 — 6–8 mm; EN14700-T Fe16 hard-face option")
        flight.append("Flame hardening of flight OD to 50–55 HRC")
    else:
        flight.append("Carbon steel S235 or 304L stainless (food grade)")

    # Shaft
    if w >= 3 or abr in ("High", "Very High"):
        shaft.append("Solid bar EN10083 42CrMo4 (quench & temper) — preferred for high abrasion")
        shaft.append("Pipe option: Schedule 80 gives same section modulus at lower weight")
        shaft.append("Hard-chrome plating at seal and bearing journal locations")
    else:
        shaft.append("Solid bar S355 / AISI 1045 — standard duty")
        shaft.append("Hollow pipe EN10210 S355J2H viable — reduces inertia for light/medium duty")

    # Surface treatments
    if abr in ("High", "Very High"):
        treatments.append("Hard-banding: submerged arc weld Stellite 6 or ChromoCarbide on flight OD")
        treatments.append("HVOF WC-Co thermal spray on shaft bearing journals")
        if w >= 3.5:
            treatments.append("Ceramic tile (SiC or B₄C) on inlet chute impact zones")
    if abr == "Medium" or w >= 1.5:
        treatments.append("Flame hardening of lower trough — target 48–52 HRC")
        treatments.append("Induction hardening of flight edges for cost-effective life extension")
    if moist > 20:
        treatments.append("Hot-dip galvanise trough or 2-pack epoxy primer + polyurethane topcoat")
    if moist < 2 and abr == "Low":
        treatments.append("Powder-coat trough interior for corrosion protection")

    # Notes
    if rho > 1.8:
        notes.append(f"High bulk density ({rho} t/m³) — verify hanger bearing spacing (≤3 m recommended)")
    if psz > 20:
        notes.append(f"Coarse particles ({psz} mm) — consider half-pitch inlet and bolt-on wear shoes")
    if moist > 30:
        notes.append("Very high moisture — risk of build-up; evaluate paddle flights with scrapers")

    return {
        "trough": trough,
        "flight": flight,
        "shaft":  shaft,
        "treatments": treatments,
        "notes": notes,
    }
