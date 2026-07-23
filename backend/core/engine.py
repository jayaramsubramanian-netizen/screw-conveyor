"""
screw_conveyor_engine.py
========================
Core physics engine — Python translation of the JS calcEngine.
All formulas are identical to the validated JS version.
Inputs:  EngineInput (Pydantic model)
Outputs: EngineResult (Pydantic model)

Rule: This file is the SINGLE SOURCE OF TRUTH for all calculations.
      The frontend never computes physics — it only calls this API.
"""
import math
from typing import Optional, List, Dict, Any
from ..models.schemas import EngineInput, EngineResult, CapResult, PowerResult


# ── CONSTANTS ─────────────────────────────────────────────────────
MOTOR_SZ = [0.37,0.55,0.75,1.1,1.5,2.2,3,4,5.5,7.5,11,15,18.5,22,30,37,
             45,55,75,90,110,132,160,200,250,315]
SHAFT_STD_MM = [25,30,35,40,45,50,55,60,65,70,75,80,90,100,110,120,130,140,160,180,200]
C_367 = 3600 / 9.81          # = 366.97 — CEMA unit conversion (documented)
PSZ_FROM_CLASS = {
    "A200": 0.075, "A100": 0.15, "A40": 0.42, "B6": 6.0,
    "C1/2": 12.0, "D3": 75.0, "D7": 180.0
}


def nxt_motor(kw: float) -> float:
    for s in MOTOR_SZ:
        if s >= kw:
            return s
    return 315.0


def psz_of(mat: dict) -> float:
    return PSZ_FROM_CLASS.get(mat.get("particle_class", "B6"), 6.0)


# ── INCLINATION FACTOR aFact(θ) ────────────────────────────────────
# CEMA stepped model (default) or continuous exponential.
# Matches JS aFact() exactly.

def mat_recs(mat: dict) -> dict:
    """Generate material and surface recommendations based on material properties."""
    abr   = mat.get("abr", "Low")
    cls   = mat.get("cls", "I")
    moist = mat.get("moist", 0)
    temp  = mat.get("temp_max", 200)
    wc    = calc_wc(mat)

    trough = []
    flight = []
    shaft  = []
    treats = []
    notes  = []

    # Trough
    if abr in ("High", "Very High"):
        trough.append("Hardox 450 / AR400 (6–10 mm) — abrasion-resistant liner")
        trough.append("Replaceable bolt-on wear liners at inlet/outlet")
    elif abr == "Medium":
        trough.append("Carbon steel S355 (6–8 mm)")
    else:
        if moist > 10:
            trough.append("Stainless 304 (4–6 mm) — moisture/corrosion resistance")
        else:
            trough.append("Carbon steel S355 (4–6 mm) — standard duty")

    if temp > 300:
        trough.append("Heat-resistant steel 1.4878 or refractory lining for T > 300°C")
    elif temp > 150:
        trough.append("Thermal insulation jacket recommended for T > 150°C")

    # Flights
    if abr in ("High", "Very High"):
        flight.append("S355 6–8 mm + EN14700-T Fe16 hard-face")
        flight.append("Flame harden OD to 50–55 HRC")
    elif abr == "Medium":
        flight.append("S355 / AISI 4140 — standard flight steel")
        flight.append("Overlay weld OD edge with 55HRC wire if >8,000 h target life")
    else:
        flight.append("S355 / AISI 1045 standard flights")

    if moist > 20:
        flight.append("Stainless 316L recommended for sticky/wet materials")

    # Shaft
    shaft.append("S355 / AISI 1045 solid bar — standard duty")
    if temp > 200:
        shaft.append("42CrMo4 alloy steel for T > 200°C service")
    if cls in ("III", "IV"):
        shaft.append("EN10210 S355J2H pipe viable for light duty")

    # Surface treatments
    if abr in ("High", "Very High"):
        treats.append("Flame harden lower trough to 48–52 HRC")
        treats.append("Induction harden flight edges")
    if moist > 15:
        treats.append("Hot-dip galvanise trough exterior")
        treats.append("Epoxy coat internal surfaces — food-grade if applicable")

    # Notes
    if cls in ("III", "IV"):
        notes.append(f"CEMA Class {cls} — elevated power factor, hardened components advised")
    if wc > 2.0:
        notes.append("High wear coefficient — inspect flights every 2,000 h")

    return {
        "trough":     trough,
        "flight":     flight,
        "shaft":      shaft,
        "treatments": treats,
        "notes":      notes,
    }


def a_fact(ang_deg: float, mat: Optional[dict] = None, continuous: bool = False) -> float:
    b = abs(ang_deg)
    if continuous:
        # Exponential decay: f = exp(-k * ang)
        k = 0.018
        if mat:
            psz = psz_of(mat)
            moist = mat.get("moist", 5)
            wc = calc_wc(mat)
            k = 0.022 if psz > 25 else 0.012 if moist > 20 else 0.018 if wc > 2 else 0.015
        return math.exp(-k * b)
    # CEMA stepped table
    if b <= 0:   return 1.00
    if b <= 5:   return 0.94
    if b <= 10:  return 0.90
    if b <= 15:  return 0.85
    if b <= 20:  return 0.78
    if b <= 25:  return 0.70
    if b <= 30:  return 0.60
    if b <= 35:  return 0.48
    if b <= 40:  return 0.38
    return 0.28


# ── COMPUTED MATERIAL PROPERTIES ───────────────────────────────────
def calc_wc(mat: dict) -> float:
    """Wear coefficient — from abr category + particle size."""
    base = {"Low": 0.25, "Medium": 0.70, "High": 1.40, "Very High": 2.30}.get(
        mat.get("abr", "Medium"), 0.50)
    return min(max(base * (1 + psz_of(mat) / 100), 0.10), 4.50)


def calc_ks(mat: dict) -> float:
    """CEMA Ks conveyability factor."""
    base = {1: 1.0, 2: 0.88, 3: 0.72, 4: 0.55}.get(mat.get("flowability", 2), 0.80)
    coh_penalty = max(0.50, 1 - mat.get("cohesion", 0.2) / 10)
    return max(0.30, min(base * coh_penalty, 1.0))


