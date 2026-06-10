"""
Extended Process Modules for Screw Conveyor Applications.

Beyond conveying, screw conveyors are used as:
  1. Mixers / Blenders         (twin-shaft, ribbon, paddle)
  2. Dryers / Dehumidifiers    (heated trough or jacketed screw)
  3. Coolers                   (water-jacketed or air-swept)
  4. Classifiers / Screeners   (variable pitch separation by density/size)
  5. Compactors / Feeders      (metered discharge, live-bottom bins)
  6. Reactors                  (chemical / thermal residence time)

All calculation methods are adapted from:
  - CEMA Screw Conveyor Engineering Standard
  - Perry's Chemical Engineers' Handbook (heat transfer)
  - Industrial Dryer Design (Mujumdar)
  - AIChE mixer design correlations
"""
import math
from typing import Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# 1. MIXER / BLENDER
# ─────────────────────────────────────────────────────────────────────────────

class MixerInput(BaseModel):
    # Geometry
    diameter_m: float = Field(0.3, gt=0)
    length_m: float = Field(3.0, gt=0)
    n_shafts: int = Field(1, ge=1, le=2, description="1=single, 2=twin-shaft")
    flight_type: str = Field("ribbon", description="ribbon | paddle | combination")
    pitch_ratio: float = Field(1.0, description="Pitch/Diameter ratio")
    # Material
    material: str = "Cement"
    bulk_density_t_m3: float = Field(1.2, gt=0)
    # Operation
    speed_rpm: float = Field(40.0, gt=0)
    fill_fraction: float = Field(0.45, gt=0, le=0.75)
    feed_rate_t_h: float = Field(10.0, gt=0)
    # Target
    mixing_index_target: float = Field(0.95, ge=0.5, le=1.0, description="Coefficient of variation target (0-1)")
    material_B_fraction: float = Field(0.3, ge=0, le=1.0, description="Fraction of second component")


class MixerResult(BaseModel):
    # Mixing performance
    residence_time_s: float
    froude_number: float
    mixing_index: float        # Estimated CoV-based mixing quality 0-1
    mixing_ok: bool
    tip_speed_m_s: float
    # Power
    P_mixing_kW: float         # Net mixing power
    P_total_kW: float
    motor_kW: float
    specific_energy_kWh_t: float
    # Throughput
    volume_m3: float
    batch_mass_kg: float
    # Geometry recommendation
    recommended_length_m: float
    n_paddle_rows: int
    warnings: list[str]


