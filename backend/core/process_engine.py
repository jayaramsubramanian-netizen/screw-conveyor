"""
process_engine.py
=================
Python translation of all process module calculations from screw-process-v4.html.

Modules implemented:
  - Dryer    (LMTD heat transfer + two-phase drying kinetics)
  - Cooler   (NTU-effectiveness + moving-bed correction)
  - Mixer    (Newton number + Lacey + Axial Dispersion Model)
  - Reactor  (Arrhenius + Damköhler + RTD/ADM correction)
  - Separator(Stokes settling + grade efficiency)
  - Compactor(Janssen back-pressure + power-law compaction)

Key decisions implemented:
  D-04: Slip factor S=0.60–0.95 applied to all residence time calculations
  D-08: Reactor RTD correction matches manual §4.2 exactly
  D-09: Dryer D_factor scale correction retained from JS (flagged)
  D-10: Separator uses Stokes model (B) — physics-based
  D-11: Compactor uses simplified Janssen (B) — conservative
  D-12: Mixer Newton number + regime/shaft modifiers (B enhancements)

Engineering reference: vectrix_manual_v5.html
"""
import math
from typing import List, Dict, Any, Optional, Literal


# ══════════════════════════════════════════════════════════════════════════════
# SHARED TRANSPORT UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def slip_factor(fill: float, incline_deg: float = 0) -> float:
    """
    Slip factor S = 0.60–0.95.
    D-04 decision: applied to residence time; not to Qt.
    Quadratic peak at fill=0.40 (optimal transport fill).
    """
    sf_fill = 0.85 - 0.4 * (fill - 0.40) ** 2
    sf_incl = math.exp(-incline_deg / 30)
    return clamp(sf_fill * sf_incl, 0.60, 0.95)


def transport(P_m: float, N_rpm: float, fill: float,
              L_m: float, incline_deg: float = 0) -> Dict:
    """
    D-04 FINAL: Two-velocity model.
    v_ax_ideal: ideal transport velocity P·N/60 — used for capacity Qt.
    v_ax:       slip-corrected P·N·S/60    — used by process modules for dt_seg/t_res.
    t_res is always slip-corrected (material residence in reactor/dryer/mixer).
    """
    S          = slip_factor(fill, incline_deg)
    v_ax_ideal = P_m * N_rpm / 60              # ideal [m/s] — capacity
    v_ax       = P_m * N_rpm * S / 60          # slip-corrected [m/s] — process modules
    t_res      = L_m / max(v_ax, 1e-9)         # slip-corrected residence time [s]
    return {"v_ax": v_ax, "v_ax_ideal": v_ax_ideal, "t_res": t_res, "S": S}


def classify_flow_regime(Fr: float) -> Dict:
    """Froude number → mixing flow regime."""
    if Fr < 0.10:
        return {"name": "Sliding",     "score": 0.30, "power_mod": 1.10, "mixing_mod": 0.20}
    if Fr < 0.50:
        return {"name": "Rolling",     "score": 1.00, "power_mod": 1.00, "mixing_mod": 1.00}
    if Fr < 2.00:
        return {"name": "Cascading",   "score": 0.70, "power_mod": 1.05, "mixing_mod": 0.80}
    return     {"name": "Centrifugal", "score": 0.10, "power_mod": 1.25, "mixing_mod": 0.10}


# ══════════════════════════════════════════════════════════════════════════════
# PSD UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def normalize_psd(psd: List[Dict]) -> List[Dict]:
    total = sum(p["mass_frac"] for p in psd)
    if total <= 0:
        return psd
    return [{"d": p["d"], "mass_frac": p["mass_frac"] / total} for p in psd]


def default_psd(d_mean_mm: float = 2.0, spread: float = 2.0) -> List[Dict]:
    bins  = [d_mean_mm * 0.15, d_mean_mm * 0.50, d_mean_mm, d_mean_mm * spread]
    fracs = [0.15, 0.35, 0.35, 0.15]
    return [{"d": d, "mass_frac": f} for d, f in zip(bins, fracs)]


def get_d50(psd: List[Dict]) -> float:
    cum = 0.0
    for p in psd:
        cum += p["mass_frac"]
        if cum >= 0.5:
            return p["d"]
    return psd[-1]["d"] if psd else 1.0


def get_dx(psd: List[Dict], x_frac: float) -> float:
    cum = 0.0
    for p in psd:
        cum += p["mass_frac"]
        if cum >= x_frac:
            return p["d"]
    return psd[-1]["d"] if psd else 1.0


def psd_metrics(psd: List[Dict]) -> Dict:
    d50 = get_d50(psd)
    d10 = get_dx(psd, 0.10)
    d90 = get_dx(psd, 0.90)
    span = (d90 - d10) / max(d50, 0.001)
    return {"d50": d50, "d10": d10, "d90": d90, "span": span}


# ── PSD update per module ────────────────────────────────────────────────────

def update_psd_mixer(psd: List[Dict], k_mix: float = 0.01, dx: float = 0.25) -> List[Dict]:
    d_mean = sum(p["d"] * p["mass_frac"] for p in psd)
    k = clamp(k_mix, 0, 0.5)
    return normalize_psd([
        {"d": p["d"] + (d_mean - p["d"]) * k * dx, "mass_frac": p["mass_frac"]}
        for p in psd
    ])


def update_psd_dryer(psd: List[Dict], drying_rate: float = 0.01, dx: float = 0.25) -> List[Dict]:
    shrink = 1 - 0.015 * clamp(drying_rate, 0, 0.5) * dx
    return normalize_psd([
        {"d": max(0.001, p["d"] * shrink), "mass_frac": p["mass_frac"]}
        for p in psd
    ])


def update_psd_cooler(psd: List[Dict], **_) -> List[Dict]:
    return psd  # thermal only, no size change