def calc_lambda(mat: dict) -> float:
    """λ resistance factor — 60% DB reference + 40% parametric."""
    psz = psz_of(mat)
    wc  = calc_wc(mat)
    base = 1.80 if psz < 0.5 else 1.40 if psz < 5.0 else 1.00
    moist = mat.get("moist", 0)
    moist_f = 1.20 if moist > 30 else 0.95 if moist > 20 else 0.98 if moist > 10 else 1.00
    abr_f   = 1.25 if wc > 3 else 1.15 if wc > 2 else 1.05 if wc > 1 else 1.00
    parametric = base * moist_f * abr_f
    blended = 0.6 * (mat.get("lambda_ref") or 1.0) + 0.4 * parametric
    return max(0.4, min(blended, 3.5))


def calc_fill(mat: dict, ang_deg: float = 0, cont_a_fact: bool = False) -> float:
    """Effective fill fraction with inclination + moisture + bridging corrections."""
    fill_max = mat.get("fill_max") or {1: 0.45, 2: 0.40, 3: 0.32, 4: 0.25}.get(
        mat.get("flowability", 2), 0.30)
    f_theta = a_fact(ang_deg, mat, cont_a_fact)
    moist_penalty  = 0.85 if mat.get("moist", 0) > 25 else 0.92 if mat.get("moist", 0) > 15 else 1.0
    bridge_penalty = 0.93 if mat.get("bridging_risk", 0) > 0.40 else 0.97 if mat.get("bridging_risk", 0) > 0.20 else 1.0
    return min(fill_max * f_theta * moist_penalty * bridge_penalty, fill_max)


# ── SHAFT UTILITIES ────────────────────────────────────────────────
def startup_factor(abr: str, temp_c: float = 20, moist: float = 0) -> float:
    sf = 1.5 if abr in ("High", "Very High") else 2.0 if moist > 30 else 1.8 if moist > 20 else 1.5
    if temp_c < 0:    sf += 0.5
    elif temp_c < 5:  sf += 0.25
    return sf


def temp_correction(tau_allow: float, temp_c: float) -> float:
    if temp_c > 300: return tau_allow * 0.55
    if temp_c > 200: return tau_allow * 0.70
    if temp_c > 150: return tau_allow * 0.80
    if temp_c > 100: return tau_allow * 0.90
    return tau_allow


def shaft_wt_solid(od_m: float) -> float:
    return math.pi * od_m**3 / 16


def shaft_wt_pipe(od_m: float, id_m: float) -> float:
    return math.pi * (od_m**4 - id_m**4) / (16 * od_m)


def req_shaft_dia(T_Nm: float, tau_allow_mpa: float) -> float:
    """Minimum solid shaft diameter from torsion."""
    if tau_allow_mpa <= 0 or T_Nm <= 0:
        return 0.025
    return (16 * T_Nm / (math.pi * tau_allow_mpa * 1e6)) ** (1/3)


def auto_select_shaft(T_Nm: float, tau_allow: float, prefer_pipe: bool = False):
    req_m = req_shaft_dia(T_Nm, tau_allow)
    req_mm = req_m * 1000
    sel_mm = next((s for s in SHAFT_STD_MM if s >= req_mm), SHAFT_STD_MM[-1])
    od_m = sel_mm / 1000
    Wt = shaft_wt_solid(od_m)
    tau_act = T_Nm / max(Wt, 1e-12) / 1e6
    sf = tau_allow / max(tau_act, 0.001)
    # Pipe option for shaft OD >= 50 mm
    pipe_opt = None
    if sel_mm >= 50:
        wall = max(6, round(sel_mm * 0.12))
        id_mm = sel_mm - 2 * wall
        if id_mm > 20:
            do_m, di_m = od_m, id_mm / 1000
            Wt_p = shaft_wt_pipe(do_m, di_m)
            tau_p = T_Nm / max(Wt_p, 1e-12) / 1e6
            wt_save = round((1 - (do_m**2 - di_m**2) / do_m**2) * 100)
            pipe_opt = {"od_mm": sel_mm, "wall_mm": wall, "id_mm": id_mm,
                        "tau_mpa": tau_p, "wt_save_pct": wt_save,
                        "ok": tau_p <= tau_allow}
    return {"sel_mm": sel_mm, "req_mm": req_mm, "sf": sf, "od_m": od_m,
            "tau_act": tau_act, "pipe_opt": pipe_opt}


def shaft_deflection_I(w_N_m: float, span_m: float, I_m4: float, E: float = 2.1e11) -> float:
    if I_m4 <= 0 or span_m <= 0:
        return 0.0
    return 5 * w_N_m * span_m**4 / (384 * E * I_m4)


def critical_speed_IA(I_m4: float, A_m2: float, L_m: float,
                       E: float = 2.1e11, support: str = "pinfix") -> float:
    if I_m4 <= 0 or A_m2 <= 0 or L_m <= 0:
        return 9999
    K = 2.00 if support == "fixed" else 1.00 if support == "pinned" else 1.57
    rho_steel = 7850
    omega = (K**2 * math.pi**2 / L_m**2) * math.sqrt((E * I_m4) / (rho_steel * A_m2))
    return omega * 60 / (2 * math.pi)


def hanger_count(L_m: float, D_m: float, mat_abr: str, ang_deg: float) -> dict:
    max_span = 3.6 if D_m >= 0.45 else 3.0 if D_m >= 0.30 else 2.4
    if mat_abr in ("High", "Very High"):
        max_span *= 0.85
    if ang_deg > 20:
        max_span *= 0.90
    count = max(0, math.ceil(L_m / max_span) - 1)
    span  = L_m / (count + 1) if count > 0 else L_m
    return {"count": count, "span": span, "max_span": max_span}


def calc_multi_pitch(L_m, P_in, P_body, P_out, L_in_pct, L_out_pct):
    L_in  = L_m * L_in_pct / 100
    L_out = L_m * L_out_pct / 100
    L_bod = L_m - L_in - L_out
    if L_bod < 0:
        L_bod, L_in, L_out = L_m, 0, 0
    P_eff = (L_in * P_in + L_bod * P_body + L_out * P_out) / L_m
    return {"P_eff": P_eff, "L_in": L_in, "L_body": L_bod, "L_out": L_out}


