"""
Family Designer — sweeps diameter × length for a given material.
"""
import math
from models.schemas import FamilyDesignInput, FamilyResult, FamilyPoint, ConveyorInput
from core import cema, kws, din


def design_family(inp: FamilyDesignInput) -> FamilyResult:
    ENGINES = {"CEMA": cema, "KWS": kws, "DIN": din}
    engine = ENGINES.get(inp.standard, cema)

    points = []
    for D_mm in inp.diameters_mm:
        D = D_mm / 1000.0
        pitch = D               # standard pitch = 1×D
        N_max = 50.0 / D        # approx CEMA peripheral speed limit (1 m/s)
        N     = round(N_max * 0.65)

        for L in inp.lengths_m:
            ci = ConveyorInput(
                material=inp.material,
                capacity_t_h=9999,
                length_m=L,
                angle_deg=inp.angle_deg,
                surge_factor=inp.surge_factor,
                trough_diameter_m=D,
                pitch_m=pitch,
                speed_rpm=N,
                flight_thickness_m=max(0.006, 0.004 + D * 0.02),
                wear_allowance_m=0.003,
                shaft_type="bar",
                bearing_load_kN=max(1.0, 1.2 * D * L),
                shaft_allow_shear_mpa=40.0,
                hangers_count=max(0, int(L / 3) - 1),
                standard=inp.standard,
            )
            try:
                r = engine.calculate(ci)
                points.append(FamilyPoint(
                    diameter_mm=D_mm,
                    length_m=L,
                    max_capacity_t_h=round(r.capacity.achieved_t_h, 2),
                    speed_rpm=N,
                    power_kW=round(r.power.P_total_kW, 3),
                    motor_kW=r.power.motor_selected_kW,
                    torque_Nm=round(r.torque.running_Nm, 1),
                    L10_hours=round(r.bearing.L10_hours, 0),
                    cost_usd=round(r.cost.estimated_cost_usd, 2),
                    kWh_per_tonne=round(r.efficiency.kWh_per_tonne, 4),
                    pitch_m=pitch,
                ))
            except Exception:
                pass

    return FamilyResult(
        standard=inp.standard,
        material=inp.material,
        angle_deg=inp.angle_deg,
        points=points,
        diameter_series=inp.diameters_mm,
        length_series=inp.lengths_m,
    )
