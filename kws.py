"""
DIN 15262 Screw Conveyor Calculation Engine (SI units).
"""
import math
from models.schemas import (
    ConveyorInput, CalculationResult,
    CapacityResult, PowerResult, TorqueResult,
    BearingResult, WearResult, GearboxResult, CostResult,
    EfficiencyResult, MaterialRecsResult,
)
from core.databases import get_costs, get_material, get_bearing, get_gearbox, select_motor, MOTOR_SIZES_KW
from core.utils import (
    volumetric_capacity, power_incline, power_empty_friction,
    shaft_torque, shaft_section_modulus, shaft_shear_stress_from_Wt,
    bearing_L10, wear_life, steel_mass, angle_capacity_factor,
    MOTOR_EFFICIENCY, G, calc_efficiency, get_material_recs,
)

DIN_MU_EMPTY = 0.07


def calculate(inp: ConveyorInput) -> CalculationResult:
    warnings, errors = [], []

    mat = get_material(inp.material)
    brg = get_bearing(inp.bearing_type)
    gbx = get_gearbox(inp.gearbox_model)

    D       = inp.trough_diameter_m
    rho     = mat["bulk_density"]
    lam     = mat["lambda_din"]
    Ks      = mat["Ks"]
    k_w     = mat["wear_coeff"]
    phi     = mat["trough_loading"]
    phi_eff = phi * angle_capacity_factor(inp.angle_deg)

    Qv = volumetric_capacity(D, inp.pitch_m, inp.speed_rpm, phi_eff)
    Qm = Qv * rho
    cap_ok = Qm >= inp.capacity_t_h
    if not cap_ok:
        warnings.append(f"Achieved {Qm:.2f} t/h < required {inp.capacity_t_h} t/h.")
    if inp.angle_deg > 15:
        warnings.append("DIN 15262: Angles >15° require special pitch design and reduced fill ratios.")

    cap_result = CapacityResult(
        volumetric_m3h=round(Qv, 3), achieved_t_h=round(Qm, 3),
        required_t_h=inp.capacity_t_h, capacity_ok=cap_ok, fill_fraction=round(phi_eff, 4),
    )

    Q_design  = inp.capacity_t_h * inp.surge_factor
    cos_theta = math.cos(math.radians(inp.angle_deg))
    sin_theta = math.sin(math.radians(inp.angle_deg))

    P_empty    = power_empty_friction(D, inp.length_m, inp.speed_rpm, inp.hangers_count, Ce=DIN_MU_EMPTY)
    P_material = (Q_design * inp.length_m * lam * Ks * cos_theta) / 367.0
    P_incline  = (Q_design * G * inp.length_m * sin_theta) / 3600.0
    P_shaft    = P_empty + P_material + P_incline
    P_installed = P_shaft / MOTOR_EFFICIENCY
    motor_kW   = select_motor(P_installed, MOTOR_SIZES_KW)

    power_result = PowerResult(
        P_empty_kW=round(P_empty, 3), P_material_kW=round(P_material, 3),
        P_incline_kW=round(P_incline, 3), P_total_kW=round(P_shaft, 3),
        P_shaft_kW=round(P_installed, 3), motor_selected_kW=motor_kW,
    )

    Wt, shaft_od_mm, shaft_id_mm, is_pipe = shaft_section_modulus(
        inp.shaft_type, D, inp.pipe_od_mm, inp.pipe_wall_mm
    )
    T_run    = shaft_torque(P_shaft, inp.speed_rpm)
    T_start  = T_run * 2.5
    tau      = shaft_shear_stress_from_Wt(T_start, Wt)
    shear_ok = tau <= inp.shaft_allow_shear_mpa
    if not shear_ok:
        warnings.append(f"Shaft shear {tau:.1f} MPa > allowable {inp.shaft_allow_shear_mpa} MPa.")

    torque_result = TorqueResult(
        running_Nm=round(T_run, 1), startup_Nm=round(T_start, 1),
        shaft_od_mm=round(shaft_od_mm, 1), shaft_id_mm=round(shaft_id_mm, 1),
        is_pipe=is_pipe, actual_shear_mpa=round(tau, 2), shear_ok=shear_ok,
    )

    L10h, L10mr = bearing_L10(brg["C_kN"], inp.bearing_load_kN, brg["p"], inp.speed_rpm)
    if L10h < 20000:
        warnings.append(f"L10 {L10h:.0f} h < DIN recommended 20,000 h minimum.")

    brg_result = BearingResult(
        bearing_type=inp.bearing_type, C_kN=brg["C_kN"], P_applied_kN=inp.bearing_load_kN,
        exponent=brg["p"], L10_hours=round(L10h, 0), L10_million_rev=round(L10mr, 3),
    )

    wh, wt = wear_life(inp.flight_thickness_m, inp.wear_allowance_m, k_w, inp.speed_rpm, inp.capacity_t_h)
    wear_result = WearResult(
        wear_coefficient=k_w,
        usable_thickness_m=round(inp.flight_thickness_m - inp.wear_allowance_m, 4),
        estimated_life_hours=round(wh, 0), estimated_life_tons=round(wt, 0),
    )

    torque_ok  = T_start <= gbx["max_torque_Nm"]
    thermal_ok = P_installed <= gbx["thermal_power_kW"] * gbx["thermal_sf"]
    if not torque_ok:
        warnings.append(f"Startup torque {T_start:.0f} Nm > gearbox max {gbx['max_torque_Nm']} Nm.")
    if not thermal_ok:
        warnings.append(f"Power {P_installed:.2f} kW exceeds gearbox thermal rating.")

    gbx_result = GearboxResult(
        model=inp.gearbox_model, max_torque_Nm=gbx["max_torque_Nm"],
        thermal_power_kW=gbx["thermal_power_kW"], thermal_sf=gbx["thermal_sf"],
        required_power_kW=round(P_installed, 3), torque_ok=torque_ok, thermal_ok=thermal_ok,
    )

    abr = mat["abrasive"]
    is_ss = abr == "Low" and mat.get("temperature_c", 20) < 80
    steel_type = "Stainless 304" if is_ss else ("WearLiner" if k_w > 2 else "Steel")
    costs = get_costs()
    unit_cost = costs.get(steel_type, costs.get("Steel", 2.0))
    mass_kg   = steel_mass(D, inp.length_m, inp.flight_thickness_m, inp.pitch_m)
    cost_result = CostResult(
        steel_weight_kg=round(mass_kg, 1), material_type=steel_type,
        unit_cost_usd_kg=unit_cost, estimated_cost_usd=round(mass_kg * unit_cost, 2),
    )

    eff_result  = EfficiencyResult(**calc_efficiency(Qm, inp.capacity_t_h, P_installed, phi_eff * 100))
    recs_result = MaterialRecsResult(**get_material_recs(mat))

    return CalculationResult(
        standard="DIN", material=inp.material, inputs=inp,
        capacity=cap_result, power=power_result, torque=torque_result,
        bearing=brg_result, wear=wear_result, gearbox=gbx_result, cost=cost_result,
        efficiency=eff_result, material_recs=recs_result,
        warnings=warnings, errors=errors,
    )
