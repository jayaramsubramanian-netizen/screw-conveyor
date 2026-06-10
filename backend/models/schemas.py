"""
Pydantic schemas — request/response shapes for all API endpoints.
Field names mirror the JS database schema exactly.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator


# ═══════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class EngineInput(BaseModel):
    """All inputs required by calc_engine(). Matches JS DEF object."""
    # Conveyor geometry
    type:           Literal["screw", "pipe"] = "screw"
    D:              float = Field(0.3,  ge=0.05, le=1.2,   description="Trough/pipe diameter [m]")
    L:              float = Field(10.0, ge=0.5,  le=100.0, description="Conveyor length [m]")
    N:              float = Field(60.0, ge=5.0,  le=300.0, description="Speed [RPM]")
    P:              float = Field(0.3,  ge=0.05, le=2.0,   description="Body pitch [m]")
    ang:            float = Field(0.0,  ge=-20,  le=45,    description="Inclination angle [°]")

    # Process
    mat:            str   = Field("Cement", description="Material name (must exist in DB)")
    cap:            float = Field(30.0, ge=0.01, le=5000,  description="Required capacity [t/h]")
    surge:          float = Field(1.2,  ge=1.0,  le=2.0,   description="Surge factor")

    # Multi-pitch
    use_multipitch: bool  = False
    P_in:           Optional[float] = None
    P_out:          Optional[float] = None
    pct_in:         float = 10.0
    pct_out:        float = 10.0

    # Shaft
    shaft_mode:     Literal["auto", "manual"] = "auto"
    shtype:         Literal["bar", "pipe"]    = "bar"
    pod:            float = 80.0
    pwall:          float = 8.0
    sallow:         float = 40.0
    prefer_pipe:    bool  = False
    support_cond:   Literal["pinfix", "pinned", "fixed"] = "pinfix"

    # Flight wear
    ft:             float = 0.008
    wa:             float = 0.003
    temp_c:         float = 20.0

    # Drive
    brg:            str   = "UC210"
    gbx:            str   = "GB-40k"
    bload:          Optional[float] = None
    hangers:        Optional[int]   = None
    duty:           int   = Field(8, ge=1, le=24)

    # Misc
    contAFact:      bool  = False

    lam_factor: float = 1.0    # standards multiplier: CEMA=1.00, DIN=1.01, Custom=user

    class Config:
        extra = "allow"   # forward-compatible with future fields


class AxialProfileInput(BaseModel):
    inp: EngineInput
    segments: int = Field(60, ge=10, le=200)


class FamilyInput(BaseModel):
    mat:    str   = "Cement"
    ang:    float = 0.0
    surge:  float = 1.2
    cap:    float = 30.0
    L:      float = 10.0
    Ds:     List[float] = [0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    Ls:     List[float] = [5, 10, 15, 20, 25, 30]


class MaterialFilter(BaseModel):
    search:      Optional[str]  = None
    category:    Optional[str]  = None
    abr:         Optional[str]  = None
    flowability: Optional[int]  = None
    cls:         Optional[str]  = None
    app:         Optional[str]  = None


# ═══════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class MaterialOut(BaseModel):
    id:             int
    name:           str
    category:       Optional[str]
    rho:            float
    rho_min:        Optional[float]
    rho_max:        Optional[float]
    lambda_ref:     Optional[float]
    fill_max:       float
    abr:            str
    cls:            str
    particle_class: Optional[str]
    flowability:    Optional[int]
    moist:          float
    aor:            Optional[float]
    cohesion:       Optional[float]
    temp_max:       Optional[float]
    bridging_risk:  Optional[float]
    flow_regime:    Optional[str]
    confidence:     Optional[float]
    source:         Optional[str]
    note:           Optional[str]
    cema_code:      Optional[str]
    flags:          Optional[str]
    app:            Optional[List[str]]
    custom:         bool = False

    class Config:
        from_attributes = True


class BearingOut(BaseModel):
    id:         int
    name:       str
    mfr:        Optional[str]
    type:       Optional[str]
    bore:       Optional[float]
    C:          Optional[float]
    C0:         Optional[float]
    p:          Optional[float]
    speed_g:    Optional[int]
    seal:       Optional[str]
    role:       Optional[str]
    mass_kg:    Optional[float]
    note:       Optional[str]

    class Config:
        from_attributes = True


class GearboxOut(BaseModel):
    id:         int
    model:      str
    type:       Optional[str]
    stages:     Optional[int]
    Tn:         float
    Pkw:        float
    ratio_min:  Optional[float]
    ratio_max:  Optional[float]
    eta:        Optional[float]
    mount:      Optional[str]
    ip:         Optional[str]
    mass_kg:    Optional[float]
    note:       Optional[str]

    class Config:
        from_attributes = True


class CapResult(BaseModel):
    Qt:                 float
    Qv:                 float
    Qt_raw:             float
    Qt_body:            float
    Qt_inlet:           float
    Qt_outlet:          float
    Qt_governing:       float
    fill:               float
    fill_actual:        float
    feed_ratio:         float
    eta_L:              float
    pipe_transport_derate: float
    ok:                 bool
    req:                float
    lam_used:           float


class PowerResult(BaseModel):
    Pe:             float
    Pm:             float
    Pi:             float
    Pf:             float
    Pf_factor:      float
    Ps_ideal:       float
    Ps:             float
    Pt:             float
    motor:          float
    motor_rated:    float
    motor_SF:       float


class TorqueResult(BaseModel):
    Tr:         float
    Tr_max:     float
    Ts:         float
    od:         float
    tau:        float
    tau_run:    float
    shOk:       bool
    eff_od_mm:  float
    I_m4:       float
    A_m2:       float


class WearResult(BaseModel):
    v_tip:          float
    P_contact_kPa:  float
    P_factor:       float
    wrate_mm_h:     float
    wc:             float
    thick_mm:       float
    life_h:         float
    life_t:         float


class EffResult(BaseModel):
    fill_pct:   float
    cap_util:   float
    kWh_t:      float
    sug_geom:   Dict[str, Any]


class EngineResult(BaseModel):
    D:              float
    L:              float
    N:              float
    ang:            float
    is_pipe:        bool
    P_eff:          float
    cap:            CapResult
    pwr:            PowerResult
    tor:            TorqueResult
    wear:           WearResult
    eff:            EffResult
    brg_r:          Dict[str, Any]
    hgr:            Dict[str, Any]
    gbx_r:          Dict[str, Any]
    deflection:     float
    defl_limit:     float
    deflection_ok:  bool
    nc:             float
    nc_ratio:       float
    vibration_risk: float
    vri_label:      str
    regime:         Dict[str, str]
    # computed material properties (not raw DB row)
    mat_props:      Optional[Dict[str, Any]] = None


class AxialSegment(BaseModel):
    x:              float
    fill_pct:       float
    Qt:             float
    Qt_cap:         float
    pwr_density:    float
    torque_pm:      float
    torque_cumul:   float
    wear_rate:      float
    axial_velocity: float
    localAng:       float
    localPitch:     float
    status:         str
    isHanger:       bool


class AxialProfileResult(BaseModel):
    segments: List[AxialSegment]


class FamilyPoint(BaseModel):
    Dmm:        float
    L:          float
    N:          float
    cap:        float
    cap_ok:     bool
    pwr:        float
    motor:      float
    tor:        float
    shaft_mm:   float
    hgr:        int
    L10:        float
    kWh:        float
    cost:       float
    score:      float


class FamilyResult(BaseModel):
    pts: List[FamilyPoint]


class HealthResponse(BaseModel):
    status:   str
    db_mats:  int
    db_brgs:  int
    db_gbxs:  int
    version:  str = "2.5.0"


class MotorOut(BaseModel):
    id:          int
    model:       str
    frame:       Optional[str]
    Pkw:         Optional[float]
    poles:       Optional[int]
    rpm_50hz:    Optional[float]
    efficiency:  Optional[float]
    ie_class:    Optional[str]
    ip:          Optional[str]
    mass_kg:     Optional[float]
    custom:      bool = False
    note:        Optional[str]

    class Config:
        from_attributes = True


class DriveOut(BaseModel):
    id:           int
    model:        str
    type:         Optional[str]
    Pkw_max:      Optional[float]
    Vrated:       Optional[float]
    Irated:       Optional[float]
    overload_pct: Optional[float]
    control:      Optional[str]
    ip:           Optional[str]
    features:     Optional[str]
    custom:       bool = False
    note:         Optional[str]

    class Config:
        from_attributes = True


class CostItemOut(BaseModel):
    id:             int
    item:           str
    usd:            float
    description:    Optional[str]
    material_group: Optional[str]
    custom:         bool = False
    note:           Optional[str]

    class Config:
        from_attributes = True
