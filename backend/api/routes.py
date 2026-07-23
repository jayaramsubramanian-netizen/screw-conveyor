"""
FastAPI route definitions.
All heavy physics stays in core/engine.py — routes only handle
HTTP, DB lookup, and response shaping.

Pylance fixes applied in this pass:
  - axial_profile(): build_axial_profile() returns list[dict]; each dict
    is now converted into an AxialSegment instance before being handed
    to AxialProfileResult(segments=...), which expects List[AxialSegment].
  - All `if not X.custom:` conditionals wrapped in bool(getattr(...))
    since SQLAlchemy's declarative Column[bool] class-level type makes
    Pylance treat instance-level truthiness as invalid (Column.__bool__
    raises at the class-definition level even though instance access
    returns a real bool at runtime). This is a static-analysis false
    positive, not a runtime bug — the wrapper changes nothing at runtime.
  - All `obj.custom = True` assignments changed to
    setattr(obj, "custom", True) for the same reason — direct attribute
    assignment against a Column-typed class attribute trips
    reportAttributeAccessIssue even though it's a normal ORM instance
    write at runtime.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import math

from ..db.database import get_db
from ..models.tables import Material, Bearing, Gearbox, Motor, Drive, CostItem
from ..models.schemas import (
    EngineInput, EngineResult, AxialProfileInput, AxialProfileResult,
    FamilyInput, FamilyResult, FamilyPoint,
    MaterialOut, BearingOut, GearboxOut,
    HealthResponse, AxialSegment,
    MotorOut, DriveOut, CostItemOut,
)
from ..core.engine import calc_engine, calc_fill, calc_lambda, calc_ks, calc_wc, psz_of, a_fact, calc_structural

router = APIRouter()


# ── HELPERS ────────────────────────────────────────────────────────
def mat_to_dict(m: Material) -> dict:
    """Convert ORM Material row to dict for engine consumption."""
    return {k: getattr(m, k) for k in [
        "name","category","rho","rho_min","rho_max","lambda_ref","fill_max",
        "abr","cls","particle_class","flowability","moist","aor","cohesion",
        "temp_max","bridging_risk","flow_regime","confidence","source",
        "note","cema_code","flags","app",
    ]}


def get_mat(name: str, db: Session) -> dict:
    m = db.query(Material).filter(Material.name == name).first()
    if not m:
        # Fall back to first available material instead of crashing
        m = db.query(Material).order_by(Material.name).first()
    if not m:
        raise HTTPException(503, "No materials in database. Run: python -m backend.db.seed")
    return mat_to_dict(m)


def get_brg(name: str, db: Session) -> dict:
    b = db.query(Bearing).filter(Bearing.name == name).first()
    if not b:
        # fallback to first bearing matching minimum bore
        b = db.query(Bearing).order_by(Bearing.bore).first()
    return {k: getattr(b, k) for k in ["name","C","C0","p","bore","speed_g","seal","role"]}


def get_gbx(model: str, db: Session) -> dict:
    g = db.query(Gearbox).filter(Gearbox.model == model).first()
    if not g:
        g = db.query(Gearbox).order_by(Gearbox.Tn).first()
    return {k: getattr(g, k) for k in ["model","Tn","Pkw","type","eta","ratio_min","ratio_max"]}


# ═══════════════════════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════════════════════
@router.get("/health", response_model=HealthResponse, tags=["System"])
def health(db: Session = Depends(get_db)):
    """API health check + DB row counts."""
    return HealthResponse(
        status   = "ok",
        db_mats  = db.query(Material).count(),
        db_brgs  = db.query(Bearing).count(),
        db_gbxs  = db.query(Gearbox).count(),
    )


# ═══════════════════════════════════════════════════════════════════
# CALCULATE — main engine endpoint
# ═══════════════════════════════════════════════════════════════════
@router.post("/calculate", tags=["Engine"])
def calculate(payload: EngineInput, db: Session = Depends(get_db)):
    """
    Run the full screw conveyor sizing engine.
    Returns capacity, power, shaft, bearing, wear, efficiency results.
    """
    mat = get_mat(payload.mat, db)
    brg = get_brg(payload.brg, db)
    gbx = get_gbx(payload.gbx, db)
    inp = payload.model_dump()

    result = calc_engine(inp, mat, brg, gbx, lam_factor=payload.lam_factor)

    # Add computed mat properties for display (not raw DB fields)
    result["mat_props"] = {
        "lam":      calc_lambda(mat),
        "fill_max": mat["fill_max"],
        "Ks":       calc_ks(mat),
        "wc":       calc_wc(mat),
        "psz":      psz_of(mat),
    }

    # Structural sizing. Ported from calcStructural() in CalcPage.tsx, which
    # ran client-side — this is now backend-authoritative (see engine.py and
    # STRUCTURAL_REVIEW_NOTE.md option 1). The .tsx called it with
    #   fill = R.cap?.fill_actual || R.cap?.fill || 0.30
    # so fill is read from the cap block with the same 0.30 fallback, keeping
    # the structural pass consistent with the capacity result.
    cap = result.get("cap", {})
    fill_struct = cap.get("fill_actual") or cap.get("fill") or 0.30
    result["structural"] = calc_structural(
        inp["D"], inp["L"],
        mat.get("rho", 1.2), inp.get("ang", 0) or 0,
        fill_struct, mat.get("abr", "Medium"), inp.get("temp_c", 20) or 20,
    )
    return result


# ═══════════════════════════════════════════════════════════════════
# AXIAL PROFILE
# ═══════════════════════════════════════════════════════════════════
@router.post("/axial-profile", response_model=AxialProfileResult, tags=["Engine"])
def axial_profile(payload: AxialProfileInput, db: Session = Depends(get_db)):
    """
    Build axial profile (fill, power, torque, wear at each x position).
    Used by the profile chart component.
    """
    inp = payload.inp.model_dump()
    mat = get_mat(payload.inp.mat, db)
    brg = get_brg(payload.inp.brg, db)
    gbx = get_gbx(payload.inp.gbx, db)

    # Run engine first to get R (needed for hgr span etc)
    R = calc_engine(inp, mat, brg, gbx, db=db)

    from ..core.axial import build_axial_profile
    raw_segments = build_axial_profile(inp, R, mat, payload.segments)

    # build_axial_profile() returns plain dicts; AxialProfileResult
    # requires List[AxialSegment], so convert each entry explicitly
    # rather than relying on FastAPI's response_model coercion alone.
    segments = [
        s if isinstance(s, AxialSegment) else AxialSegment(**s)
        for s in raw_segments
    ]
    return AxialProfileResult(segments=segments)


# ═══════════════════════════════════════════════════════════════════
# FAMILY DESIGNER
# ═══════════════════════════════════════════════════════════════════
@router.post("/family", response_model=FamilyResult, tags=["Engine"])
def family(payload: FamilyInput, db: Session = Depends(get_db)):
    """
    Generate family of designs (D × L combinations) for a material.
    """
    mat = get_mat(payload.mat, db)
    pts = []

    MOTOR_SZ = [0.37,0.55,0.75,1.1,1.5,2.2,3,4,5.5,7.5,11,15,18.5,22,30,37,45,55,75,90]

    for Dmm_raw in payload.Ds:
        # Accept mm values (frontend sends 150,200,...) or m values
        Dmm = Dmm_raw if Dmm_raw >= 10 else Dmm_raw * 1000  # normalise to mm
        D = Dmm / 1000
        max_v = 2.0 if (calc_wc(mat) > 2) else 3.0 if calc_wc(mat) > 1 else 4.0
        Ns = [n for n in [20,30,40,50,60,80,100,120] if math.pi*D*n/60 <= max_v]

        for L in payload.Ls:
            for N in Ns:
                try:
                    brg_row = db.query(Bearing).filter(Bearing.bore >= D * 200 * 0.18).order_by(Bearing.bore).first()
                    gbx_row = db.query(Gearbox).order_by(Gearbox.Tn).first()
                    brg = {k: getattr(brg_row, k) for k in ["name","C","C0","p","bore"]}
                    gbx = {k: getattr(gbx_row, k) for k in ["model","Tn","Pkw","type"]}

                    inp = {
                        "D": D, "L": L, "N": N, "P": D,
                        "ang": payload.ang, "cap": payload.cap,
                        "surge": payload.surge, "mat": payload.mat,
                        "type": "screw", "sallow": 40, "duty": 8,
                        "ft": 0.008, "wa": 0.003,
                        "hangers": None, "use_multipitch": False,
                        "bload": max(1, mat["rho"] * D * D * L * 9.81 / 1000),
                    }
                    R = calc_engine(inp, mat, brg, gbx, db=db)

                    # Score: penalise oversizing, reward efficiency
                    util = R["eff"]["cap_util"]
                    score = max(0, 100 - abs(util - 85) * 0.8 - R["eff"]["kWh_t"] * 10)

                    pts.append(FamilyPoint(
                        Dmm     = Dmm,
                        L       = L,
                        N       = N,
                        cap     = R["cap"]["Qt"],
                        cap_ok  = R["cap"]["ok"],
                        pwr     = R["pwr"]["Pt"],
                        motor   = R["pwr"]["motor"],
                        tor     = R["tor"]["Tr"],
                        shaft_mm= R["shaft_auto"]["sel_mm"],
                        hgr     = R["hgr"]["count"],
                        L10     = R["brg_r"]["L10"],
                        kWh     = R["eff"]["kWh_t"],
                        cost    = float(R.get("cost", {}).get("total", D * 1200 * L + N * 5)),
                        score   = score,
                    ))
                except Exception:
                    continue

    pts.sort(key=lambda p: (not p.cap_ok, p.kWh))
    return FamilyResult(pts=pts)


# ═══════════════════════════════════════════════════════════════════
# MATERIALS
# ═══════════════════════════════════════════════════════════════════
@router.get("/materials", response_model=List[MaterialOut], tags=["Database"])
def list_materials(
    search:      Optional[str] = None,
    category:    Optional[str] = None,
    abr:         Optional[str] = None,
    flowability: Optional[int] = None,
    cls:         Optional[str] = None,
    limit:       int = Query(500, le=1000),
    offset:      int = 0,
    db: Session = Depends(get_db),
):
    """List materials with optional filters."""
    q = db.query(Material)
    if search:
        q = q.filter(Material.name.ilike(f"%{search}%"))
    if category:
        q = q.filter(Material.category == category)
    if abr:
        q = q.filter(Material.abr == abr)
    if flowability:
        q = q.filter(Material.flowability == flowability)
    if cls:
        q = q.filter(Material.cls == cls)
    return q.offset(offset).limit(limit).all()


@router.get("/materials/categories", tags=["Database"])
def material_categories(db: Session = Depends(get_db)):
    """Distinct categories for filter dropdowns."""
    from sqlalchemy import distinct
    cats = db.query(distinct(Material.category)).filter(Material.category.isnot(None)).all()
    return sorted([c[0] for c in cats])


@router.get("/materials/{name}", response_model=MaterialOut, tags=["Database"])
def get_material(name: str, db: Session = Depends(get_db)):
    m = db.query(Material).filter(Material.name == name).first()
    if not m:
        raise HTTPException(404, f"Material '{name}' not found")
    return m


@router.post("/materials", response_model=MaterialOut, tags=["Database"])
def create_material(payload: dict, db: Session = Depends(get_db)):
    """Create a custom material."""
    existing = db.query(Material).filter(Material.name == payload.get("name")).first()
    if existing:
        raise HTTPException(409, f"Material '{payload['name']}' already exists")
    m = Material(**payload, custom=True)
    db.add(m); db.commit(); db.refresh(m)
    return m


@router.put("/materials/{name}", response_model=MaterialOut, tags=["Database"])
def update_material(name: str, payload: dict, db: Session = Depends(get_db)):
    """Update a custom material (built-in materials are read-only)."""
    m = db.query(Material).filter(Material.name == name).first()
    if not m:
        raise HTTPException(404, f"Material '{name}' not found")
    if not bool(getattr(m, "custom", False)):
        raise HTTPException(403, "Built-in CEMA materials are read-only. Create a custom copy instead.")
    for k, v in payload.items():
        if hasattr(m, k):
            setattr(m, k, v)
    db.commit(); db.refresh(m)
    return m


@router.delete("/materials/{name}", tags=["Database"])
def delete_material(name: str, db: Session = Depends(get_db)):
    m = db.query(Material).filter(Material.name == name).first()
    if not m:
        raise HTTPException(404)
    if not bool(getattr(m, "custom", False)):
        raise HTTPException(403, "Built-in CEMA materials cannot be deleted.")
    db.delete(m); db.commit()
    return {"deleted": name}


# ═══════════════════════════════════════════════════════════════════
# BEARINGS
# ═══════════════════════════════════════════════════════════════════
@router.get("/bearings", response_model=List[BearingOut], tags=["Database"])
def list_bearings(
    min_bore: Optional[float] = None,
    role:     Optional[str]   = None,
    db: Session = Depends(get_db),
):
    q = db.query(Bearing)
    if min_bore:
        q = q.filter(Bearing.bore >= min_bore)
    if role:
        q = q.filter(Bearing.role.ilike(f"%{role}%"))
    return q.order_by(Bearing.bore).all()


@router.get("/bearings/{name}", response_model=BearingOut, tags=["Database"])
def get_bearing(name: str, db: Session = Depends(get_db)):
    b = db.query(Bearing).filter(Bearing.name == name).first()
    if not b:
        raise HTTPException(404)
    return b


# ═══════════════════════════════════════════════════════════════════
# GEARBOXES
# ═══════════════════════════════════════════════════════════════════
@router.get("/gearboxes", response_model=List[GearboxOut], tags=["Database"])
def list_gearboxes(
    min_Tn:   Optional[float] = None,
    type:     Optional[str]   = None,
    db: Session = Depends(get_db),
):
    q = db.query(Gearbox)
    if min_Tn:
        q = q.filter(Gearbox.Tn >= min_Tn)
    if type:
        q = q.filter(Gearbox.type == type)
    return q.order_by(Gearbox.Tn).all()


@router.get("/gearboxes/{model}", response_model=GearboxOut, tags=["Database"])
def get_gearbox(model: str, db: Session = Depends(get_db)):
    g = db.query(Gearbox).filter(Gearbox.model == model).first()
    if not g:
        raise HTTPException(404)
    return g



# ═══════════════════════════════════════════════════════════════════
# BEARINGS — full CRUD
# ═══════════════════════════════════════════════════════════════════

@router.post("/bearings", response_model=BearingOut, tags=["Database"])
def create_bearing(payload: dict, db: Session = Depends(get_db)):
    existing = db.query(Bearing).filter(Bearing.name == payload.get("name")).first()
    if existing:
        raise HTTPException(409, f"Bearing '{payload['name']}' already exists")
    obj = Bearing(**{k: v for k, v in payload.items() if hasattr(Bearing, k)}, custom=True)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/bearings/{name}", response_model=BearingOut, tags=["Database"])
def update_bearing(name: str, payload: dict, db: Session = Depends(get_db)):
    obj = db.query(Bearing).filter(Bearing.name == name).first()
    if not obj:
        raise HTTPException(404, f"Bearing '{name}' not found")
    for k, v in payload.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    setattr(obj, "custom", True)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/bearings/{name}", tags=["Database"])
def delete_bearing(name: str, db: Session = Depends(get_db)):
    obj = db.query(Bearing).filter(Bearing.name == name).first()
    if not obj:
        raise HTTPException(404)
    if not bool(getattr(obj, "custom", False)):
        raise HTTPException(403, "Built-in bearings are read-only. Create a custom copy instead.")
    db.delete(obj); db.commit()
    return {"deleted": name}


# ═══════════════════════════════════════════════════════════════════
# GEARBOXES — full CRUD
# ═══════════════════════════════════════════════════════════════════

@router.post("/gearboxes", response_model=GearboxOut, tags=["Database"])
def create_gearbox(payload: dict, db: Session = Depends(get_db)):
    existing = db.query(Gearbox).filter(Gearbox.model == payload.get("model")).first()
    if existing:
        raise HTTPException(409, f"Gearbox '{payload['model']}' already exists")
    obj = Gearbox(**{k: v for k, v in payload.items() if hasattr(Gearbox, k)}, custom=True)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/gearboxes/{model}", response_model=GearboxOut, tags=["Database"])
def update_gearbox(model: str, payload: dict, db: Session = Depends(get_db)):
    obj = db.query(Gearbox).filter(Gearbox.model == model).first()
    if not obj:
        raise HTTPException(404, f"Gearbox '{model}' not found")
    for k, v in payload.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    setattr(obj, "custom", True)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/gearboxes/{model}", tags=["Database"])
def delete_gearbox(model: str, db: Session = Depends(get_db)):
    obj = db.query(Gearbox).filter(Gearbox.model == model).first()
    if not obj:
        raise HTTPException(404)
    if not bool(getattr(obj, "custom", False)):
        raise HTTPException(403, "Built-in gearboxes are read-only. Create a custom copy instead.")
    db.delete(obj); db.commit()
    return {"deleted": model}


# ═══════════════════════════════════════════════════════════════════
# MOTORS — full CRUD
# ═══════════════════════════════════════════════════════════════════

@router.get("/motors", response_model=List[MotorOut], tags=["Database"])
def list_motors(db: Session = Depends(get_db)):
    return [m.__dict__ for m in db.query(Motor).order_by(Motor.Pkw).all()]

@router.post("/motors", response_model=MotorOut, tags=["Database"])
def create_motor(payload: dict, db: Session = Depends(get_db)):
    existing = db.query(Motor).filter(Motor.model == payload.get("model")).first()
    if existing:
        raise HTTPException(409, f"Motor '{payload['model']}' already exists")
    obj = Motor(**{k: v for k, v in payload.items() if hasattr(Motor, k)}, custom=True)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/motors/{model}", response_model=MotorOut, tags=["Database"])
def update_motor(model: str, payload: dict, db: Session = Depends(get_db)):
    obj = db.query(Motor).filter(Motor.model == model).first()
    if not obj:
        raise HTTPException(404, f"Motor '{model}' not found")
    for k, v in payload.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    setattr(obj, "custom", True)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/motors/{model}", tags=["Database"])
def delete_motor(model: str, db: Session = Depends(get_db)):
    obj = db.query(Motor).filter(Motor.model == model).first()
    if not obj:
        raise HTTPException(404)
    if not bool(getattr(obj, "custom", False)):
        raise HTTPException(403, "Built-in motors are read-only. Create a custom copy instead.")
    db.delete(obj); db.commit()
    return {"deleted": model}


# ═══════════════════════════════════════════════════════════════════
# DRIVES — full CRUD
# ═══════════════════════════════════════════════════════════════════

@router.get("/drives", response_model=List[DriveOut], tags=["Database"])
def list_drives(db: Session = Depends(get_db)):
    return [d.__dict__ for d in db.query(Drive).order_by(Drive.Pkw_max).all()]

@router.post("/drives", response_model=DriveOut, tags=["Database"])
def create_drive(payload: dict, db: Session = Depends(get_db)):
    existing = db.query(Drive).filter(Drive.model == payload.get("model")).first()
    if existing:
        raise HTTPException(409, f"Drive '{payload['model']}' already exists")
    obj = Drive(**{k: v for k, v in payload.items() if hasattr(Drive, k)}, custom=True)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/drives/{model}", response_model=DriveOut, tags=["Database"])
def update_drive(model: str, payload: dict, db: Session = Depends(get_db)):
    obj = db.query(Drive).filter(Drive.model == model).first()
    if not obj:
        raise HTTPException(404, f"Drive '{model}' not found")
    for k, v in payload.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    setattr(obj, "custom", True)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/drives/{model}", tags=["Database"])
def delete_drive(model: str, db: Session = Depends(get_db)):
    obj = db.query(Drive).filter(Drive.model == model).first()
    if not obj:
        raise HTTPException(404)
    if not bool(getattr(obj, "custom", False)):
        raise HTTPException(403, "Built-in drives are read-only. Create a custom copy instead.")
    db.delete(obj); db.commit()
    return {"deleted": model}


# ═══════════════════════════════════════════════════════════════════
# COST ITEMS — full CRUD
# ═══════════════════════════════════════════════════════════════════

@router.get("/costs", response_model=List[CostItemOut], tags=["Database"])
def list_costs(db: Session = Depends(get_db)):
    return [c.__dict__ for c in db.query(CostItem).order_by(CostItem.item).all()]

@router.post("/costs", response_model=CostItemOut, tags=["Database"])
def create_cost(payload: dict, db: Session = Depends(get_db)):
    existing = db.query(CostItem).filter(CostItem.item == payload.get("item")).first()
    if existing:
        raise HTTPException(409, f"Cost item '{payload['item']}' already exists")
    obj = CostItem(**{k: v for k, v in payload.items() if hasattr(CostItem, k)}, custom=True)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/costs/{item}", response_model=CostItemOut, tags=["Database"])
def update_cost(item: str, payload: dict, db: Session = Depends(get_db)):
    obj = db.query(CostItem).filter(CostItem.item == item).first()
    if not obj:
        raise HTTPException(404, f"Cost item '{item}' not found")
    for k, v in payload.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    setattr(obj, "custom", True)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/costs/{item}", tags=["Database"])
def delete_cost(item: str, db: Session = Depends(get_db)):
    obj = db.query(CostItem).filter(CostItem.item == item).first()
    if not obj:
        raise HTTPException(404)
    if not bool(getattr(obj, "custom", False)):
        raise HTTPException(403, "Built-in cost items are read-only. Create a custom copy instead.")
    db.delete(obj); db.commit()
    return {"deleted": item}


# ═══════════════════════════════════════════════════════════════════
# MULTI-STANDARD CALCULATE (CEMA + DIN + Custom in one call)
# ═══════════════════════════════════════════════════════════════════

class MultiCalcResult(BaseModel):
    CEMA:   Dict[str, Any]
    DIN:    Dict[str, Any]
    Custom: Dict[str, Any]

@router.post("/calculate-multi", tags=["Engine"])
def calculate_multi(payload: EngineInput, db: Session = Depends(get_db)):
    """
    Run calculation under three standards simultaneously:
    CEMA (lam×1.00), DIN 15262 (lam×1.01), Custom (lam×payload.lam_factor).
    Returns all three results in one response.
    """
    mat = get_mat(payload.mat, db)
    brg = get_brg(payload.brg, db)
    gbx = get_gbx(payload.gbx, db)
    inp = payload.model_dump()

    standards = {
        "CEMA":   1.00,
        "DIN":    1.01,
        "Custom": payload.lam_factor,
    }
    results = {}
    for std_name, lf in standards.items():
        r = calc_engine(inp, mat, brg, gbx, lam_factor=lf)
        r["_standard"] = std_name
        r["_lam_factor"] = lf
        results[std_name] = r

    return results


# ═══════════════════════════════════════════════════════════════════
# PROCESS MODULES
# ═══════════════════════════════════════════════════════════════════
from ..core.process_engine import (
    calc_feeder,
    solve_system, calc_mixer, transport,
    classify_flow_regime, normalize_psd, default_psd, psd_metrics, get_d50,
)


@router.post("/process/dryer", tags=["Process"])
def run_dryer(payload: dict, db: Session = Depends(get_db)):
    """
    Screw dryer: LMTD heat transfer + two-phase drying kinetics.
    Inputs: diam, len, speedDry, fillDry, tIn, mIn, tTr, U, d_p, CpDry, feed, rho
    """
    result = solve_system(payload, "dryer")
    fin   = result["final"]
    tr    = result["tr"]
    hist  = result["history"]
    feed  = payload.get("feed", 5)           # t/h
    mIn   = payload.get("mIn", 18) / 100     # moisture in (fraction)
    mOut  = payload.get("mOut", 5)           # target moisture out (%)
    tTr   = payload.get("tTr", 120)
    tIn   = payload.get("tIn", 20)
    # Post-process dryer KPIs
    X_out = fin["moisture"] * 100
    m_dry = feed * (1 - mIn)
    W_ev  = max(0, feed * mIn - m_dry * fin["moisture"])         # t/h water evaporated
    lw    = (2501 - 2.42 * (tIn + tTr) / 2) * 1000              # avg latent heat J/kg
    Q_kJ  = max(fin["Q_cumul"], 0.001)
    eff   = min(1, W_ev * 1000 / 3600 * lw / max(Q_kJ * 1000, 1))
    kWh_kgWater = Q_kJ / 3600 / max(W_ev, 0.001)               # kWh per kg water
    dT1   = max(0.01, tTr - tIn)
    dT2   = max(0.01, tTr - X_out)
    LMTD  = abs(dT1 - dT2) / max(abs(import_log_ratio := (dT1 / max(dT2, 0.01))), 0.01) if abs(dT1-dT2) > 0.01 else dT1
    target_met = X_out <= mOut + 1
    return {**result, "module": "dryer",
            "mOut_actual":  round(X_out, 2),
            "kWh_kgWater":  round(kWh_kgWater, 3),
            "eff":          round(eff, 3),
            "LMTD":         round(dT1, 1),
            "target_met":   target_met,
            "Xout_target":  mOut / 100,
            "summary": {
                "T_in":          hist[0]["T"] if hist else tIn,
                "T_out":         round(fin["T"], 1),
                "moisture_in_pct":  round(mIn * 100, 1),
                "moisture_out_pct": round(X_out, 2),
                "target_pct":    mOut,
                "target_met":    target_met,
                "W_evap_tph":    round(W_ev, 3),
                "Q_total_kW":    round(Q_kJ, 2),
                "eff_thermal":   round(eff, 3),
                "kWh_per_kgWater": round(kWh_kgWater, 3),
                "t_res_s":       round(tr["t_res"], 1),
                "v_ax":          round(tr["v_ax"], 4),
            }}


@router.post("/process/cooler", tags=["Process"])
def run_cooler(payload: dict, db: Session = Depends(get_db)):
    """
    Screw cooler: NTU-effectiveness + moving-bed non-ideality.
    Inputs: diam, Lc, speedCool, fillC2, tInC, coolIn, tTgtC, U, Cp, feed, rho
    """
    result = solve_system(payload, "cooler")
    fin   = result["final"]
    tr    = result["tr"]
    hist  = result["history"]
    tIn   = payload.get("tInC", 200)
    tTgt  = payload.get("tTgtC", 80)
    coolIn= payload.get("coolIn", 20)
    feed  = payload.get("feed", 5)
    Cp    = payload.get("Cp", 900)
    U     = payload.get("U", 50)
    D     = payload.get("diam", 0.3)
    L     = payload.get("Lc", 4)
    T_out = fin["T"]
    Qd_target = feed * 1000 / 3600 * Cp * max(0, tIn - tTgt)   # W design duty
    Q_actual  = fin["Q_cumul"] * 1000                             # W actual
    target_met = T_out <= tTgt + 2
    dT_lm = max(0.01, ((tIn - coolIn) + (T_out - coolIn)) / 2)
    import math as _m
    NTU = U * (_m.pi * D * L) / max(feed * 1000 / 3600 * Cp, 1)
    eps_ideal = 1 - _m.exp(-NTU)
    eps_actual = round(min(1, Q_actual / max(Qd_target, 1)), 3)
    return {**result, "module": "cooler",
            "eps_actual":  eps_actual,
            "Q_actual_kW": round(Q_actual / 1000, 2),
            "Qd_target":   round(Qd_target / 1000, 2),
            "target_met":  target_met,
            "NTU":         round(NTU, 3),
            "summary": {
                "T_in":        tIn,
                "T_out":       round(T_out, 1),
                "target_C":    tTgt,
                "target_met":  target_met,
                "Q_actual_kW": round(Q_actual / 1000, 2),
                "Qd_target_kW":round(Qd_target / 1000, 2),
                "eps_actual":  eps_actual,
                "NTU":         round(NTU, 3),
                "t_res_s":     round(tr["t_res"], 1),
                "v_ax":        round(tr["v_ax"], 4),
            }}


@router.post("/process/reactor", tags=["Process"])
def run_reactor(payload: dict, db: Session = Depends(get_db)):
    """
    Screw reactor: Arrhenius kinetics + Damköhler + ADM correction.
    Inputs: len, Nr, fillR, tIn, feedR, rho, rxn, Ea_kJ, k0, dHrxn, CpR, D_ax
    Note: Ea_kJ=0 → k0 used as local rate constant [1/s] (no Arrhenius).
    """
    result = solve_system(payload, "reactor")
    final  = result["final"]
    t_res  = result["tr"]["t_res"]
    k_local = payload.get("k0", 0.05)
    Da     = k_local * t_res
    import math as _m
    L      = payload.get("len", payload.get("Lr", 4))
    D_ax   = payload.get("D_ax", 0.005)
    v_ax   = result["tr"]["v_ax"]
    Pe_r   = v_ax * L / max(D_ax, 1e-6)
    resReq = payload.get("resReq", 15)
    conv   = round(final["X_conv"] * 100, 2)
    ok     = t_res >= resReq
    return {**result, "module": "reactor",
            "conv":    conv,
            "Da":      round(Da, 3),
            "Pe_r":    round(Pe_r, 2),
            "res_min": round(t_res / 60, 2),
            "resReq":  resReq,
            "ok":      ok,
            "summary": {
                "X_conv_pct":    conv,
                "Da":            round(Da, 3),
                "Pe":            round(Pe_r, 2),
                "t_res_s":       round(t_res, 1),
                "t_res_min":     round(t_res / 60, 2),
                "target_min":    resReq,
                "target_met":    ok,
                "T_out":         round(final["T"], 1),
                "v_ax":          round(v_ax, 4),
            }}


@router.post("/process/mixer", tags=["Process"])
def run_mixer(payload: dict):
    """
    Screw mixer: Newton number + Lacey + Axial Dispersion Model.
    Inputs: D, L, N, rho, fill, mtype, mode, shaft_mode, psz, psz2, pr
    """
    # Normalise frontend field names → engine field names
    inp = {
        "D":    payload.get("D") or payload.get("diam", 0.4),
        "L":    payload.get("L") or payload.get("len",  4.0),
        "N":    payload.get("N") or payload.get("speed", 40),
        "rho":  payload.get("rho", 1.2),
        "fill": payload.get("fill", 0.45),
        "mtype":payload.get("mtype", "ribbon"),
        "mode": payload.get("mode", "batch"),
        "shaft_mode": payload.get("shaft_mode", "single"),
        "psz":  payload.get("psz", 1.0),
        "psz2": payload.get("psz2", 1.0),
        "pr":   payload.get("pr", 1),
        "ns":   payload.get("ns", 1),
        **{k: v for k, v in payload.items() if k not in ("diam","len","speed")},
    }
    result = calc_mixer(inp)
    return {**result, "module": "mixer"}


@router.post("/process/separator", tags=["Process"])
def run_separator(payload: dict, db: Session = Depends(get_db)):
    """
    Screw separator: Stokes settling grade efficiency.
    Inputs: lenSep, speedS, fill2, tIn, feedS, rho, rhoA, d_p
    """
    result = solve_system(payload, "sep")
    final  = result["final"]
    metrics = psd_metrics(final["PSD"])
    import math as _m
    tr_sep = result["tr"]
    N_sep  = payload.get("speedS", 30)
    D_sep  = payload.get("diam", 0.3)
    fill_s = payload.get("fill2", 0.35)
    t_res_s= tr_sep["t_res"]
    mass_in = result["history"][0]["mass_flow"] if result["history"] else 1
    fines_frac = final["mass_flow"] / max(mass_in, 0.001)
    sep_pct = round((1 - fines_frac) * 100, 1)  # coarse removed %
    # Rotation efficiency (lower is better for gentle separation)
    N_ref   = 45
    eta_rot = round(1 / (1 + (N_sep / N_ref) ** 1.5), 3)
    eta_fill= round(min(1, fill_s / 0.35), 3)
    eta_time= round(min(1, t_res_s / 120), 3)
    return {**result, "module": "separator",
            "sep":      sep_pct,
            "eta_rot":  eta_rot,
            "eta_fill": eta_fill,
            "eta_time": eta_time,
            "summary": {
                "sep_pct":       sep_pct,
                "d50_in_mm":     result["history"][0].get("d50", 2) if result["history"] else 2,
                "d50_out_mm":    metrics["d50"],
                "d10_out_mm":    metrics["d10"],
                "d90_out_mm":    metrics["d90"],
                "fines_frac":    round(fines_frac, 3),
                "eta_rot":       eta_rot,
                "eta_fill":      eta_fill,
                "eta_time":      eta_time,
                "t_res_s":       round(t_res_s, 1),
                "v_ax":          round(tr_sep["v_ax"], 4),
            }}


@router.post("/process/compactor", tags=["Process"])
def run_compactor(payload: dict, db: Session = Depends(get_db)):
    """
    Screw compactor: Janssen back-pressure + power-law compaction.
    Inputs: diam, fLen, fN_max, fFill, tIn, fRho, tgtR, mu_wall, k_lat
    """
    result = solve_system(payload, "compact")
    final  = result["final"]
    rho_initial = payload.get("fRho", 1.2) * 1000
    rho_target  = payload.get("tgtR", 0.85) * 1000
    CR = final["rho"] / max(rho_initial, 1)
    import math as _m
    N_comp   = payload.get("Nc", 30)
    omega_c  = 2 * _m.pi * N_comp / 60
    D_comp   = payload.get("diam", 0.3)
    sigma_j  = final["sigma"]    # kPa Janssen
    tau_shear= sigma_j * payload.get("mu_wall", 0.35)
    Pm_c     = sigma_j * 1000 * _m.pi * (D_comp/2)**2 * result["tr"]["v_ax"]  # W
    Tr_c     = Pm_c / max(omega_c, 0.001)
    plugging = sigma_j > 200   # plug if back pressure > 200 kPa
    return {**result, "module": "compactor",
            "rho_out":      round(final["rho"] / 1000, 3),
            "CR":           round(CR, 3),
            "sigma_max":    round(sigma_j, 2),
            "sigma_janssen":round(sigma_j, 2),
            "torque_Nm":    round(Tr_c, 1),
            "plugging":     plugging,
            "summary": {
                "rho_in":        round(rho_initial / 1000, 3),
                "rho_out":       round(final["rho"] / 1000, 3),
                "CR":            round(CR, 3),
                "sigma_max_kPa": round(sigma_j, 2),
                "tau_shear_kPa": round(tau_shear, 2),
                "torque_Nm":     round(Tr_c, 1),
                "plugging":      plugging,
                "v_ax":          round(result["tr"]["v_ax"], 4),
            }}


@router.post("/process/feeder", tags=["Process"])
def run_feeder(payload: dict):
    """
    Screw feeder / doser sizing engine.
    CEMA 7th Ed. + Jenike hopper principles.
    Inputs: fDiam, fLen, fPitch, fFill, fRho, fN_min, fN_max, fQ_target,
            fMat_flowability, fMode, fDriveType, fHopperVol, fHopperAngle,
            fWallFriction, fLIW_tare, fDownstreamT, fBatchSize
    """
    result = calc_feeder(payload)
    return {**result, "module": "feeder"}