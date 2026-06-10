"""
Axial profile engine — Python translation of buildAxialProfile().
Computes per-segment physics (fill, power, torque, wear) along conveyor length.
"""
import math
from typing import List, Dict, Any
from .engine import (
    a_fact, calc_lambda, calc_ks, calc_wc, psz_of,
    calc_fill, critical_speed_IA, shaft_deflection_I,
)


def build_axial_profile(inp: dict, R: dict, mat: dict, segments: int = 60) -> List[Dict]:
    """
    Build axial profile along conveyor length.
    Returns list of segment dicts with x, fill_pct, Qt, pwr_density,
    torque_pm, torque_cumul, wear_rate, axial_velocity, status.
    """
    D   = inp["D"]
    L   = inp["L"]
    N   = inp["N"]
    ang = inp.get("ang", 0)
    ang_rad = ang * math.pi / 180
    P   = inp.get("P") or D
    surge = inp.get("surge", 1.2)
    is_pipe = inp.get("type", "screw") == "pipe"
    Ce  = 0.58 if is_pipe else 0.50
    hgr_span = R["hgr"]["span"]
    hgr_count = R["hgr"]["count"]

    # Multipitch zone lengths
    use_mp  = inp.get("use_multipitch", False)
    L_in    = L * inp.get("pct_in",  10) / 100
    L_out   = L * inp.get("pct_out", 10) / 100
    P_in    = inp.get("P_in")  or P
    P_out   = inp.get("P_out") or P

    profile = []
    torque_cumul = 0.0
    dx = L / segments

    for i in range(segments + 1):
        x = L * i / segments

        # Local pitch and material
        if use_mp:
            local_pitch = P_in if x < L_in else P_out if x > L - L_out else P
        else:
            local_pitch = P

        local_ang  = ang
        local_mat  = mat

        # Fill efficiency
        f_theta = a_fact(local_ang, local_mat, inp.get("contAFact", False))
        if is_pipe:
            fill_eff = min(0.45, mat.get("fill_max", 0.30) * 1.10) * f_theta
        else:
            fill_eff = (mat.get("fill_max", 0.30) or 0.30) * f_theta

        # Qt capacity — EXACT HTML prototype formula:
        # Qt = (π/4)·D²·P·N·φ·60·ρ  where φ = mat.fill_max × f(θ)
        # fill_eff is applied ONCE here, not split across velocity and area.
        A_cross  = (math.pi / 4) * D**2
        Qv_local = A_cross * local_pitch * N * fill_eff * 60   # m³/h
        Qt_cap   = Qv_local * mat["rho"]                        # t/h max capability
        Qt_actual = Qt_cap   # no extra slip — a_fact(θ) already reduces fill_eff
        fill_pct  = fill_eff * 100

        # Axial velocity for display only (m/s) — P·N/60 = pitch per second
        axial_velocity = local_pitch * (N / 60) * fill_eff * f_theta

        # ── Torque gradient dT/dx = (D/2)·λ·Ks·Q(x)/v(x) ─────────
        lam = calc_lambda(mat)
        Ks  = calc_ks(mat)
        Qt_kg_s  = Qt_actual * mat["rho"] * 1000 / 3600
        v_safe   = max(axial_velocity, 0.001)
        dT_dx    = (D / 2) * (lam * Ks * Qt_kg_s / v_safe)     # Nm/m
        torque_cumul += dT_dx * dx

        # Power density
        omega       = 2 * math.pi * N / 60
        n_hgr_est   = max(0, math.ceil(L / (3.6 if D >= 0.45 else 3.0 if D >= 0.3 else 2.4)) - 1)
        Pe_pm       = Ce * N * math.sqrt(D) / 1000 * (1 + 0.05 * n_hgr_est) / max(L, 1)
        Pi_pm       = Qt_kg_s * 9.81 * math.sin(ang_rad) / 1000
        pwr_density = max(Pe_pm, omega * dT_dx / 1000 + Pe_pm + Pi_pm)

        # Wear at this segment
        # Physics: wear driven by tip speed × material hardness × contact pressure
        # Inlet zone (x < 15% of L): 1.8× — fresh abrasive feed, max fill gradient
        # Outlet zone (x > 85% of L): 1.2× — compaction and discharge turbulence
        # Middle zone: 1.0× — steady-state conveying
        # NOTE: Hanger bearings are shaft supports — they do NOT cause flight tip wear.
        #       Removing the incorrect 1.4× hanger proximity multiplier.
        wc       = calc_wc(mat)
        v_tip    = math.pi * D * N / 60
        if x < L * 0.15:
            zone_f = 1.8   # inlet: fresh abrasive feed, max fill gradient
        elif x > L * 0.85:
            zone_f = 1.2   # outlet: discharge turbulence and compaction
        else:
            zone_f = 1.0   # steady-state body zone
        wear_rate = wc * (v_tip / 1.0) * (mat["rho"] / 1.6) * 0.01 * zone_f

        # Flow regime
        choke_fill = 0.45 if is_pipe else mat.get("fill_max", 0.30)
        flood_th   = 0.45 if is_pipe else mat.get("fill_max", 0.30)
        cap_req    = inp.get("cap", 0)
        overfill   = fill_eff > flood_th
        choke      = not overfill and cap_req > 0 and Qt_actual < cap_req
        starve     = not overfill and not choke and fill_pct < 12
        status     = "flood" if overfill else "choke" if choke else "starve" if starve else "ok"

        is_hanger = (hgr_span > 0 and
                     abs(x / hgr_span - round(x / hgr_span)) < (dx / hgr_span)
                     and 0.5 < x < L - 0.5)

        profile.append({
            "x":              round(x, 3),
            "fill_pct":       round(fill_pct, 2),
            "Qt":             round(Qt_actual, 2),
            "Qt_cap":         round(Qt_cap, 2),
            "pwr_density":    round(pwr_density, 4),
            "torque_pm":      round(dT_dx, 2),
            "torque_cumul":   round(torque_cumul, 1),
            "wear_rate":      round(wear_rate, 5),
            "axial_velocity": round(axial_velocity, 4),
            "localAng":       local_ang,
            "localPitch":     round(local_pitch, 4),
            "status":         status,
            "isHanger":       is_hanger,
        })

    return profile