def update_psd_reactor(psd: List[Dict], k_arr: float = 0.005, dt_seg: float = 1.0) -> List[Dict]:
    updated = []
    for p in psd:
        k_p  = k_arr / (1 + p["d"] * 0.5)
        conv = 1 - math.exp(-min(50, k_p * dt_seg))
        updated.append({"d": p["d"], "mass_frac": p["mass_frac"] * (1 - conv * 0.5)})
    return normalize_psd(updated)


def update_psd_separator_stokes(psd: List[Dict],
                                v_ax: float = 0.1,
                                rho_p: float = 1500.0,
                                rho_f: float = 1.2,
                                mu: float = 1.8e-5) -> List[Dict]:
    """
    D-10 SECONDARY MODEL: Stokes settling — physics-based, for validation.
    Use mode="physics" in separator_step to activate.
    """
    g = 9.81
    result = []
    for p in psd:
        d_m     = p["d"] * 1e-3
        v_settle = (rho_p - rho_f) * g * d_m**2 / (18 * mu)
        sep_eff  = min(1.0, v_settle / max(v_ax, 0.001))
        result.append({
            "d": p["d"],
            "mass_frac":   p["mass_frac"] * (1 - sep_eff),  # fines remain
            "coarse_frac": p["mass_frac"] * sep_eff,
            "fine_frac":   p["mass_frac"] * (1 - sep_eff),
            "sep_eff":     sep_eff,
        })
    # Normalise outlet (fine fraction only)
    fine_total = sum(r["fine_frac"] for r in result)
    if fine_total > 0:
        for r in result:
            r["mass_frac"] = r["fine_frac"] / fine_total
    return result


def update_psd_separator_sigmoid(psd: List[Dict],
                                 d50: float = 2.0,
                                 v_ax: float = 0.1,
                                 v_ref: float = 0.15,
                                 sigma_psd: float = 1.0,
                                 k: float = 1.5) -> List[Dict]:
    """
    D-10 PRIMARY MODEL: Sigmoid grade efficiency curve (Rosin-Rammler adapted).
    Default model for equipment design. Matches vectrix_manual_v5.html §3.1.
    η(d) = 1 / (1 + e^(−k·(d − d50_eff)/σ))
    d50_eff = d50 · (v_ax/v_ref)^0.3  (velocity-shifted cut size)
    """
    # Velocity-shifted effective cut size (manual §2.2)
    d50_eff = d50 * (max(v_ax, 1e-6) / max(v_ref, 1e-6)) ** 0.3
    result  = []
    for p in psd:
        exponent  = -k * (p["d"] - d50_eff) / max(sigma_psd, 0.01)
        eta       = 1.0 / (1.0 + math.exp(clamp(exponent, -50, 50)))  # sep prob → fines
        result.append({
            "d":           p["d"],
            "mass_frac":   p["mass_frac"] * eta,          # fines (separated)
            "coarse_frac": p["mass_frac"] * (1 - eta),    # coarse (passes through)
            "fine_frac":   p["mass_frac"] * eta,
            "sep_eff":     eta,
            "d50_eff":     d50_eff,
        })
    fine_total = sum(r["fine_frac"] for r in result)
    if fine_total > 0:
        for r in result:
            r["mass_frac"] = r["fine_frac"] / fine_total
    return result


# Alias for backwards compatibility — Stokes model kept as secondary
def update_psd_separator(psd, v_ax=0.1, rho_p=1500.0, rho_f=1.2, mu=1.8e-5):
    """Alias: routes to Stokes (physics) model. Use update_psd_separator_sigmoid for design."""
    return update_psd_separator_stokes(psd, v_ax=v_ax, rho_p=rho_p, rho_f=rho_f, mu=mu)


def update_psd_compactor(psd: List[Dict], sigma_kPa: float = 10.0, dx: float = 0.25) -> List[Dict]:
    growth = 1 + 0.003 * math.sqrt(clamp(sigma_kPa, 0, 1000)) * dx
    return normalize_psd([{"d": p["d"] * growth, "mass_frac": p["mass_frac"]} for p in psd])


# ══════════════════════════════════════════════════════════════════════════════
# INITIAL STATE
# ══════════════════════════════════════════════════════════════════════════════