def gearbox_service_factor(mat: dict, hours_per_day: int = 8) -> float:
    sf = (1.00 if hours_per_day <= 4 else 1.25 if hours_per_day <= 8
          else 1.50 if hours_per_day <= 16 else 1.75)
    if mat.get("abr") in ("High", "Very High") or mat.get("moist", 0) > 20:
        sf += 0.25
    return sf


# ── WEAR MODEL ─────────────────────────────────────────────────────
def wear_rate(mat: dict, fill_actual: float, D: float, N: float, temp_c: float = 20) -> dict:
    v_tip = math.pi * D * N / 60
    P_contact_kPa = fill_actual * mat.get("rho", 1.4) * 9.81 * D
    P_ref_kPa = 3.0
    temp_mult = (2.50 if temp_c > 300 else 1.80 if temp_c > 200
                 else 1.40 if temp_c > 150 else 1.15 if temp_c > 100 else 1.0)
    hardness = {"Very High": 1.60, "High": 1.30, "Medium": 1.00, "Low": 0.75}.get(
        mat.get("abr", "Medium"), 1.0)
    speed_f = (v_tip / 1.0) ** 1.1
    P_factor = max(0.1, P_contact_kPa / P_ref_kPa)
    K_base = 0.006
    wc = calc_wc(mat)
    wrate = K_base * wc * P_factor * speed_f * temp_mult * hardness
    return {"v_tip": v_tip, "P_contact_kPa": P_contact_kPa, "P_factor": P_factor,
            "wrate_mm_h": wrate, "wc": wc}


# ═══════════════════════════════════════════════════════════════════
# MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════

def build_warns(inp: dict, R_partial: dict, mat: dict) -> dict:
    """Build engineering warnings matching the HTML prototype logic."""
    crit, adv, opt = [], [], []

    D     = inp.get("D", 0.3)
    N     = inp.get("N", 60)
    L     = inp.get("L", 10)
    cap   = inp.get("cap", 0)
    ang   = inp.get("ang", 0)
    sallow= inp.get("sallow", 40)

    cap_r = R_partial.get("cap", {})
    tor_r = R_partial.get("tor", {})
    brg_r = R_partial.get("brg_r", {})
    eff_r = R_partial.get("eff", {})
    pwr_r = R_partial.get("pwr", {})
    hgr_r = R_partial.get("hgr", {})
    nc_r  = R_partial.get("nc", 9999)
    nc_ratio = R_partial.get("nc_ratio", 0)

    Qt      = cap_r.get("Qt", 0)
    fill    = cap_r.get("fill_actual", cap_r.get("fill", 0.3))
    shOk    = tor_r.get("shOk", True)
    tau     = tor_r.get("tau", 0)
    L10     = brg_r.get("L10", 99999)
    cap_util= eff_r.get("cap_util", 100)
    kWh_t   = eff_r.get("kWh_t", 0)
    abr     = mat.get("abr", "Medium")
    cls     = mat.get("cls", "I")

    # Capacity
    if Qt < cap * 0.98:
        D_mm = round(D * 1000)
        N_sug = min(300, round(N * (cap / max(Qt, 0.01)) ** 0.5))
        D_sug = [d for d in [150,200,250,300,350,400,450,500,600] if d > D_mm]
        crit.append(
            f"Max capacity {Qt:.1f} t/h < required {cap} t/h. "
            f"{'Suggest Ø' + str(D_sug[0]) + 'mm' if D_sug else 'Increase D'} "
            f"or increase speed to {N_sug} RPM."
        )

    # Utilisation
    if cap_util > 100:
        adv.append(
            f"Screw {cap_util:.0f}% utilised — undersized. "
            f"Suggest Ø{round((D+0.05)*1000/50)*50}mm or increase speed to "
            f"{min(300, round(N * (cap_util/100) ** 0.5))} RPM."
        )
    if cap_util < 70 and cap_util > 0:
        adv.append(
            f"Screw only {cap_util:.0f}% utilised — consider smaller diameter "
            f"for better efficiency."
        )

    # Near max capacity
    if 90 < cap_util <= 100:
        adv.append(
            f"Near max capacity ({cap_util:.0f}% util) — increase diameter one "
            f"CEMA step for reliability margin."
        )

    # Shaft stress
    if not shOk:
        crit.append(
            f"Shaft shear stress {tau:.1f} MPa exceeds allowable {sallow} MPa. "
            f"Increase shaft diameter or reduce torque."
        )

    # Bearing L10
    if L10 < 10000:
        crit.append(f"Bearing L10 life {round(L10):,} h < 10,000 h minimum. Select larger bearing.")
    elif L10 < 20000:
        adv.append(f"Bearing L10 {round(L10):,} h below 20,000 h target. Consider larger bearing or reduce load.")

    # Critical speed
    if nc_ratio > 0.7:
        crit.append(f"Running speed {inp.get('N',0)} RPM is {nc_ratio*100:.0f}% of critical speed Nc={round(nc_r)} RPM. Reduce speed.")
    elif nc_ratio > 0.5:
        adv.append(f"Speed approaching critical ({nc_ratio*100:.0f}% of Nc={round(nc_r)} RPM). Verify shaft stiffness.")

    # Inclination
    if ang > 20:
        adv.append(f"Steep inclination {ang}° — use cleated/paddle flights and verify aFact slip correction.")
    if ang > 30:
        crit.append(f"Inclination {ang}° exceeds CEMA recommended 30° max for standard screw conveyors.")

    # Fill fraction
    if fill * 100 > 45:
        adv.append(f"Fill fraction {fill*100:.1f}% exceeds 45% — flooding risk. Reduce speed or increase diameter.")
    if fill * 100 < 12:
        adv.append(f"Fill fraction {fill*100:.1f}% very low — inefficient operation. Consider smaller diameter.")

    # Energy
    if kWh_t > 2.0:
        adv.append(f"High energy intensity {kWh_t:.2f} kWh/t. Consider larger diameter at lower speed.")

    # Abrasiveness
    if abr in ("High", "Very High"):
        adv.append(f"Material abrasiveness '{abr}' — specify hardened flights (55 HRC) and AR-lined trough.")

    # CEMA class
    if cls in ("III", "IV"):
        adv.append(f"CEMA Class {cls} material — apply service factor to motor and gearbox (min SF 1.25).")

    # Hanger auto-select
    hgr_count = hgr_r.get("count", 0)
    hgr_span  = hgr_r.get("span", L)
    if hgr_count > 0:
        opt.append(
            f"Auto-selected {hgr_count} intermediate hanger bearing{'s' if hgr_count != 1 else ''} "
            f"at {hgr_span:.1f}m span (CEMA) — {hgr_count+1} spans, {hgr_count+2} total shaft supports."
        )

    return {"crit": crit, "adv": adv, "opt": opt}