def calculate_mixer(inp: MixerInput) -> MixerResult:
    warnings = []
    D = inp.diameter_m
    L = inp.length_m
    N = inp.speed_rpm
    rho = inp.bulk_density_t_m3 * 1000.0  # kg/m³

    # Tip speed (peripheral velocity of flight tips)
    tip_speed = math.pi * D * N / 60.0  # m/s

    # Froude number (inertia/gravity ratio) – key dimensionless mixing parameter
    Fr = (N / 60.0)**2 * D / (2 * 9.81)

    # Residence time
    Q_vol = (math.pi / 4) * D**2 * inp.pitch_ratio * D * N * inp.fill_fraction * 60.0
    if Q_vol <= 0:
        Q_vol = 1e-6
    fill_vol = (math.pi / 4) * D**2 * L * inp.fill_fraction
    residence_s = fill_vol / (Q_vol / 3600.0)

    # Mixing index estimation (empirical, based on Beaudry correlation for screws)
    # MI = 1 - exp(-k × N × t)  where k depends on flight type
    k_mix = {"ribbon": 0.015, "paddle": 0.025, "combination": 0.020}.get(inp.flight_type, 0.015)
    k_mix *= inp.n_shafts  # twin-shaft doubles mixing intensity
    mixing_turns = N * residence_s / 60.0  # total shaft revolutions during residence
    mixing_index = 1.0 - math.exp(-k_mix * mixing_turns)
    mixing_ok = mixing_index >= inp.mixing_index_target

    if not mixing_ok:
        required_turns = -math.log(1 - inp.mixing_index_target) / k_mix
        rec_L = required_turns / N * (Q_vol / 3600.0) / ((math.pi / 4) * D**2 * inp.fill_fraction)
        warnings.append(
            f"Mixing index {mixing_index:.3f} < target {inp.mixing_index_target:.2f}. "
            f"Increase length to ≈{rec_L:.1f} m or speed."
        )
        recommended_L = max(L, rec_L)
    else:
        recommended_L = L

    if tip_speed > 3.0:
        warnings.append(f"Tip speed {tip_speed:.2f} m/s > 3 m/s — risk of material degradation.")
    if Fr > 1.0:
        warnings.append(f"Froude number {Fr:.3f} > 1 — centrifugal effects may reduce mixing quality.")

    # Power (Rautenbach & Mackel correlation for horizontal mixer):
    # P = Ne × ρ × N³ × D⁵
    # Newton number Ne ≈ 4.0 (paddle), 2.5 (ribbon), 3.5 (combination)
    Ne = {"ribbon": 2.5, "paddle": 4.0, "combination": 3.5}.get(inp.flight_type, 2.5)
    Ne *= inp.n_shafts**0.8   # shaft count correction
    P_mixing = Ne * rho * (N / 60.0)**3 * D**5 / 1000.0  # kW

    # Scale by fill
    P_mixing *= (inp.fill_fraction / 0.4) ** 0.6
    P_total = P_mixing * 1.15  # 15% mechanical losses

    # Motor selection (simple)
    motor_kW = _next_motor(P_total)

    volume = (math.pi / 4) * D**2 * L * inp.fill_fraction
    batch_mass = volume * rho

    specific_energy = (P_total / (inp.feed_rate_t_h + 1e-9))

    n_paddle_rows = max(3, int(L / (D * 0.5)))

    return MixerResult(
        residence_time_s=round(residence_s, 1),
        froude_number=round(Fr, 4),
        mixing_index=round(mixing_index, 4),
        mixing_ok=mixing_ok,
        tip_speed_m_s=round(tip_speed, 3),
        P_mixing_kW=round(P_mixing, 3),
        P_total_kW=round(P_total, 3),
        motor_kW=motor_kW,
        specific_energy_kWh_t=round(specific_energy, 3),
        volume_m3=round(volume, 4),
        batch_mass_kg=round(batch_mass, 1),
        recommended_length_m=round(recommended_L, 2),
        n_paddle_rows=n_paddle_rows,
        warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. DRYER / DEHUMIDIFIER
# ─────────────────────────────────────────────────────────────────────────────

class DryerInput(BaseModel):
    diameter_m: float = Field(0.3, gt=0)
    length_m: float = Field(6.0, gt=0)
    speed_rpm: float = Field(5.0, gt=0)
    # Material
    material: str = "Grain (Wheat)"
    bulk_density_t_m3: float = Field(0.75, gt=0)
    feed_rate_t_h: float = Field(5.0, gt=0)
    fill_fraction: float = Field(0.35, gt=0)
    # Moisture
    moisture_in_pct: float = Field(18.0, ge=0, le=60, description="Inlet moisture content (%wb)")
    moisture_out_pct: float = Field(13.5, ge=0, le=60, description="Target outlet moisture (%wb)")
    # Thermal
    trough_temp_c: float = Field(80.0, description="Heating medium / trough temperature (°C)")
    inlet_temp_c: float = Field(20.0, description="Product inlet temperature (°C)")
    target_temp_c: float = Field(50.0, description="Product target outlet temperature (°C)")
    heating_type: str = Field("steam_jacket", description="steam_jacket | electric | hot_air")
    # Steam jacket parameters
    steam_pressure_bar: float = Field(3.0, gt=0, description="Steam pressure (bar g)")
    U_W_m2K: float = Field(50.0, gt=0, description="Overall heat transfer coeff (W/m²·K)")


class DryerResult(BaseModel):
    # Evaporation
    water_removed_kg_h: float
    evaporation_rate_kg_m2h: float
    # Heat loads
    Q_evap_kW: float       # Heat for evaporation
    Q_sensible_kW: float   # Sensible heating of product
    Q_total_kW: float      # Total heat duty
    Q_losses_kW: float     # Estimated 15% shell losses
    # Heat transfer area
    heat_transfer_area_m2: float
    NTU: float             # Number of Transfer Units
    required_length_m: float
    length_ok: bool
    # Drive
    P_drive_kW: float
    motor_kW: float
    # Steam
    steam_consumption_kg_h: Optional[float]
    steam_temp_c: float
    # Residence
    residence_time_min: float
    warnings: list[str]


def calculate_dryer(inp: DryerInput) -> DryerResult:
    warnings = []

    # Latent heat of water vaporization at operating temperature
    T_avg = (inp.inlet_temp_c + inp.trough_temp_c) / 2.0
    lambda_w = (2501 - 2.42 * T_avg) * 1000  # J/kg (Antoine approximation)

    # Moisture balance
    Fin = inp.feed_rate_t_h * 1000.0  # kg/h dry+wet feed
    # Dry mass flow
    M_dry = Fin * (1 - inp.moisture_in_pct / 100.0)
    # Water in and out
    W_in  = Fin * (inp.moisture_in_pct / 100.0)
    W_out = M_dry * (inp.moisture_out_pct / 100.0) / (1 - inp.moisture_out_pct / 100.0)
    W_evap = max(0.0, W_in - W_out)  # kg/h

    if W_evap <= 0:
        warnings.append("Outlet moisture ≥ inlet moisture — no drying required.")

    # Heat duties
    Q_evap_kW = W_evap * lambda_w / 3.6e6        # kW
    Cp_material = 1800.0  # J/(kg·K) typical dry bulk
    Q_sensible_kW = Fin * Cp_material * (inp.target_temp_c - inp.inlet_temp_c) / 3.6e6  # kW
    Q_losses_kW = (Q_evap_kW + Q_sensible_kW) * 0.15
    Q_total_kW  = Q_evap_kW + Q_sensible_kW + Q_losses_kW

    # Heat transfer area required
    LMTD = _lmtd(
        T_hot_in=inp.trough_temp_c,
        T_hot_out=inp.trough_temp_c,    # steam condenses isothermally
        T_cold_in=inp.inlet_temp_c,
        T_cold_out=inp.target_temp_c
    )
    if LMTD < 1:
        LMTD = 1.0

    A_required = (Q_total_kW * 1000.0) / (inp.U_W_m2K * LMTD)  # m²
    # Available heat transfer area (inner trough perimeter × length)
    A_available_per_m = math.pi * inp.diameter_m * 0.75  # U-trough ~75% of full perim
    required_length = A_required / A_available_per_m
    A_available = A_available_per_m * inp.length_m
    length_ok = A_available >= A_required

    if not length_ok:
        warnings.append(f"Heat transfer area {A_available:.1f} m² < required {A_required:.1f} m². "
                       f"Increase length to ≥ {required_length:.1f} m.")

    evap_rate = W_evap / max(A_available, 0.01)   # kg/(m²·h)
    if evap_rate > 15.0:
        warnings.append(f"Evaporation rate {evap_rate:.1f} kg/(m²·h) > 15 — consider multiple passes.")

    # NTU (Number of Transfer Units)
    NTU = inp.U_W_m2K * A_available / (Fin * Cp_material / 3600.0) if Fin > 0 else 0

    # Residence time
    D, L, N = inp.diameter_m, inp.length_m, inp.speed_rpm
    Qv = (math.pi / 4) * D**2 * D * N * inp.fill_fraction * 60.0  # m³/h (pitch = D)
    res_min = (((math.pi / 4) * D**2 * L * inp.fill_fraction) / (Qv / 60.0)) if Qv > 0 else 0

    # Drive power (low speed, mainly empty + product friction)
    P_drive = 0.06 * N * math.sqrt(D) * L / 1000.0  # approximate
    motor_kW = _next_motor(P_drive)

    # Steam
    h_fg = lambda_w  # J/kg (approx. same as latent heat at pressure)
    steam_cons = (Q_total_kW * 3600.0 * 1000.0) / h_fg  # kg/h
    T_steam = 100.0 + (inp.steam_pressure_bar - 1) * 28.0  # approx sat. temp °C

    if inp.trough_temp_c > 120 and "grain" in inp.material.lower():
        warnings.append("Trough temperature >120°C may damage grain quality.")
    if inp.moisture_out_pct < 10:
        warnings.append("Very low target moisture may cause product degradation or dust explosion risk.")

    return DryerResult(
        water_removed_kg_h=round(W_evap, 2),
        evaporation_rate_kg_m2h=round(evap_rate, 3),
        Q_evap_kW=round(Q_evap_kW, 3),
        Q_sensible_kW=round(Q_sensible_kW, 3),
        Q_total_kW=round(Q_total_kW, 3),
        Q_losses_kW=round(Q_losses_kW, 3),
        heat_transfer_area_m2=round(A_available, 2),
        NTU=round(NTU, 3),
        required_length_m=round(required_length, 2),
        length_ok=length_ok,
        P_drive_kW=round(P_drive, 3),
        motor_kW=motor_kW,
        steam_consumption_kg_h=round(steam_cons, 1) if inp.heating_type == "steam_jacket" else None,
        steam_temp_c=round(T_steam, 1),
        residence_time_min=round(res_min, 2),
        warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. COOLER
# ─────────────────────────────────────────────────────────────────────────────

class CoolerInput(BaseModel):
    diameter_m: float = Field(0.3, gt=0)
    length_m: float = Field(6.0, gt=0)
    speed_rpm: float = Field(8.0, gt=0)
    material: str = "Clinker"
    bulk_density_t_m3: float = Field(1.5, gt=0)
    feed_rate_t_h: float = Field(20.0, gt=0)
    fill_fraction: float = Field(0.30, gt=0)
    inlet_temp_c: float = Field(200.0, description="Product inlet temperature (°C)")
    target_temp_c: float = Field(80.0, description="Target outlet temperature (°C)")
    coolant_type: str = Field("water", description="water | air")
    coolant_inlet_temp_c: float = Field(20.0)
    coolant_outlet_temp_c: float = Field(45.0)
    U_W_m2K: float = Field(80.0, description="Overall HTC water jacket (W/m²·K)")
    Cp_material_J_kgK: float = Field(900.0, description="Specific heat of product (J/kg·K)")


class CoolerResult(BaseModel):
    Q_duty_kW: float
    Q_losses_kW: float
    coolant_flow_kg_h: float
    heat_transfer_area_m2: float
    required_length_m: float
    length_ok: bool
    LMTD_K: float
    NTU: float
    effectiveness: float
    P_drive_kW: float
    motor_kW: float
    residence_time_min: float
    warnings: list[str]


def calculate_cooler(inp: CoolerInput) -> CoolerResult:
    warnings = []
    Fin_kgh = inp.feed_rate_t_h * 1000.0

    Q_duty = Fin_kgh * inp.Cp_material_J_kgK * (inp.inlet_temp_c - inp.target_temp_c) / 3.6e6  # kW
    Q_losses = Q_duty * 0.10
    Q_net = Q_duty - Q_losses   # heat extracted by coolant

    # Coolant flow
    Cp_water = 4186.0  # J/(kg·K)
    dT_coolant = max(1.0, inp.coolant_outlet_temp_c - inp.coolant_inlet_temp_c)
    coolant_flow = (Q_net * 3600.0 * 1000.0) / (Cp_water * dT_coolant)  # kg/h

    LMTD = _lmtd(
        T_hot_in=inp.inlet_temp_c, T_hot_out=inp.target_temp_c,
        T_cold_in=inp.coolant_inlet_temp_c, T_cold_out=inp.coolant_outlet_temp_c
    )
    if LMTD < 1:
        LMTD = 1.0
        warnings.append("LMTD near zero — check temperature crossover.")

    A_required = (Q_net * 1000.0) / (inp.U_W_m2K * LMTD)
    A_per_m = math.pi * inp.diameter_m * 0.75
    req_L = A_required / A_per_m
    A_avail = A_per_m * inp.length_m
    length_ok = A_avail >= A_required

    if not length_ok:
        warnings.append(f"Required length {req_L:.1f} m > available {inp.length_m} m.")

    Cm_dot = Fin_kgh * inp.Cp_material_J_kgK / 3600.0  # W/K
    NTU = (inp.U_W_m2K * A_avail) / Cm_dot if Cm_dot > 0 else 0
    effectiveness = 1 - math.exp(-NTU) if NTU >= 0 else 0

    D, L, N = inp.diameter_m, inp.length_m, inp.speed_rpm
    Qv = (math.pi / 4) * D**2 * D * N * inp.fill_fraction * 60.0
    res_min = (((math.pi / 4) * D**2 * L * inp.fill_fraction) / (Qv / 60.0)) if Qv > 0 else 0

    P_drive = 0.07 * N * math.sqrt(D) * L / 1000.0
    motor_kW = _next_motor(P_drive)

    if inp.inlet_temp_c > 300:
        warnings.append("Product temperature >300°C — use high-temperature seals and alloy construction.")

    return CoolerResult(
        Q_duty_kW=round(Q_duty, 2),
        Q_losses_kW=round(Q_losses, 2),
        coolant_flow_kg_h=round(coolant_flow, 1),
        heat_transfer_area_m2=round(A_avail, 2),
        required_length_m=round(req_L, 2),
        length_ok=length_ok,
        LMTD_K=round(LMTD, 2),
        NTU=round(NTU, 3),
        effectiveness=round(effectiveness, 4),
        P_drive_kW=round(P_drive, 3),
        motor_kW=motor_kW,
        residence_time_min=round(res_min, 2),
        warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. SEPARATOR / CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────

class SeparatorInput(BaseModel):
    diameter_m: float = Field(0.4, gt=0)
    length_m: float = Field(4.0, gt=0)
    speed_rpm: float = Field(30.0, gt=0)
    material: str = "Sand"
    bulk_density_t_m3: float = Field(1.6, gt=0)
    feed_rate_t_h: float = Field(15.0, gt=0)
    fill_fraction: float = Field(0.35, gt=0)
    # Separation parameters
    separation_type: str = Field("density", description="density | particle_size | magnetic | air_classification")
    # Density separation
    rho_A_t_m3: float = Field(1.6, description="Density of fraction A (t/m³)")
    rho_B_t_m3: float = Field(2.5, description="Density of fraction B (t/m³)")
    fraction_A_pct: float = Field(60.0, description="Feed fraction of material A (%)")
    # Particle size
    cut_size_mm: float = Field(5.0, gt=0, description="Separation cut point (mm)")
    particle_size_mm: float = Field(8.0, gt=0, description="Mean feed particle size (mm)")
    sigma_size: float = Field(2.0, gt=0, description="Std dev of particle size (mm)")
    # Variable pitch (for density separation)
    pitch_inlet_m: float = Field(0.4, description="Pitch at inlet (m)")
    pitch_outlet_m: float = Field(0.2, description="Pitch at outlet (m)")


class SeparatorResult(BaseModel):
    separation_efficiency: float   # Tromp curve efficiency 0-1
    separation_sharpness: float    # κ index (higher = sharper)
    underflow_t_h: float           # Fine / dense fraction
    overflow_t_h: float            # Coarse / light fraction
    settling_velocity_m_s: float   # Terminal settling velocity of cut particle
    residence_time_s: float
    P_drive_kW: float
    motor_kW: float
    recommendations: list[str]
    warnings: list[str]


def calculate_separator(inp: SeparatorInput) -> SeparatorResult:
    warnings = []
    recommendations = []

    D = inp.diameter_m
    L = inp.length_m
    N = inp.speed_rpm

    # Residence time
    pitch_avg = (inp.pitch_inlet_m + inp.pitch_outlet_m) / 2.0
    Qv = (math.pi / 4) * D**2 * pitch_avg * N * inp.fill_fraction * 60.0
    fill_vol = (math.pi / 4) * D**2 * L * inp.fill_fraction
    res_s = fill_vol / (Qv / 3600.0) if Qv > 0 else 0

    # Terminal settling velocity (Stokes for small particles, drag for larger)
    d_p = inp.cut_size_mm / 1000.0
    rho_fluid = 1.2  # air, kg/m³
    rho_particle = inp.rho_B_t_m3 * 1000.0
    mu = 1.8e-5  # air dynamic viscosity Pa·s
    v_t = _terminal_velocity(d_p, rho_particle, rho_fluid, mu)

    if inp.separation_type == "density":
        # Stratification efficiency based on density difference and residence time
        delta_rho = abs(inp.rho_B_t_m3 - inp.rho_A_t_m3)
        sep_eff = min(0.95, 0.30 * math.log1p(delta_rho * res_s / 100.0))
        sharpness = delta_rho * 2.0

        if delta_rho < 0.3:
            warnings.append(f"Density difference {delta_rho:.2f} t/m³ is low — separation will be poor.")
            recommendations.append("Consider adding vibration or air classification.")

    elif inp.separation_type == "particle_size":
        # Tromp function: logistic curve centered at cut_size
        z = (inp.particle_size_mm - inp.cut_size_mm) / inp.sigma_size
        sep_eff = 1.0 / (1.0 + math.exp(-1.5 * z))
        sharpness = 4.0 / inp.sigma_size  # sharper with tighter distribution
        recommendations.append(f"Install {inp.cut_size_mm:.1f} mm screen/wedge bars in the discharge zone.")

    elif inp.separation_type == "magnetic":
        sep_eff = 0.90  # typical for ferrous particles
        sharpness = 5.0
        recommendations.append("Install rare-earth drum magnets at 2× discharge points along the screw.")

    elif inp.separation_type == "air_classification":
        # Light fraction carried by airstream
        v_air = 3.0  # m/s design air velocity
        sep_eff = min(0.90, v_t / (v_air + 1e-6))
        sharpness = 2.0
        recommendations.append(f"Terminal velocity of cut particle: {v_t:.3f} m/s — size air velocity accordingly.")

    else:
        sep_eff = 0.5
        sharpness = 1.0

    underflow = inp.feed_rate_t_h * (inp.fraction_A_pct / 100.0) * sep_eff
    overflow  = inp.feed_rate_t_h - underflow

    if sep_eff < 0.70:
        warnings.append(f"Separation efficiency {sep_eff:.1%} < 70% — multi-stage separation recommended.")

    if N > 60:
        warnings.append("High RPM reduces stratification time — lower speed improves separation.")
        recommendations.append("Reduce speed to 15-30 RPM for better separation.")

    P_drive = 0.05 * N * math.sqrt(D) * L / 1000.0 * inp.fill_fraction / 0.3
    motor_kW = _next_motor(P_drive)

    return SeparatorResult(
        separation_efficiency=round(sep_eff, 4),
        separation_sharpness=round(sharpness, 3),
        underflow_t_h=round(underflow, 3),
        overflow_t_h=round(overflow, 3),
        settling_velocity_m_s=round(v_t, 5),
        residence_time_s=round(res_s, 1),
        P_drive_kW=round(P_drive, 3),
        motor_kW=motor_kW,
        recommendations=recommendations,
        warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. REACTOR (Chemical / Thermal Residence)
# ─────────────────────────────────────────────────────────────────────────────

class ReactorInput(BaseModel):
    diameter_m: float = Field(0.3, gt=0)
    length_m: float = Field(8.0, gt=0)
    speed_rpm: float = Field(3.0, gt=0, description="Very low speed for max residence time")
    material: str = "Fly Ash"
    bulk_density_t_m3: float = Field(0.9, gt=0)
    feed_rate_t_h: float = Field(5.0, gt=0)
    fill_fraction: float = Field(0.50, gt=0)
    # Reaction
    required_residence_min: float = Field(15.0, gt=0, description="Process-specified residence time (min)")
    reaction_type: str = Field("thermal", description="thermal | chemical | biological | calcination")
    process_temp_c: float = Field(150.0, description="Required process temperature (°C)")
    inlet_temp_c: float = Field(20.0)
    # Heat
    heat_flux_kW_m2: float = Field(5.0, description="Applied heat flux to trough wall (kW/m²)")
    Cp_J_kgK: float = Field(1000.0, description="Specific heat of product (J/kg·K)")


class ReactorResult(BaseModel):
    actual_residence_min: float
    residence_ok: float
    required_length_m: float
    length_ok: bool
    # Thermal
    Q_process_kW: float
    trough_area_m2: float
    achievable_temp_rise_c: float
    # Conversion estimate
    conversion_pct: float  # first-order Damköhler estimate
    Damkohler_number: float
    P_drive_kW: float
    motor_kW: float
    warnings: list[str]


def calculate_reactor(inp: ReactorInput) -> ReactorResult:
    warnings = []
    D, L, N = inp.diameter_m, inp.length_m, inp.speed_rpm
    Fin_kgh = inp.feed_rate_t_h * 1000.0

    pitch = D  # standard pitch
    Qv = (math.pi / 4) * D**2 * pitch * N * inp.fill_fraction * 60.0
    fill_vol = (math.pi / 4) * D**2 * L * inp.fill_fraction
    actual_res_s = fill_vol / (Qv / 3600.0) if Qv > 0 else 0
    actual_res_min = actual_res_s / 60.0

    required_res_s = inp.required_residence_min * 60.0
    required_length = L * required_res_s / max(actual_res_s, 1e-3)
    length_ok = actual_res_min >= inp.required_residence_min

    if not length_ok:
        warnings.append(
            f"Actual residence {actual_res_min:.1f} min < required {inp.required_residence_min} min. "
            f"Increase length to {required_length:.1f} m or reduce speed."
        )

    trough_area = math.pi * D * L * 0.75
    Q_process = (Fin_kgh * inp.Cp_J_kgK * (inp.process_temp_c - inp.inlet_temp_c)) / 3.6e6  # kW
    Q_available = inp.heat_flux_kW_m2 * trough_area
    achievable_dT = (Q_available * 3.6e6) / (Fin_kgh * inp.Cp_J_kgK)

    # Damköhler number (first-order reaction, τ × k_r)
    # Assume k_r ~ 0.01 - 0.1 s⁻¹ typical for thermal processes
    k_r_typical = {"thermal": 0.005, "chemical": 0.02, "biological": 0.001, "calcination": 0.008}.get(inp.reaction_type, 0.005)
    Da = k_r_typical * actual_res_s
    conversion = (1.0 - math.exp(-Da)) * 100.0

    P_drive = 0.04 * N * math.sqrt(D) * L / 1000.0
    motor_kW = _next_motor(P_drive)

    if inp.process_temp_c > 250:
        warnings.append("High process temperature >250°C — use refractory lining and high-temp seals.")
    if actual_res_min > 60:
        warnings.append("Very long residence time — consider multiple parallel units.")

    return ReactorResult(
        actual_residence_min=round(actual_res_min, 2),
        residence_ok=round(actual_res_min, 2),
        required_length_m=round(required_length, 2),
        length_ok=length_ok,
        Q_process_kW=round(Q_process, 2),
        trough_area_m2=round(trough_area, 3),
        achievable_temp_rise_c=round(achievable_dT, 1),
        conversion_pct=round(conversion, 2),
        Damkohler_number=round(Da, 4),
        P_drive_kW=round(P_drive, 3),
        motor_kW=motor_kW,
        warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. COMPACTOR / LIVE-BOTTOM FEEDER
# ─────────────────────────────────────────────────────────────────────────────

class CompactorInput(BaseModel):
    diameter_m: float = Field(0.3, gt=0)
    length_m: float = Field(2.0, gt=0)
    speed_rpm: float = Field(20.0, gt=0)
    material: str = "Fly Ash"
    bulk_density_t_m3: float = Field(0.9, gt=0)
    loose_density_t_m3: float = Field(0.55, gt=0)
    target_density_t_m3: float = Field(0.85, gt=0)
    compression_ratio: float = Field(1.5, ge=1.0, le=5.0)
    feed_rate_t_h: float = Field(8.0, gt=0)
    fill_fraction: float = Field(0.60, gt=0)


class CompactorResult(BaseModel):
    compression_achieved: float
    density_ratio: float
    P_compaction_kW: float
    P_total_kW: float
    motor_kW: float
    back_pressure_kPa: float
    tip_force_N: float
    warnings: list[str]


def calculate_compactor(inp: CompactorInput) -> CompactorResult:
    warnings = []
    D = inp.diameter_m
    N = inp.speed_rpm

    # Compression pressure estimation
    delta_rho = inp.target_density_t_m3 - inp.loose_density_t_m3
    compression_ratio_achieved = inp.target_density_t_m3 / max(inp.loose_density_t_m3, 0.01)

    # Back pressure from compaction (simplified Janssen-type)
    k_fric = 0.4  # lateral pressure ratio
    back_pressure = delta_rho * 1000 * 9.81 * inp.length_m * k_fric  # Pa → kPa
    back_pressure_kPa = back_pressure / 1000.0

    # Tip force on flight
    tip_force = back_pressure * (math.pi / 4) * D**2  # N

    # Compaction power
    Qv = (math.pi / 4) * D**2 * D * N * inp.fill_fraction * 60.0  # m³/h
    P_compact = back_pressure * Qv / 3.6e6  # kW
    P_total = P_compact * 1.3  # friction

    motor_kW = _next_motor(P_total)

    if compression_ratio_achieved > 2.5:
        warnings.append("High compression ratio — risk of plugging. Reduce length or add pressure relief.")
    if tip_force > 50000:
        warnings.append(f"Tip force {tip_force:.0f} N is high — ensure adequate shaft and flight strength.")

    return CompactorResult(
        compression_achieved=round(compression_ratio_achieved, 3),
        density_ratio=round(compression_ratio_achieved, 3),
        P_compaction_kW=round(P_compact, 3),
        P_total_kW=round(P_total, 3),
        motor_kW=motor_kW,
        back_pressure_kPa=round(back_pressure_kPa, 2),
        tip_force_N=round(tip_force, 0),
        warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_MOTOR_SIZES = [0.37,0.55,0.75,1.1,1.5,2.2,3.0,4.0,5.5,7.5,11,15,18.5,22,30,37,45,55,75,90,110,132,160,200]

def _next_motor(P_kW: float) -> float:
    for s in _MOTOR_SIZES:
        if s >= P_kW:
            return s
    return _MOTOR_SIZES[-1]


def _lmtd(T_hot_in, T_hot_out, T_cold_in, T_cold_out) -> float:
    dT1 = T_hot_in  - T_cold_out
    dT2 = T_hot_out - T_cold_in
    if abs(dT1 - dT2) < 0.01:
        return max(1.0, dT1)
    if dT1 <= 0 or dT2 <= 0:
        return max(abs(dT1), abs(dT2), 1.0)
    return (dT1 - dT2) / math.log(dT1 / dT2)


def _terminal_velocity(d_p: float, rho_p: float, rho_f: float, mu: float) -> float:
    """Iterative Haider-Levenspiel terminal velocity for spheres."""
    g = 9.81
    Ar = d_p**3 * rho_f * (rho_p - rho_f) * g / mu**2
    if Ar <= 0:
        return 0.0
    if Ar < 36.0:   # Stokes regime
        return (rho_p - rho_f) * g * d_p**2 / (18.0 * mu)
    elif Ar < 83000:  # Intermediate
        return mu / (rho_f * d_p) * (14.42 + 1.827 * math.sqrt(Ar) - 3.798)**0.5
    else:  # Newton regime
        return math.sqrt(3.1 * d_p * (rho_p - rho_f) * g / rho_f)
