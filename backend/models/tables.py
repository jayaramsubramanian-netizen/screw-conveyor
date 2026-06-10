"""
SQLAlchemy ORM table definitions.
Field names exactly match the JS material database schema.
"""
from sqlalchemy import Column, Integer, Float, String, Text, JSON, Boolean
from ..db.database import Base


class Material(Base):
    __tablename__ = "materials"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(120), unique=True, nullable=False, index=True)
    category        = Column(String(60), index=True)
    rho             = Column(Float, nullable=False)          # bulk density t/m³
    rho_min         = Column(Float)
    rho_max         = Column(Float)
    lambda_ref      = Column(Float)                          # reference λ (CEMA validated)
    fill_max        = Column(Float)                          # max trough fill fraction
    abr             = Column(String(20))                     # Low/Medium/High/Very High
    cls             = Column(String(5))                      # CEMA load class I–IV
    particle_class  = Column(String(10))                     # A200/A100/A40/B6/C1/2/D3/D7
    flowability     = Column(Integer)                        # 1=Very free … 4=Sluggish
    moist           = Column(Float)                          # moisture %
    aor             = Column(Float)                          # angle of repose °
    cohesion        = Column(Float)                          # cohesion kPa
    temp_max        = Column(Float)                          # max process temp °C
    bridging_risk   = Column(Float)                          # 0.0–1.0
    flow_regime     = Column(String(30))                     # mass_flow/funnel_flow/cohesive_flow
    confidence      = Column(Float)                          # 0–1 data confidence
    source          = Column(String(30))
    note            = Column(Text)
    cema_code       = Column(String(30))
    flags           = Column(String(20))
    app             = Column(JSON)                           # ["conv","dry","mix",...]
    custom          = Column(Boolean, default=False)


class Bearing(Base):
    __tablename__ = "bearings"

    id          = Column(Integer, primary_key=True)
    name        = Column(String(30), unique=True, nullable=False, index=True)
    mfr         = Column(String(20))
    type        = Column(String(20))
    bore        = Column(Float)          # mm
    od          = Column(Float)
    B           = Column(Float)
    C           = Column(Float)          # dynamic load rating kN
    C0          = Column(Float)          # static load rating kN
    p           = Column(Float)          # life exponent
    speed_g     = Column(Integer)        # grease speed limit rpm
    seal        = Column(String(20))
    role        = Column(String(30))
    brg_insert  = Column(String(20))
    mass_kg     = Column(Float)
    note        = Column(Text)
    custom      = Column(Boolean, default=False)


class Gearbox(Base):
    __tablename__ = "gearboxes"

    id          = Column(Integer, primary_key=True)
    model       = Column(String(30), unique=True, nullable=False, index=True)
    type        = Column(String(5))      # W/H/B/P
    stages      = Column(Integer)
    Tn          = Column(Float)          # rated torque Nm
    Pkw         = Column(Float)          # rated power kW
    ratio_min   = Column(Float)
    ratio_max   = Column(Float)
    eta         = Column(Float)          # efficiency %
    mount       = Column(String(10))
    ip          = Column(String(10))
    temp_max    = Column(Float)
    mass_kg     = Column(Float)
    note        = Column(Text)
    custom      = Column(Boolean, default=False)


class Motor(Base):
    __tablename__ = "motors"

    id          = Column(Integer, primary_key=True)
    model       = Column(String(30), unique=True)
    frame       = Column(String(20))
    Pkw         = Column(Float)
    poles       = Column(Integer)
    rpm_50hz    = Column(Float)
    efficiency  = Column(Float)
    ie_class    = Column(String(5))
    ip          = Column(String(10))
    mass_kg     = Column(Float)
    note        = Column(Text)
    custom      = Column(Boolean, default=False)


class Drive(Base):
    __tablename__ = "drives"

    id          = Column(Integer, primary_key=True)
    model       = Column(String(30), unique=True)
    type        = Column(String(5))      # VFD/SS/DOL/SD
    Pkw_max     = Column(Float)
    Vrated      = Column(Float)
    Irated      = Column(Float)
    overload_pct= Column(Float)
    control     = Column(String(30))
    ip          = Column(String(10))
    features    = Column(Text)
    note        = Column(Text)
    custom      = Column(Boolean, default=False)


class CostItem(Base):
    __tablename__ = "cost_items"

    id          = Column(Integer, primary_key=True)
    item        = Column(String(60), unique=True, nullable=False, index=True)
    usd         = Column(Float, nullable=False)     # USD per kg
    description = Column(String(120))
    material_group = Column(String(40))             # Steel/Stainless/Wear/Special
    custom      = Column(Boolean, default=False)
    note        = Column(Text)


# Add custom flag to Bearing and Gearbox for edit tracking
# (columns added via ALTER in seed if missing — SQLite-safe approach handled in seed.py)