def calc_engine(inp: dict, mat: dict, brg: dict, gbx: dict, lam_factor: float = 1.0, db=None) -> dict:
    """
    Full screw conveyor sizing engine.
    Identical physics to the validated JavaScript calcEngine.

    Parameters
    ----------
    inp : dict  — conveyor design inputs (matches EngineInput schema)
    mat : dict  — material record from DB (matches Material ORM)
    brg : dict  — bearing record from DB
    gbx : dict  — gearbox record from DB

    Returns
    -------
    dict — complete engineering result (matches EngineResult schema)
    """
    D   = inp["D"]
    L   = inp["L"]
    N   = inp["N"]
    ang = inp.get("ang", 0)
    ang_rad = ang * math.pi / 180
    P   = inp.get("P") or D
    surge = inp.get("surge", 1.2)
    is_pipe = inp.get("type", "screw") == "pipe"
    cont_a_fact = inp.get("contAFact", False)
    duty_h = int(inp.get("duty", 8))

    # ── Fill fraction ────────────────────────────────────────────
    f_theta = a_fact(ang, mat, cont_a_fact)
    if is_pipe:
        # D-06 FINAL: φ_pipe = 0.45 × 0.90 × f(θ) = 0.405 × f(θ)
        # Pipe fill is geometry-constrained, not material-limited.
        # 0.45 = max enclosed fill (pipe wall constraint)
        # 0.90 = service factor for pressure losses / non-uniform packing
        active_fill = 0.45 * 0.90 * f_theta   # = 0.405 at horizontal
    else:
        active_fill = calc_fill(mat, ang, cont_a_fact)

    # ── Loading efficiency η_L ───────────────────────────────────
    v_tip_cap = math.pi * D * N / 60
    eta_L_base  = 0.82 if is_pipe else 0.92
    eta_L_speed = max(0.80, 1.0 - (v_tip_cap - 3.0) * 0.04) if v_tip_cap > 3.0 else 1.0
    eta_L_angle = max(0.82, 1.0 - (ang - 20) * 0.006) if ang > 20 else 1.0
    eta_L_fill  = min(1.0, 0.85 + 0.30 * active_fill)
    eta_L = eta_L_base * eta_L_speed * eta_L_angle * eta_L_fill

    # ── Multi-pitch ──────────────────────────────────────────────
    use_mp = inp.get("use_multipitch", False)
    mp = calc_multi_pitch(
        L,
        inp.get("P_in") or P,
        P,
        inp.get("P_out") or P,
        inp.get("pct_in", 10),
        inp.get("pct_out", 10),
    )
    P_eff = mp["P_eff"]

    # ── λ dynamic (clamped) ─────────────────────────────────────
    lam_raw = calc_lambda(mat)
    lam_dynamic = min(lam_raw, (mat.get("lambda_ref") or 1.0) * 1.40)

    # ── Per-zone capacity ────────────────────────────────────────
    # Capacity — CEMA formula: Qt = (π/4)·D²·P·N·φ·60·ρ
    # η_L (loading efficiency) is a POWER correction, NOT a capacity reduction.
    # Removing η_L from capacity makes engine match HTML prototype exactly.
    _zBase = (math.pi / 4) * D**2 * N * active_fill * 60 * mat["rho"]
    Qt_body   = _zBase * P
    Qt_inlet  = _zBase * (inp.get("P_in") or P) if use_mp else Qt_body
    Qt_outlet = _zBase * (inp.get("P_out") or P) if use_mp else Qt_body
    Qt_governing = min(Qt_body, Qt_inlet, Qt_outlet)

    # ── Feed-limited fill ────────────────────────────────────────
    cap_req = inp.get("cap", 30)
    feed_ratio  = min(1.0, cap_req / Qt_governing) if Qt_governing > 0 else 1.0
    fill_actual = active_fill * feed_ratio

    # ── Pipe transport derating ──────────────────────────────────
    pipe_derate = 0.88 if is_pipe else 1.0
    Qv  = (math.pi / 4) * D**2 * P_eff * N * fill_actual * eta_L * 60 * pipe_derate
    Qt_raw = Qv * mat["rho"]

    # ── D-04 FINAL: Slip factor — v_axial ideal (capacity); t_res slip-corrected ─
    # Capacity Qt: uses ideal v_axial = P·N (no slip). Screw pushes volume forward.
    # Residence time t_res: uses slip-corrected denominator. Material lags the flight.
    # This is correct: without slip correction, dryer/reactor/mixer all overestimate.
    _sf_fill = 0.65 if fill_actual<0.20 else 0.80 if fill_actual<0.35 else 0.90 if fill_actual<0.50 else 0.85
    _sf_incl = 0.85 if ang>15 else 0.92 if ang>5 else 1.0
    slip_S   = max(0.60, min(0.95, _sf_fill * _sf_incl))
    v_axial  = P_eff * (N / 60)               # ideal axial velocity [m/s] — for capacity
    t_res    = L / max(P_eff * (N/60) * slip_S, 1e-6)  # slip-corrected [s] — for process modules

    # ── Flow regime ──────────────────────────────────────────────
    choke_fill = 0.45 if is_pipe else mat.get("fill_max", 0.30)
    Qt_pre = Qt_governing * 0.70 if active_fill > choke_fill else Qt_governing
    regime_Qt = 1.0; regime_Ps = 1.0; regime_name = "Normal"
    if fill_actual > choke_fill:
        regime_Qt, regime_Ps, regime_name = 0.75, 1.25, "Flooding"
    elif Qt_pre < cap_req * 0.95 and cap_req > 0:
        regime_Ps, regime_name = 1.15, "Choking"
    elif fill_actual < 0.12:
        regime_Ps, regime_name = 0.95, "Starved"
    Qt = min(Qt_pre * regime_Qt, Qt_pre)

    # ── Power ────────────────────────────────────────────────────
    Qd = cap_req * surge
    Ce = 0.58 if is_pipe else 0.50
    hgr_auto = hanger_count(L, D, mat.get("abr", "Medium"), ang)
    # User override: hangers=0 means auto, any positive integer = explicit count
    user_hangers_raw = inp.get("hangers")
    # Coerce once, up front. The previous form stored the None check in a
    # bool (`user_override`) and then called int(user_hangers_raw) on the
    # next line — narrowing does not survive that hop, so the int() call was
    # typed as possibly-None. Same runtime behaviour, checkable statically.
    user_hangers = int(user_hangers_raw) if user_hangers_raw is not None else 0
    user_override = user_hangers > 0
    hgr_count = user_hangers if user_override else hgr_auto["count"]
    # Recompute span from actual count: N hangers = N+1 spans
    hgr_span_actual = L / (hgr_count + 1) if hgr_count > 0 else L
    hgr = {
        "count":       hgr_count,
        "span":        hgr_span_actual,      # ← always recomputed from actual count
        "max_span":    hgr_auto["max_span"],
        "auto_count":  hgr_auto["count"],
        "auto_span":   hgr_auto["span"],
        "user_override": user_override,
    }
    hanger_factor = 1.0 if is_pipe else 1 + 0.05 * hgr_count
    Pe = Ce * N * math.sqrt(D) * L / 1000 * hanger_factor

    Ks = calc_ks(mat)
    # D-02: CEMA base Pm + optional fill_coupling (bounded ±15%)
    Pm_base = Qd * L * lam_dynamic * lam_factor * Ks / C_367
    if inp.get("use_fill_coupling", False):
        fill_max_ref = mat.get("fill_max") or 0.30
        fill_coupling = max(0.85, min(1.15,
            0.85 + 0.30 * (fill_actual / max(fill_max_ref, 0.01))))
    else:
        fill_coupling = 1.0  # default: pure CEMA (A=C)
    Pm = Pm_base * fill_coupling
    Pi = Qd * 9.81 * L * math.sin(ang_rad) / 3600
    Ps_ideal = (Pe + Pm + Pi) * regime_Ps

    v_tip_ps = math.pi * D * N / 60
    Pf_base  = 0.10 if is_pipe else 0.07
    Pf_speed = 0.04 * min(1, v_tip_ps / 4)
    Pf_mat   = 0.04 * min(1, calc_wc(mat) / 3)
    Pf_factor = min(0.20, Pf_base + Pf_speed + Pf_mat)
    Pf = (Pe + Pm) * Pf_factor
    Ps = Ps_ideal + Pf

    # ── AGMA SF + motor ─────────────────────────────────────────
    agma_sf_duty = (1.00 if duty_h <= 4 else 1.25 if duty_h <= 8
                    else 1.50 if duty_h <= 16 else 1.75)
    agma_sf_mat  = 0.25 if mat.get("abr") in ("High", "Very High") or mat.get("moist", 0) > 20 else 0.0
    agma_sf_inc  = 0.25 if ang > 15 else 0.0
    agma_sf      = agma_sf_duty + agma_sf_mat + agma_sf_inc
    motor_SF     = agma_sf
    Pt           = Ps / 0.9
    motor_rated  = Pt * motor_SF
    motor        = nxt_motor(motor_rated)

    # ── Torque ───────────────────────────────────────────────────
    omega = 2 * math.pi * N / 60
    Tr     = (Ps * 1000) / omega if omega > 0 else 0
    Tr_max = Tr * 1.25
    temp_c = inp.get("temp_c", 20)
    sf_startup = startup_factor(mat.get("abr", "Medium"), temp_c, mat.get("moist", 0))
    Ts = Tr_max * sf_startup

    # ── Shaft ────────────────────────────────────────────────────
    tau_allow  = temp_correction(inp.get("sallow", 40), temp_c)
    shAuto     = auto_select_shaft(Ts, tau_allow, inp.get("prefer_pipe", False))

    # Manual override support — mirrors HTML prototype exactly
    shaft_mode = inp.get("shaft_mode", "auto")
    shtype     = inp.get("shtype", "bar")
    pod_mm     = float(inp.get("pod", 80) or 80)
    pwall_mm   = float(inp.get("pwall", 8) or 8)

    if shaft_mode == "manual":
        sh_od_m   = max(0.020, pod_mm / 1000)
        if shtype == "pipe":
            sh_id_m = max(0.0, sh_od_m - 2 * pwall_mm / 1000)
        else:
            sh_id_m = 0.0
    else:
        sh_od_m = shAuto["od_m"]
        sh_id_m = 0.0   # auto always selects solid bar

    # Section modulus Wt and second moment I — hollow if pipe, solid if bar
    if sh_id_m > 0:
        sh_Wt = shaft_wt_pipe(sh_od_m, sh_id_m)
        I_shaft = math.pi * (sh_od_m**4 - sh_id_m**4) / 64
        A_shaft = math.pi / 4 * (sh_od_m**2 - sh_id_m**2)
    else:
        sh_Wt = shaft_wt_solid(sh_od_m)
        I_shaft = math.pi * sh_od_m**4 / 64
        A_shaft = math.pi / 4 * sh_od_m**2

    tau     = Ts / max(sh_Wt, 1e-12) / 1e6     # startup shear stress (peak)
    tau_run = Tr_max / max(sh_Wt, 1e-12) / 1e6  # running shear
    sh_ok   = tau <= tau_allow

    # Pipe option (always compute both directions for display)
    if shaft_mode == "manual" and shtype == "bar":
        # Show what hollow pipe of same OD would give
        _wall = max(6, round(pod_mm * 0.12))
        _id = pod_mm - 2 * _wall
        if _id > 20:
            _do, _di = pod_mm / 1000, _id / 1000
            _Wt_p = shaft_wt_pipe(_do, _di)
            _tau_p = Ts / max(_Wt_p, 1e-12) / 1e6
            _wt_save = round((1 - (_do**2 - _di**2) / _do**2) * 100)
            shaft_pipe_opt = {"od_mm": pod_mm, "wall_mm": _wall, "id_mm": _id,
                              "tau_mpa": _tau_p, "wt_save_pct": _wt_save,
                              "ok": _tau_p <= tau_allow}
        else:
            shaft_pipe_opt = None
    elif shaft_mode == "manual" and shtype == "pipe":
        # Show solid bar of same OD for reverse comparison
        _do = sh_od_m
        _Wt_bar = shaft_wt_solid(_do)
        _tau_bar = Ts / max(_Wt_bar, 1e-12) / 1e6
        _area_pipe = A_shaft
        _area_bar = math.pi / 4 * _do**2
        _wt_save = round((1 - _area_pipe / _area_bar) * 100)
        shaft_pipe_opt = {"od_mm": pod_mm, "wall_mm": pwall_mm, "id_mm": pod_mm - 2 * pwall_mm,
                          "tau_mpa": tau, "wt_save_pct": _wt_save,
                          "ok": tau <= tau_allow, "vs_bar_tau": _tau_bar,
                          "is_pipe_showing_saving": True}
    else:
        shaft_pipe_opt = shAuto.get("pipe_opt")

    # ── Deflection & critical speed ──────────────────────────────
    shaft_kg_m  = A_shaft * 7850
    nturns_e    = L / max(P_eff, 0.01)
    ds_e        = D * 0.2
    mass        = nturns_e * (math.pi / 4) * (D**2 - ds_e**2) * inp.get("ft", 0.008) * 7850                   + math.pi * D * L * 0.75 * 0.004 * 7850
    flight_kg_m = mass / max(L, 0.001)
    mat_kg_m    = (math.pi / 4) * D**2 * fill_actual * mat["rho"] * 1000
    w_N_m       = (shaft_kg_m + flight_kg_m + mat_kg_m) * 9.81
    # span_m is the distance between supports — drives deflection, Nc, bearing load
    # hgr["span"] is already correctly recomputed from user-specified hanger count
    span_m      = hgr["span"]
    impact_f    = 1.5 if calc_wc(mat) > 2 else 1.35 if calc_wc(mat) > 1 else 1.2
    w_end_kN    = w_N_m * L / 2 * impact_f / 1000
    load        = max(inp.get("bload") or w_end_kN, 0.001)
    support_cond = inp.get("support_cond", "pinfix")
    nc          = critical_speed_IA(I_shaft, A_shaft, span_m, support=support_cond)
    nc_ratio    = N / max(nc, 1)
    deflection  = shaft_deflection_I(w_N_m, span_m, I_shaft)
    defl_limit  = min(span_m / 300, D / 8)
    defl_ok     = deflection <= defl_limit

    # ── Bearing L10 ─────────────────────────────────────────────
    L10_target = 20000 if duty_h <= 8 else 40000 if duty_h <= 16 else 60000
    C_brg = brg.get("C", 43)
    p_brg = brg.get("p", 3)
    L10   = (C_brg / max(load, 0.001)) ** p_brg * 1e6 / (60 * N)
    # Find the smallest adequate bearing that meets L10_target
    brg_adequate = None
    if db is not None and L10 < L10_target:
        from backend.models.tables import Bearing as BrgTable
        needed_C = load * (L10_target * 60 * N / 1e6) ** (1 / p_brg)
        brg_row = db.query(BrgTable).filter(BrgTable.C >= needed_C)                    .order_by(BrgTable.C).first()
        if brg_row:
            brg_adequate = brg_row.name

    # ── Gearbox ─────────────────────────────────────────────────
    Tn_gbx      = gbx.get("Tn", 40000)
    Tn_derated  = round(Tn_gbx / agma_sf)
    gbx_ok      = Ts <= Tn_derated

    # ── Wear ─────────────────────────────────────────────────────
    wr = wear_rate(mat, fill_actual, D, N, temp_c)
    thick_mm = (inp.get("ft", 0.008) - inp.get("wa", 0.003)) * 1000
    life_h   = thick_mm / max(wr["wrate_mm_h"], 1e-8)
    life_t   = life_h * max(Qt, 0)

    # ── Efficiency ───────────────────────────────────────────────
    fill_pct  = fill_actual * 100
    cap_util  = min(200, cap_req / max(Qt, 0.001) * 100)
    kWh_t     = Pt / max(Qt, 0.001)

    # ── Suggested geometry for low utilisation ───────────────────
    target_Qt = cap_req * 1.25
    D_opt_mm  = round(math.sqrt(target_Qt / max(
        (math.pi / 4) * P_eff * N * active_fill * 60 * mat["rho"] * eta_L, 0.001)) * 1000)
    CEMA_D_MM = [150,200,250,300,350,400,450,500,600,650]
    D_next_sm = next((d for d in reversed(CEMA_D_MM)
                      if d < D * 1000 and
                      (math.pi/4)*(d/1000)**2*P_eff*N*active_fill*eta_L*60*mat["rho"] >= cap_req*1.10),
                     None)
    N_opt = round(target_Qt / max(
        (math.pi/4)*D**2*P_eff*active_fill*eta_L*60*mat["rho"], 0.001))

    # ── Vibration risk score (0–10) ──────────────────────────────
    vri_speed = 4.0 if nc_ratio > 0.9 else 3.0 if nc_ratio > 0.8 else 2.0 if nc_ratio > 0.7 else 1.0 if nc_ratio > 0.5 else 0
    vri_defl  = min(3, max(0, deflection/max(defl_limit,1e-9) - 1) * 2)
    vri_len   = min(2, L / 20 * 2)
    vri_mat   = 1.0 if calc_wc(mat) > 3 else 0.5 if calc_wc(mat) > 1 else 0
    vib_risk  = round(min(10, vri_speed + vri_defl + vri_len + vri_mat) * 10) / 10
    vri_label = "Low" if vib_risk < 3 else "Moderate" if vib_risk < 6 else "High" if vib_risk < 8 else "Severe"

    # ── Assemble result ──────────────────────────────────────────
    result = {
        "D": D, "L": L, "N": N, "ang": ang, "is_pipe": is_pipe,
        "P_eff": P_eff, "mp": mp,
        "cap": {
            "Qt": Qt, "Qv": Qv, "Qt_raw": Qt_raw,
            "Qt_body": Qt_body, "Qt_inlet": Qt_inlet,
            "Qt_outlet": Qt_outlet, "Qt_governing": Qt_governing,
            "fill": active_fill, "fill_actual": fill_actual,
            "feed_ratio": feed_ratio, "eta_L": eta_L,
            "pipe_transport_derate": pipe_derate,
            "ok": Qt >= cap_req, "req": cap_req,
            "lam_used": lam_dynamic,
            "slip_S": slip_S, "v_axial": v_axial, "t_res": t_res,
        },
        "pwr": {
            "Pe": Pe, "Pm": Pm, "Pm_base": Pm_base, "fill_coupling": fill_coupling, "Pi": Pi, "Pf": Pf,
            "Pf_factor": Pf_factor, "Ps_ideal": Ps_ideal,
            "Ps": Ps, "Pt": Pt,
            "motor": motor, "motor_rated": motor_rated, "motor_SF": motor_SF,
        },
        "tor": {
            "Tr": Tr, "Tr_max": Tr_max, "Ts": Ts,
            "od": shAuto["sel_mm"], "tau": tau, "tau_run": tau_run,
            "shOk": sh_ok,
            "eff_od_mm": sh_od_m * 1000,
            "eff_id_mm": sh_id_m * 1000,
            "pipe": sh_id_m > 0,
            "I_m4": I_shaft, "A_m2": A_shaft,
        },
        "shaft_auto": {**shAuto, "pipe_opt": shaft_pipe_opt},
        "shaft_mode": shaft_mode,
        "brg_r": {
            "name": brg.get("name"), "C": C_brg, "load": load,
            "load_auto": w_end_kN, "L10": L10, "L10_target": L10_target,
            "ok": L10 >= L10_target, "adequate": brg_adequate,
        },
        "hgr": hgr,   # span/count already correct from user override logic
        "deflection": deflection, "defl_limit": defl_limit,
        "deflection_ok": defl_ok,
        "nc": nc, "nc_ratio": nc_ratio,
        "vibration_risk": vib_risk, "vri_label": vri_label,
        "wear": {
            **wr, "thick_mm": thick_mm,
            "life_h": life_h, "life_t": life_t,
        },
        "gbx_r": {
            "model": gbx.get("model"), "Tn": Tn_gbx,
            "Tn_derated": Tn_derated, "tOk": gbx_ok,
            "pOk": Pt <= gbx.get("Pkw", 999),
            "agma_sf": agma_sf,
        },
        "eff": {
            "fill_pct": fill_pct, "cap_util": cap_util,
            "kWh_t": kWh_t,
            "sug_geom": {
                "D_opt_mm": D_opt_mm, "D_next_sm": D_next_sm, "N_opt": N_opt,
                "target_Qt": target_Qt,
            },
        },
    }

    # ── Cost estimate ──────────────────────────────────────────
    abr = mat.get("abr", "Medium")
    if abr == "Low" and (mat.get("moist", 0) or 0) > 10:
        steel_grade = "Stainless 304"
    elif calc_wc(mat) > 2.0:
        steel_grade = "WearLiner"
    else:
        steel_grade = "Steel"
    cost_usd_per_kg = {"Steel": 2.0, "Stainless 304": 5.0, "WearLiner": 6.0,
                       "Hardox 450": 9.0, "Stainless 316": 7.5}.get(steel_grade, 2.0)
    n_turns = L / max(P_eff, 0.01)
    ds = D * 0.2
    flight_mass = 7850 * math.pi * (D**2 / 4 - ds**2 / 4) * (P_eff * 0.015) * n_turns
    trough_mass = 7850 * math.pi * D * 0.006 * L
    screw_mass  = round(flight_mass + trough_mass)
    cost_total  = round(screw_mass * cost_usd_per_kg)

    # ── Efficiency score ───────────────────────────────────────
    Qt_max    = max(Qt, 0.001)
    load_ratio = min(inp.get("cap", Qt) / Qt_max, 1.5)
    eta_load   = load_ratio / 0.3 * 0.5 if load_ratio < 0.3 else (0.95 if load_ratio > 0.95 else load_ratio)
    kWh_t_val  = Pt / Qt_max
    eta_energy = (1.0 if kWh_t_val < 0.3 else
                  0.95 if kWh_t_val < 1.0 else
                  0.75 if kWh_t_val < 2.0 else
                  0.5  if kWh_t_val < 4.0 else 0.2)
    eta_incline = 1 - abs(inp.get("ang", 0)) / 45
    eff_score  = min(100, round(40 * eta_load + 35 * eta_energy + 25 * eta_incline))
    cap_util   = min(200, inp.get("cap", Qt) / Qt_max * 100)

    warns = build_warns(inp, result, mat)
    result.update({
        "regime": {"name": regime_name},
        "mat": mat,
        "warns": warns,
        "cost": {
            "steel": steel_grade,
            "uc": cost_usd_per_kg,
            "mass": screw_mass,
            "total": cost_total,
        },
        "recs": mat_recs(mat),
        "eff": {
            "fill_pct": fill_pct,
            "cap_util": cap_util,
            "kWh_t": kWh_t_val,
            "eta_load": eta_load,
            "eta_energy": eta_energy,
            "eta_incline": eta_incline,
            "score": eff_score,
            "sug_geom": {
                "D_opt_mm": D_opt_mm, "D_next_sm": D_next_sm,
                "N_opt": N_opt, "target_Qt": target_Qt,
            },
        },
    })
    return result