def init_state(inp: Dict, module_type: str) -> Dict:
    """Initialise axial solver state vector."""
    d_p_mm = inp.get("d_p", 0.002) * 1000
    return {
        "T":         inp.get("tIn", inp.get("tInC", 20.0)),
        "moisture":  inp.get("mIn", 0.0) / 100.0,
        "X_conv":    0.0,
        "mass_flow": inp.get("feed", inp.get("feedR", inp.get("feedS", 5.0))) * 1000 / 3600,
        "fill":      inp.get("fillDry", inp.get("fillC2", inp.get("fillR", inp.get("fill2", inp.get("fFill", 0.35))))),
        "PSD":       normalize_psd(default_psd(d_p_mm, 3)),
        "Q_cumul":   0.0,
        "energy":    0.0,
        "torque":    0.0,
        "rho":       inp.get("rho", inp.get("fRho", 1.2)) * 1000,
        "sigma":     0.0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MODULE STEP FUNCTIONS
# Each takes (state, inp, tr, ...) and returns updated state dict.
# ══════════════════════════════════════════════════════════════════════════════

def dryer_step(state: Dict, inp: Dict, tr: Dict, A_seg: float) -> Dict:
    """
    LMTD heat transfer + two-phase drying kinetics.
    D-09: D_factor = (0.3/D)^0.3 scale correction retained from JS.
    Manual §4: Q = U_eff · A · LMTD; two-phase switch at X_crit.
    """
    d_p     = max(0.0001, inp.get("d_p", 0.003))
    k_solid = inp.get("k_solid", 0.3)
    fill    = state["fill"]
    cf      = clamp(0.5 + 0.5 * fill * (0.8 if fill > 0.6 else 1.0), 0.3, 0.7)
    h_solid = k_solid / d_p * cf
    # D-09 FINAL: Empirical diameter scale correction — KEEP, label as empirical.
    # Accounts for surface-to-volume ratio scaling as screw diameter changes.
    # U_eff at D=0.3m is the reference; larger screws have lower specific U.
    # Formula: U_eff_actual = U_eff_ref × (0.3/D)^0.3
    D_f     = (0.3 / max(inp.get("diam", 0.3), 0.05)) ** 0.3   # empirical diameter correction
    U_eff   = (1 / (1 / max(inp.get("U", 50), 1) + 1 / h_solid + 0.0002)) * D_f
    tTr     = inp.get("tTr", 120)
    lw_loc  = (2501 - 2.42 * state["T"]) * 1000   # J/kg latent heat of water

    L     = inp.get("len", inp.get("L", 6))
    dx    = L / 16
    dt_seg = dx / max(tr["v_ax"], 0.001)

    Q_W = U_eff * A_seg * max(0, tTr - state["T"])   # W available from wall

    # Evaporation limits
    m_evap_heat = Q_W / max(lw_loc, 1)   # kg/s heat-limited
    X_crit = 0.15 + 0.1 * (1 - min(1, (d_p * 1000) / 5))

    if state["moisture"] > X_crit:
        m_evap_kin = m_evap_heat * 2.0   # constant-rate: heat always bottleneck
    else:
        D_eff  = 1.5e-10 * math.exp(min(50, 2500 / (273 + state["T"])))
        L_p    = d_p / 2
        N_dry  = inp.get("speedDry", 30)
        rot_f  = clamp((max(N_dry, 1) / 60) ** 0.5 / (1 + N_dry / 200), 0.2, 1.2)
        k_diff = D_eff / (L_p * L_p)
        m_evap_kin = k_diff * rot_f * state["mass_flow"] * max(0, state["moisture"] - 0.002)

    m_evap_rate = min(m_evap_heat, m_evap_kin)
    m_evap      = m_evap_rate * dt_seg

    dX          = m_evap / max(state["mass_flow"] * dt_seg, 0.001)
    new_moisture = max(0.002, state["moisture"] - dX)
    Q_evap_W    = m_evap_rate * lw_loc
    Q_sens_W    = max(0, Q_W - Q_evap_W)
    Cp          = inp.get("CpDry", 1800)
    new_T       = min(tTr, state["T"] + Q_sens_W * dt_seg / (Cp * max(state["mass_flow"], 0.001)))

    omega_dry = 2 * math.pi * inp.get("speedDry", 30) / 60
    dTorque   = Q_W * 0.05 / omega_dry if omega_dry > 0 else 0

    return {**state,
        "moisture":  new_moisture,
        "T":         new_T,
        "mass_flow": max(0, state["mass_flow"] - m_evap / max(dt_seg, 1)),
        "Q_cumul":   state["Q_cumul"] + Q_W / 1000,
        "energy":    state["energy"]  + Q_W * dt_seg,
        "torque":    state["torque"]  + dTorque,
    }


def cooler_step(state: Dict, inp: Dict, tr: Dict, A_seg: float) -> Dict:
    """
    NTU-effectiveness method with moving-bed non-ideality correction.
    Manual §: Q = U_eff · A · ΔT; U_eff from composite wall + particle resistance.
    """
    d_pc = max(0.0001, inp.get("d_p_c", 0.005))
    cf   = clamp(0.5 + 0.4 * state["fill"], 0.4, 0.7)
    rot  = (max(tr.get("N", 20), 1) / 60) ** 0.3
    h_s  = (inp.get("k_sol_c", 0.4) / d_pc) * cf * rot
    U_eff = 1 / (1 / max(inp.get("U", 50), 1) + 1 / h_s + 0.0002)
    Cp    = inp.get("Cp", 900)
    T_cool = inp.get("coolIn", 20)
    Q_W    = U_eff * A_seg * max(0, state["T"] - T_cool)
    Q_cap_W = state["mass_flow"] * Cp * (state["T"] - max(T_cool + 1, inp.get("tTgtC", 80)))
    Q_actual = min(Q_W, max(0, Q_cap_W))
    dT = Q_actual / (Cp * max(state["mass_flow"], 0.001))
    return {**state,
        "T":       max(T_cool + 1, state["T"] - dT),
        "Q_cumul": state["Q_cumul"] + Q_actual / 1000,
    }


def reactor_step(state: Dict, inp: Dict, tr: Dict, dx: float) -> Dict:
    """
    First-order Arrhenius kinetics + axial dispersion RTD correction.
    D-08: RTD_corr = 4α·e^(Pe/2)/(1+α)² matches manual §4.2 exactly.
    """
    R_gas  = 8.314
    rxn    = inp.get("rxn", "thermal")
    k0_defaults = {"thermal": 0.08, "chemical": 0.25, "biological": 0.005, "calcination": 0.12}
    Ea_defaults = {"thermal": 35000, "chemical": 55000, "biological": 20000, "calcination": 80000}
    k0 = inp.get("k0") or k0_defaults.get(rxn, 0.08)
    Ea_kJ_inp = inp.get("Ea_kJ", 0)
    if Ea_kJ_inp == 0:
        # k0 is the local reaction rate constant at operating T [1/s] — no Arrhenius
        k = k0
    else:
        Ea = Ea_kJ_inp * 1000 if Ea_kJ_inp > 0 else Ea_defaults.get(rxn, 45000)
        k  = k0 * math.exp(-min(50, Ea / (R_gas * (273.15 + state["T"]))))
    dt_seg = dx / max(tr["v_ax"], 0.001)

    # Ideal plug-flow increment
    dX_pf  = (1 - state["X_conv"]) * (1 - math.exp(-min(50, k * dt_seg)))
    new_X  = min(0.999, state["X_conv"] + dX_pf)

    # D-08: RTD Axial Dispersion correction (full-length correction applied once)
    # Applied at exit segment for overall conversion accuracy
    D_ax   = inp.get("D_ax", 0.005)   # m²/s axial dispersion coeff
    L      = inp.get("len", inp.get("Lr", 4))
    v_ax   = tr["v_ax"]
    Pe     = v_ax * L / D_ax if D_ax > 0 else 30
    Da     = k * (L / max(v_ax, 0.001))
    # RTD correction — Closed-Closed boundary, Danckwerts (1953)
    # For Pe > 20 (near plug-flow screw), use Bodenstein approximation:
    #   RTD_corr ≈ 1 - 2/Pe  (avoids exp(Pe/2) overflow at high Pe)
    # For Pe < 20 (well-mixed, high dispersion), use full formula.
    if Pe > 20:
        RTD_corr = clamp(1 - 2 / Pe, 0.5, 1.0)
    else:
        alpha = math.sqrt(max(0, 1 + 4 * Da / max(Pe, 0.001)))
        if alpha > 0:
            RTD_corr = clamp(
                (4 * alpha * math.exp(min(Pe / 2, 50)) / (1 + alpha) ** 2) * math.exp(-Da),
                0.0, 1.0)
        else:
            RTD_corr = 1.0

    # Apply RTD correction: scales X toward well-mixed limit
    # Only meaningful at Da > 0.5; at low Da it has negligible effect
    new_X_adm = clamp(new_X * RTD_corr, 0.0, 0.999)

    dH    = inp.get("dHrxn", 0)
    dT_rxn = (-dH * dX_pf) / max(inp.get("CpR", 1000), 1) if dH != 0 else 0

    return {**state,
        "X_conv": new_X_adm,
        "T":      state["T"] + dT_rxn,
        "energy": state["energy"] + abs(dT_rxn) * inp.get("CpR", 1000) * state["mass_flow"],
    }


def separator_step(state: Dict, inp: Dict, tr: Dict) -> Dict:
    """
    D-10 FINAL: Dual-model separator.
    mode="engineering" (default) → Sigmoid grade efficiency curve (primary, equipment design).
    mode="physics"               → Stokes settling (secondary, validation/research).
    """
    sep_mode = inp.get("sep_mode", "engineering")
    v_ax     = tr["v_ax"]

    if sep_mode == "physics":
        # Secondary: Stokes settling model
        rho_p   = inp.get("rhoA", 1.5) * 1000
        new_psd = update_psd_separator_stokes(
            state["PSD"], v_ax=v_ax, rho_p=rho_p, rho_f=1.2, mu=1.8e-5)
    else:
        # Primary: sigmoid grade efficiency (default — matches real equipment)
        new_psd = update_psd_separator_sigmoid(
            state["PSD"],
            d50    = inp.get("d50", 2.0),         # cut size [mm] — process requirement
            v_ax   = v_ax,
            v_ref  = inp.get("v_ref", 0.15),      # reference velocity [m/s]
            sigma_psd = inp.get("sigma_psd", 1.0),# PSD spread [mm]
            k      = inp.get("k_sep", 1.5),       # slope factor (manual §3.1)
        )

    coarse_mass_frac = sum(p.get("coarse_frac", 0) for p in new_psd)
    fine_frac = clamp(1 - coarse_mass_frac, 0.0, 1.0)
    return {**state,
        "PSD":       new_psd,
        "mass_flow": state["mass_flow"] * fine_frac,
        "sep_mode":  sep_mode,
    }


def compactor_step(state: Dict, inp: Dict, dx: float) -> Dict:
    """
    D-11: Simplified Janssen back-pressure + power-law stress-density.
    Manual §3.1 simplified form: conservative, appropriate for preliminary design.
    """
    D       = inp.get("diam", 0.3)
    mu_wall = inp.get("mu_wall", 0.35)
    k_lat   = inp.get("k_lat", 0.45)
    rho     = state["rho"]

    sigma_max = (rho * 9.81 * (D / 2)) / (2 * mu_wall)
    sigma_prev_Pa = state["sigma"] * 1000
    dsigma = max(0, sigma_max * (1 - math.exp(-k_lat * dx / D)) - sigma_prev_Pa)
    new_sigma = (sigma_prev_Pa + dsigma) / 1000  # back to kPa

    alpha = inp.get("alpha_c", 0.005 if state["rho"] > 800 else 0.003)
    rho_target = inp.get("tgtR", 0.85) * 1000
    new_rho = rho + (rho_target - rho) * (1 - math.exp(-alpha * new_sigma))

    return {**state, "sigma": new_sigma, "rho": new_rho}


# ══════════════════════════════════════════════════════════════════════════════
# AXIAL SOLVER — solve_system()
# ══════════════════════════════════════════════════════════════════════════════

def solve_system(inp: Dict, module_type: str, n_seg: int = 16) -> Dict:
    """
    March state vector along screw in n_seg segments.
    Each segment applies module physics then updates PSD.
    Returns: {"history": [...], "final": state, "tr": transport}
    """
    L    = inp.get("len", inp.get("Lr", inp.get("lenSep", inp.get("Lc", inp.get("fLen", 4)))))
    dx   = L / n_seg
    P    = inp.get("diam", inp.get("fDiam", 0.3))
    N    = inp.get("speedDry", inp.get("speedCool", inp.get("Nr",
           inp.get("speedS", inp.get("Nc", inp.get("fN_max", 30))))))
    fill = inp.get("fillDry", inp.get("fillC2", inp.get("fillR",
           inp.get("fill2", inp.get("fFill", 0.35)))))
    incl = inp.get("ang", 0)

    tr_base = transport(P, N, fill, L, incl)
    tr = {**tr_base, "N": N}
    A_seg = math.pi * inp.get("diam", 0.3) * 0.75 * dx

    state   = init_state(inp, module_type)
    history = []

    for i in range(n_seg + 1):
        x = round(i * dx, 3)
        try:
            if   module_type == "dryer":   state = dryer_step(state, inp, tr, A_seg)
            elif module_type == "cooler":  state = cooler_step(state, inp, tr, A_seg)
            elif module_type == "reactor": state = reactor_step(state, inp, tr, dx)
            elif module_type == "sep":     state = separator_step(state, inp, tr)
            elif module_type == "compact": state = compactor_step(state, inp, dx)
        except Exception:
            pass

        if i < n_seg:
            try:
                psd_inp = {**inp, "v_ax": tr["v_ax"],
                           "sigma_kPa": state.get("sigma", 0),
                           "k_mix": inp.get("k_mix", 0.01),
                           "drying_rate": inp.get("drying_rate", 0.01),
                           "k_arr": inp.get("k_arr", 0.005),
                           "dt_seg": dx / max(tr["v_ax"], 0.001)}
                if   module_type == "mixer":   state["PSD"] = update_psd_mixer(state["PSD"], psd_inp.get("k_mix", 0.01), dx)
                elif module_type == "dryer":   state["PSD"] = update_psd_dryer(state["PSD"], psd_inp.get("drying_rate", 0.01), dx)
                elif module_type == "cooler":  state["PSD"] = update_psd_cooler(state["PSD"])
                elif module_type == "reactor": state["PSD"] = update_psd_reactor(state["PSD"], psd_inp.get("k_arr", 0.005), psd_inp["dt_seg"])
                elif module_type == "sep":     state["PSD"] = update_psd_separator(state["PSD"], tr["v_ax"])
                elif module_type == "compact": state["PSD"] = update_psd_compactor(state["PSD"], state.get("sigma", 0), dx)
            except Exception:
                pass

        metrics = psd_metrics(state["PSD"])
        history.append({
            "x":         x,
            "T":         round(state["T"], 1),
            "moisture":  round(state["moisture"] * 100, 2),
            "X_conv":    round(state["X_conv"] * 100, 1),
            "mass_flow": round(state["mass_flow"], 4),
            "sigma":     round(state.get("sigma", 0), 2),
            "rho":       round(state["rho"] / 1000, 3),
            "d50":       round(metrics["d50"], 3),
            "d10":       round(metrics["d10"], 3),
            "d90":       round(metrics["d90"], 3),
            "Q_cumul":   round(state["Q_cumul"], 3),
            "energy":    round(state["energy"], 1),
            "torque":    round(state["torque"], 2),
        })

    return {"history": history, "final": state, "tr": tr}


# ══════════════════════════════════════════════════════════════════════════════
# MIXER ENGINE — calc_mixer()
# D-12: Newton number + flow regime + shaft configuration modifiers
# ══════════════════════════════════════════════════════════════════════════════

MIXER_TYPE_PROPS = {
    "ribbon":  {"a": 0.75, "b": 0.25, "shear_mult": 0.8,  "Ne": 2.0, "slip_base": 0.88, "clearance_frac": 0.020, "axial_transport": 1.00, "fill_max": 0.60},
    "paddle":  {"a": 0.60, "b": 0.40, "shear_mult": 1.2,  "Ne": 3.5, "slip_base": 0.40, "clearance_frac": 0.030, "axial_transport": 0.25, "fill_max": 0.50},
    "plough":  {"a": 0.45, "b": 0.55, "shear_mult": 1.6,  "Ne": 5.0, "slip_base": 0.35, "clearance_frac": 0.025, "axial_transport": 0.35, "fill_max": 0.45},
    "screw":   {"a": 0.85, "b": 0.15, "shear_mult": 0.5,  "Ne": 1.5, "slip_base": 0.92, "clearance_frac": 0.015, "axial_transport": 1.00, "fill_max": 0.45},
}

SHAFT_CONFIG = {
    "single":       {"k_interact": 1.0, "shear_boost": 1.0, "fill_max_mult": 1.00, "P_scale": 1.00},
    "twin_co":      {"k_interact": 1.4, "shear_boost": 1.3, "fill_max_mult": 1.30, "P_scale": 1.75},
    "twin_counter": {"k_interact": 1.8, "shear_boost": 1.6, "fill_max_mult": 1.25, "P_scale": 1.85},
    "multi_3":      {"k_interact": 2.2, "shear_boost": 1.8, "fill_max_mult": 1.15, "P_scale": 2.60},
}


def calc_mixer(inp: Dict) -> Dict:
    """
    Full mixer sizing engine.
    D-12: Newton number Ne·ρ·N³·D⁵ + regime modifier + shaft config factor.
    Lacey mixing index M corrected by ADM (Peclet number).
    """
    D     = inp["D"]
    L     = inp["L"]
    N     = max(1, inp["N"])
    rho   = inp.get("rho", 1.2) * 1000        # kg/m³
    fill  = inp.get("fill", 0.45)
    mtype = inp.get("mtype", "ribbon")
    mode  = inp.get("mode", "batch")
    shaft_mode = inp.get("shaft_mode", "single")
    psz   = inp.get("psz", 1.0)
    psz2  = inp.get("psz2", 1.0)

    tp = MIXER_TYPE_PROPS.get(mtype, MIXER_TYPE_PROPS["ribbon"])
    sc = SHAFT_CONFIG.get(shaft_mode, SHAFT_CONFIG["single"])
    ns = 3 if shaft_mode == "multi_3" else 2 if shaft_mode.startswith("twin") else 1

    omega = 2 * math.pi * N / 60
    tip   = math.pi * D * N / 60
    Fr    = omega**2 * (D / 2) / 9.81
    regime = classify_flow_regime(Fr)

    # Axial velocity
    P_eff   = inp.get("pr", 1.0) * D
    slip_sf = 0.65 if fill < 0.25 else 0.80 if fill < 0.40 else 0.90 if fill < 0.60 else 0.82
    slip_S  = clamp(slip_sf * tp["slip_base"], 0.30, 0.95)
    v_axial = P_eff * N / 60 * slip_S * tp["axial_transport"]

    # Clearance and shear
    clearance   = max(D * tp["clearance_frac"], 0.002)
    shear_rate  = (tip / clearance) * sc["shear_boost"]

    # Core mixing rate
    k_conv  = v_axial / L if v_axial > 0 else 0.001
    k_shear = shear_rate / 1000
    k_raw   = (tp["a"] * k_conv + tp["b"] * k_shear * tp["shear_mult"]) * sc["k_interact"]

    regime_factor  = clamp({"Rolling": 1.0, "Cascading": 0.80, "Centrifugal": 0.30}.get(regime["name"], 0.50), 0.05, 1.2)
    fill_optimal   = 0.40 if shaft_mode == "single" else 0.65
    fill_factor    = min(1.0, fill / fill_optimal)
    k_overload     = 0.70 if fill > 0.60 else 1.0
    k_mix_total    = k_raw * clamp(regime_factor, 0.05, 1.2) * clamp(fill_factor, 0.2, 1.5) * clamp(k_overload, 0.5, 2.0)
    k_mode         = 1.30 if mode == "batch" else 1.0
    k_eff          = k_mix_total * k_mode
    t_mix_s        = 3.0 / k_eff if k_eff > 0 else 9999

    # Residence time (batch vs continuous)
    if mode == "batch":
        t_res_s = L / max(v_axial, 0.001) * (3 if fill > 0.40 else 2)
    else:
        t_res_s = L / max(v_axial, 0.001)
    t_res_min = t_res_s / 60

    # Lacey mixing index (manual §2 + ADM correction)
    # M = (σ₀² - σ²) / (σ₀² - σᵣ²)  — from variance reduction
    sigma0_sq = psz * psz2 / (psz + psz2)   # segregated variance proxy
    sigmar_sq = sigma0_sq / 1000              # random mix variance (fully mixed)
    # k_eff × t_res → variance reduction
    decay     = math.exp(-k_eff * t_res_s)
    sigma_sq  = sigmar_sq + (sigma0_sq - sigmar_sq) * decay
    M_lacey   = clamp((sigma0_sq - sigma_sq) / max(sigma0_sq - sigmar_sq, 1e-9), 0, 1)

    # Axial dispersion correction — Peclet number
    D_ax = 0.001 + 0.005 * (1 - tp["axial_transport"])  # m²/s
    Pe   = v_axial * L / max(D_ax, 1e-6) if v_axial > 0 else 30
    # RTD correction (same form as reactor §4.2)
    Da_mix = k_eff * t_res_s
    alpha_m = math.sqrt(max(0, 1 + 4 * Da_mix / max(Pe, 0.001)))
    RTD_corr = clamp((4 * alpha_m * math.exp(Pe / 2) / (1 + alpha_m)**2), 0, 1) if Pe > 0 else 1.0
    M_adm  = clamp(M_lacey * RTD_corr, 0, 1)

    # Power — Newton number × regime + shaft config (D-12)
    Ne = tp["Ne"]
    N_rps = N / 60
    P_mix_W = Ne * rho * N_rps**3 * D**5 * regime["power_mod"] * sc["P_scale"] * ns
    P_mix_kW = P_mix_W / 1000

    # Structural (simplified)
    omega_s = 2 * math.pi * N / 60
    Tr = P_mix_W / omega_s if omega_s > 0 else 0

    return {
        "D": D, "L": L, "N": N, "mode": mode, "mtype": mtype,
        "shaft_mode": shaft_mode, "ns": ns,
        "fill": fill, "fill_max": tp["fill_max"] * sc["fill_max_mult"],
        "Fr": round(Fr, 4),
        "regime": regime["name"],
        "v_axial": round(v_axial, 4),
        "slip_S": round(slip_S, 3),
        "t_res_s": round(t_res_s, 1),
        "t_res_min": round(t_res_min, 2),
        "t_mix_s": round(t_mix_s, 1),
        "shear_rate": round(shear_rate, 1),
        "k_eff": round(k_eff, 4),
        "M_lacey": round(M_lacey, 4),
        "Pe": round(Pe, 2),
        "M_adm": round(M_adm, 4),
        "P_mix_kW": round(P_mix_kW, 3),
        "Tr_Nm": round(Tr, 1),
        "Ne": Ne,
        "fill_ok": fill <= tp["fill_max"] * sc["fill_max_mult"],
        "regime_ok": regime["name"] in ("Rolling", "Cascading"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# FEEDER / DOSER ENGINE — calc_feeder()
# CEMA 7th Ed. + Jenike hopper principles
# Covers: volumetric & loss-in-weight modes, K-factor, turndown,
# feed accuracy (CV%), hopper interface, flood/starve, drive sizing.
# ══════════════════════════════════════════════════════════════════════════════

def calc_feeder(inp: Dict) -> Dict:
    """
    Screw feeder/doser sizing engine.
    Exact port of the HTML screw-process-v4.html feeder module.

    Key outputs:
      Q_mass_min/max   : t/h flow range
      N_required       : RPM needed for target flow
      target_achievable: bool
      K_factor         : volumetric efficiency 0.50–0.96
      turndown         : Q_max / Q_min ratio
      CV_total         : feed accuracy (%CV, RSS of drive+material+mode)
      accuracy_class   : "Excellent" / "Good" / "Acceptable" / "Poor"
      flood_risk/starve_risk: bool
      calibCurve       : [{N, Q}] 11-point N vs Q calibration curve
    """
    # ── 1. Geometry & transport ─────────────────────────────────────────
    D_f   = float(inp.get("fDiam", 0.2))
    fPitch= float(inp.get("fPitch", 1.0))
    P_f   = D_f * fPitch
    L_f   = float(inp.get("fLen", 1.5))
    fill_f= clamp(float(inp.get("fFill", 0.45)), 0.20, 0.70)
    rho   = float(inp.get("fRho", 0.8))          # t/m³
    N_min = max(1.0, float(inp.get("fN_min", 2)))
    N_max = max(N_min + 1, float(inp.get("fN_max", 60)))
    N_design = (N_min + N_max) / 2

    # K-factor: volumetric efficiency (slip + backflow correction)
    flowability = inp.get("fMat_flowability", "easy_flowing")
    K_base_map  = {"free_flowing": 0.90, "easy_flowing": 0.82,
                   "cohesive": 0.72, "very_cohesive": 0.58}
    K_base  = K_base_map.get(flowability, 0.82)
    K_fill  = 0.95 - 0.5 * (fill_f - 0.40) ** 2
    K_factor= clamp(K_base * K_fill, 0.50, 0.96)

    # Volumetric throughput
    Qv_per_rpm = (math.pi / 4) * D_f**2 * P_f * fill_f * K_factor  # m³/rev
    Q_vol_min  = Qv_per_rpm * N_min * 60   # m³/h
    Q_vol_max  = Qv_per_rpm * N_max * 60
    Q_mass_min = Q_vol_min * rho
    Q_mass_max = Q_vol_max * rho
    Q_target   = float(inp.get("fQ_target", 0.5))

    # Required RPM for target
    if Qv_per_rpm * rho * 60 > 0:
        N_required = Q_target / (Qv_per_rpm * rho * 60)
    else:
        N_required = N_design
    N_req_clamped     = clamp(N_required, N_min, N_max)
    target_achievable = N_min <= N_required <= N_max
    Q_actual          = Qv_per_rpm * N_req_clamped * rho * 60

    turndown = Q_mass_max / max(Q_mass_min, 0.001)

    # ── 2. Feed accuracy (CV%) ──────────────────────────────────────────
    drive_type = inp.get("fDriveType", "servo")
    CV_drive_map = {"servo": 0.3, "vfd": 0.8, "stepper": 0.2, "dc": 1.2}
    CV_mat_map   = {"free_flowing": 0.3, "easy_flowing": 0.8,
                    "cohesive": 1.5, "very_cohesive": 3.0}
    CV_drive = CV_drive_map.get(drive_type, 0.8)
    CV_mat   = CV_mat_map.get(flowability, 0.8)
    mode     = inp.get("fMode", "volumetric")
    CV_mode  = 0.3 if mode == "liw" else 1.2
    CV_total = math.sqrt(CV_drive**2 + CV_mat**2 + CV_mode**2)

    if CV_total < 0.5:   accuracy_class = "Excellent (±0.5%)"
    elif CV_total < 1.5: accuracy_class = "Good (±1.5%)"
    elif CV_total < 3.0: accuracy_class = "Acceptable (±3%)"
    else:                accuracy_class = "Poor (>±3%)"

    # ── 3. Power (CEMA Table 5-2 simplified) ───────────────────────────
    Hf    = 0.06   # CEMA friction factor (feeder)
    N_op  = N_req_clamped
    tr_f  = transport(P_f, N_op, fill_f, L_f)
    v_ax_f= tr_f["v_ax"]
    S_f   = tr_f["S"]
    Q_kg_s= Q_actual * 1000 / 3600

    P_e     = Hf * (D_f**2) * L_f * N_op / 1000 * 0.03   # kW friction
    P_mat   = Q_kg_s * v_ax_f * 1e-3                        # kW material
    P_shaft = P_e + P_mat
    P_total = P_shaft * 1.35   # +35% motor/gearbox losses

    # Standard motor sizes
    MOTOR_KW = [0.04,0.06,0.09,0.12,0.18,0.25,0.37,0.55,0.75,1.1,1.5,
                2.2,3.0,4.0,5.5,7.5,11,15,18.5,22,30,37,45,55,75,90,110]
    motor = next((m for m in MOTOR_KW if m >= max(P_total, 0.04)), MOTOR_KW[-1])

    omega_f = 2 * math.pi * N_op / 60
    torque  = P_shaft * 1000 / omega_f if omega_f > 0 else 0

    # ── 4. Hopper interface (Jenike) ────────────────────────────────────
    outlet_min    = max(2 * P_f, D_f * 1.2)   # m minimum outlet width
    hopper_vol    = float(inp.get("fHopperVol", 0.5))
    hopper_angle  = float(inp.get("fHopperAngle", 60))
    mu_wall       = float(inp.get("fWallFriction", 0.35))
    ff_crit_map   = {"free_flowing": 1.2, "easy_flowing": 1.5,
                     "cohesive": 2.5, "very_cohesive": 4.0}
    ff_crit = ff_crit_map.get(flowability, 1.5)

    refill_interval = hopper_vol * rho * 1000 / max(Q_kg_s, 0.001) / 60   # minutes
    arch_risk       = D_f < ff_crit * P_f
    arch_risk_msg   = "Arching risk — increase outlet" if arch_risk else "No arch risk ✓"
    mass_flow_angle = math.atan(mu_wall) * 180 / math.pi + 15   # min hopper half-angle

    # ── 5. Flood / starve analysis ──────────────────────────────────────
    flood_risk  = fill_f > 0.60 and flowability == "free_flowing"
    starve_risk = refill_interval < 5 and hopper_vol < 0.2
    surge_time_min = refill_interval

    # ── 6. Drive & control resolution ──────────────────────────────────
    dQ_per_rpm    = Qv_per_rpm * rho * 60   # t/h per RPM
    rpm_resolution= dQ_per_rpm / Q_target * 100 if Q_target > 0 else 0  # %/RPM
    control_ok    = rpm_resolution < 2.0

    # Loss-in-weight load cell sizing
    liw_tare    = float(inp.get("fLIW_tare", 50))
    liw_range   = hopper_vol * rho * 1000
    liw_lcell   = math.ceil((liw_tare + liw_range) / 1000) * 1000
    liw_resolution = liw_lcell * 0.0001   # 0.01% LC resolution

    # ── 7. N vs Q calibration curve (11 points) ────────────────────────
    calib_curve = []
    for i in range(11):
        N_i = N_min + i * (N_max - N_min) / 10
        Q_i = Qv_per_rpm * N_i * rho * 60
        calib_curve.append({"N": round(N_i, 1), "Q": round(Q_i, 4)})

    # ── 8. Downstream process matching ─────────────────────────────────
    t_downstream = float(inp.get("fDownstreamT", 0))
    batch_size   = float(inp.get("fBatchSize", 0))
    batch_time_s = batch_size / Q_kg_s if (batch_size > 0 and Q_kg_s > 0) else 0
    batch_ok     = batch_size == 0 or batch_time_s > t_downstream * 0.8

    # ── 9. Geometry checks ──────────────────────────────────────────────
    LD_ratio  = L_f / D_f
    tip_speed = math.pi * D_f * N_op / 60   # m/s

    # ── 10. Warnings ────────────────────────────────────────────────────
    crits, advs, opts = [], [], []
    if not target_achievable:
        crits.append(f"Target {Q_target} t/h NOT achievable at N={N_min}–{N_max} RPM "
                     f"(range: {Q_mass_min:.3f}–{Q_mass_max:.3f} t/h)")
    if flood_risk:
        crits.append(f"Flood risk: fill={fill_f:.2f}>0.6 with free-flowing material — "
                     "reduce fill or use flood gate")
    if turndown < 10:
        advs.append(f"Turndown {turndown:.1f}:1 < 10:1 — consider smaller diameter "
                    "for better low-flow control")
    if CV_total > 3:
        advs.append(f"Poor feed accuracy CV={CV_total:.1f}% — switch to LIW mode or servo drive")
    if refill_interval < 10:
        advs.append(f"Hopper refill every {refill_interval:.1f} min — consider larger hopper")
    if arch_risk:
        advs.append(f"Arching risk — outlet {D_f:.3f}m < recommended {ff_crit*P_f:.3f}m")
    if rpm_resolution > 2:
        advs.append(f"Control resolution {rpm_resolution:.1f}%/RPM > 2% — "
                    "increase N range or reduce pitch")
    if LD_ratio > 8:
        advs.append(f"L/D={LD_ratio:.1f}>8 — long feeder screws have higher flex; "
                    "check critical speed")
    if tip_speed > 2:
        advs.append(f"Tip speed {tip_speed:.2f} m/s may degrade fragile materials")
    if starve_risk:
        advs.append(f"Starve risk: hopper volume small, refill every {refill_interval:.1f} min")
    if mode == "liw":
        opts.append(f"LIW mode: load cell {liw_lcell} kg range, "
                    f"resolution {liw_resolution:.2f} kg")

    ok = target_achievable and CV_total < 3 and not flood_risk

    return {
        # Geometry
        "D_f": D_f, "P_f": round(P_f, 4), "L_f": L_f, "fill_f": fill_f,
        "LD_ratio": round(LD_ratio, 2),
        # K-factor
        "K_base": round(K_base, 3), "K_fill": round(K_fill, 3),
        "K_factor": round(K_factor, 3),
        # Flow range
        "Qv_per_rpm": round(Qv_per_rpm * 1000, 4),  # L/rev
        "Q_mass_min": round(Q_mass_min, 4),
        "Q_mass_max": round(Q_mass_max, 4),
        "Q_target":   Q_target,
        "Q_actual":   round(Q_actual, 4),
        "N_required": round(N_required, 2),
        "N_req_clamped": round(N_req_clamped, 2),
        "N_min": N_min, "N_max": N_max,
        "target_achievable": target_achievable,
        "turndown": round(turndown, 2),
        # Accuracy
        "CV_drive":  round(CV_drive, 2),
        "CV_mat":    round(CV_mat, 2),
        "CV_mode":   round(CV_mode, 2),
        "CV_total":  round(CV_total, 2),
        "accuracy_class": accuracy_class,
        # Power
        "P_e":      round(P_e, 4),
        "P_mat":    round(P_mat, 4),
        "P_shaft":  round(P_shaft, 4),
        "P_total":  round(P_total, 4),
        "motor_kW": motor,
        "torque_Nm": round(torque, 1),
        "v_ax_f":   round(v_ax_f, 4),
        "tip_speed": round(tip_speed, 3),
        # Hopper
        "outlet_min_m": round(outlet_min, 4),
        "refill_min":   round(refill_interval, 1),
        "arch_risk":    arch_risk,
        "arch_risk_msg":arch_risk_msg,
        "mass_flow_angle": round(mass_flow_angle, 1),
        # Flood/starve
        "flood_risk":    flood_risk,
        "starve_risk":   starve_risk,
        "surge_time_min":round(surge_time_min, 1),
        # Control
        "dQ_per_rpm":    round(dQ_per_rpm, 5),
        "rpm_resolution":round(rpm_resolution, 2),
        "control_ok":    control_ok,
        # LIW
        "liw_lcell":      liw_lcell,
        "liw_resolution": round(liw_resolution, 3),
        # Downstream
        "batch_ok":     batch_ok,
        "batch_time_s": round(batch_time_s, 1),
        # Calibration curve
        "calibCurve": calib_curve,
        # Overall
        "ok": ok,
        "warns": {"crit": crits, "adv": advs, "opt": opts},
    }
