"""
Backward-compatible shim: delegates to SQLite db layer.
"""
from core.db import (
    get_material_dict, get_bearing_dict, get_gearbox_dict, get_motor_sizes,
    query as db_query, init_db
)

def get_material(name: str) -> dict:
    return get_material_dict(name)

def get_bearing(name: str) -> dict:
    return get_bearing_dict(name)

def get_gearbox(model: str) -> dict:
    return get_gearbox_dict(model)

def get_motor_sizes_list() -> list:
    return get_motor_sizes()

def select_motor(required_kw: float, sizes=None) -> float:
    pool = sizes if sizes is not None else get_motor_sizes()
    for s in sorted(pool):
        if s >= required_kw:
            return s
    return sorted(pool)[-1]

# Expose live dict views for API
@property
def MATERIALS():
    rows = db_query("SELECT * FROM materials ORDER BY name")
    return {r["name"]: r for r in rows}

@property
def BEARINGS():
    rows = db_query("SELECT * FROM bearings ORDER BY name")
    return {r["name"]: r for r in rows}

@property
def GEARBOXES():
    rows = db_query("SELECT * FROM gearboxes ORDER BY model")
    return {r["model"]: r for r in rows}

COSTS_STATIC = {
    "Steel": 2.0, "Stainless": 5.0, "WearLiner": 6.0
}

def get_costs() -> dict:
    rows = db_query("SELECT item, usd_per_kg FROM costs ORDER BY item")
    return {r["item"]: r["usd_per_kg"] for r in rows}

def get_cost(steel_type: str) -> float:
    costs = get_costs()
    return costs.get(steel_type, costs.get("Steel", 2.0))

MOTOR_SIZES_KW = get_motor_sizes()
COSTS = get_costs()