# ═══════════════════════════════════════════════════════════════════════════
# STRUCTURAL — trough plate, flange, bolt, weld, hanger sizing
# ═══════════════════════════════════════════════════════════════════════════
# Ported verbatim from calcStructural() in CalcPage.tsx (which itself matches
# the HTML prototype exactly). This is real stress physics — Barlow pressure
# containment, beam bending between hangers, EN 1092-1 flange, ISO 898-1 bolt,
# AWS D1.1 weld — that previously ran client-side in the React app, in
# violation of "engine.py is the single source of truth for all calculations."
# STRUCTURAL_REVIEW_NOTE.md (option 1) called for exactly this backend port.
#
# The arithmetic is line-for-line identical to the .tsx. Any deviation would
# be a bug: the HTML prototype is the authoritative spec for the equations.
# Values already available from calc_engine() (screw_mass, hanger span) are
# recomputed here rather than shared, because calc_structural derives them
# under its own worst-case assumptions (fill=0.35 default, temp derating) and
# coupling the two would make one silently drift when the other changed.

_PLATE_SERIES_MM = [3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 25, 30]

# ISO 898-1 tensile stress areas (m²), keyed by nominal bolt diameter (mm).
_BOLT_SERIES = [
    {"d": 8,  "A": 36.6e-6},
    {"d": 10, "A": 58.0e-6},
    {"d": 12, "A": 84.3e-6},
    {"d": 16, "A": 157e-6},
    {"d": 20, "A": 245e-6},
    {"d": 24, "A": 353e-6},
]


def _first_plate_ge(value: float, fallback: float = 30) -> float:
    """First standard plate thickness ≥ value; .tsx `PLATE.find(...) || 30`."""
    for t in _PLATE_SERIES_MM:
        if t >= value:
            return t
    return fallback


def calc_structural(
    D_m: float,
    L_m: float,
    rho: float,
    ang: float,
    fill: float = 0.35,
    abr: str = "Medium",
    temp: float = 20,
) -> dict:
    """
    Preliminary structural sizing for a U-trough screw conveyor.

    Direct port of calcStructural(D_m, L_m, rho, ang, fill, abr, temp) in
    CalcPage.tsx. Signature, intermediate variable names, and the returned
    keys are all preserved so the frontend port is a pure display of this
    result with no recomputation.

    Returns plate/cover thickness, flange geometry, bolt spec + adequacy,
    weld throat, hanger span, support reactions, and component masses.
    """
    rk = rho * 1000.0
    g = 9.81

    # Allowable stress derates with temperature (MPa → Pa).
    sa = 100e6 if temp > 200 else 120e6 if temp > 150 else 160e6
    sw = sa * 0.7          # weld allowable
    sb = 144e6             # bolt allowable (gr 8.8)

    # Janssen-style fill depth and hydrostatic + surge pressure.
    fd = D_m * fill * 1.3
    Ph = rk * g * fd
    Pd = Ph * 1.3

    # Hanger span capped by diameter band.
    hs = min(L_m, 3.6 if D_m >= 0.45 else 3.0 if D_m >= 0.3 else 2.4)

    # Distributed weight: material + trough self-weight.
    wm = rk * (math.pi / 4) * D_m * D_m * fill * g
    wt = 22 * D_m * g * (1 + 0.1 * temp / 200)
    ww = wm + wt

    # Simply-supported bending moment between hangers.
    Mm = ww * hs * hs / 8.0
    tb = math.sqrt(4 * Mm / (math.pi * D_m * sa))

    Dm = D_m * 1000.0                       # diameter in mm
    tcm = (3 if Dm < 150 else 4 if Dm < 250 else 5 if Dm < 400
           else 6 if Dm < 600 else 8 if Dm < 900 else 10)   # CEMA code minimum
    wa2 = 4 if abr in ("High", "Very High") else 3 if abr == "Medium" else 2

    # Trough plate: max of beam bending and Barlow pressure, + wear allowance,
    # floored at code minimum, snapped up to a standard plate.
    tc = max(tb, Pd * D_m / (2 * sa)) * 1000.0
    tp = _first_plate_ge(max(math.ceil(tc + wa2), tcm))

    # Cover plate: flat-plate bending under a point maintenance load.
    Pc = 1200 * g / (0.06 * D_m) + 2000
    tcc = math.sqrt(3 * Pc * D_m * D_m / (16 * sa)) * 1000.0
    tc2 = _first_plate_ge(max(tcc + 2, tcm + 1), fallback=12)

    # Flange bolt circle and bolt count (multiple of 4, ~160 mm pitch).
    PCD = D_m + 2 * (tp / 1000.0) + 0.05
    nb = math.ceil(
        math.ceil(max(4, 4 * math.ceil(math.pi * PCD * 1000 / 160)) / 4) * 4
    )
    bp = math.pi * PCD * 1000 / nb

    # End-flange separating force → per-bolt load → required area → bolt.
    Fp = Pd * (math.pi / 4) * D_m * D_m + 2 * math.pi * (D_m / 2) * 0.015 * 6895
    Fe = Fp / nb
    Ab = Fe / sb
    dr = math.sqrt(4 * Ab / math.pi) * 1000.0
    bs = next((b for b in _BOLT_SERIES if b["d"] >= max(dr, 8)),
              _BOLT_SERIES[-1])
    sb_act = Fe / bs["A"] / 1e6

    # Support count and per-support reaction.
    ns = max(2, math.ceil(L_m / hs) + 1)
    Rs = ww * L_m / ns

    # Fillet weld throat (AWS D1.1), min 3 mm.
    wh = max(3, math.ceil(Pd * D_m / (2 * sw * 0.707) * 1000))

    # Component masses.
    sm = round(7850 * math.pi * D_m * 0.006 * L_m
               + (math.pi / 4 * D_m * D_m * L_m * fill * rk))
    tm = round(7850 * math.pi * D_m * (tp / 1000.0) * L_m)

    return {
        "w_total":      round(ww / 1000.0, 3),
        "M_max":        round(Mm / 1000.0, 3),
        "hanger_span":  round(hs, 2),
        "t_plate":      tp,
        "t_cover":      tc2,
        "bolt_size":    f"M{bs['d']} gr.8.8",
        "n_bolts":      nb,
        "bolt_pitch":   round(bp),
        "bolt_ok":      sb_act <= 144,
        "bolt_cap":     round(bs["A"] * 144e6 * nb / 1000.0, 1),
        "pressure_load": round(Fe / 1000.0, 1),
        "weld_size":    wh,
        "flange_t":     _first_plate_ge(max(tp, 11), fallback=14),
        "flange_w":     round(Dm * 0.12 + 20),
        "cover_bp":     round(min(150, Dm / 3)),
        "n_supports":   ns,
        "R_kN":         round(Rs / 1000.0, 1),
        "screw_mass":   sm,
        "trough_mass":  tm,
        "end_react":    round((ww * L_m / 2) / 1000.0, 1),
        "sigma_allow":  round(sa / 1e6),
        "key_b":        28 if Dm >= 100 else 25 if Dm >= 85 else 20 if Dm >= 70 else 16,
    }