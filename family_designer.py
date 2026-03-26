"""
SQLite database layer for Screw Conveyor Designer.
Replaces in-memory dicts. Supports full CRUD via FastAPI routes.
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "conveyor.db"
DB_PATH.parent.mkdir(exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS materials (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    bulk_density REAL   NOT NULL,
    lambda_cema  REAL   NOT NULL DEFAULT 1.5,
    lambda_kws   REAL   NOT NULL DEFAULT 1.55,
    lambda_din   REAL   NOT NULL DEFAULT 1.5,
    trough_loading REAL NOT NULL DEFAULT 0.30,
    Ks           REAL   NOT NULL DEFAULT 1.0,
    abrasive     TEXT   NOT NULL DEFAULT 'Low',
    wear_coeff   REAL   NOT NULL DEFAULT 1.0,
    cema_class   TEXT   NOT NULL DEFAULT 'II',
    angle_of_repose REAL DEFAULT 35.0,
    particle_size_mm REAL DEFAULT 10.0,
    moisture_pct REAL DEFAULT 0.0,
    temperature_c REAL DEFAULT 20.0,
    notes        TEXT   DEFAULT '',
    custom       INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bearings (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE,
    C_kN    REAL NOT NULL,
    p       REAL NOT NULL DEFAULT 3.0,
    description TEXT DEFAULT '',
    bore_mm REAL DEFAULT 0,
    custom  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gearboxes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model           TEXT NOT NULL UNIQUE,
    max_torque_Nm   REAL NOT NULL,
    thermal_power_kW REAL NOT NULL,
    thermal_sf      REAL NOT NULL DEFAULT 1.0,
    custom          INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS motors (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    kW      REAL NOT NULL UNIQUE,
    custom  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS costs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item        TEXT NOT NULL UNIQUE,
    usd_per_kg  REAL NOT NULL,
    notes       TEXT DEFAULT '',
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS process_configs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    process_type TEXT NOT NULL,
    config_json  TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""

SEED_MATERIALS = [
    # name, bulk_density, lam_cema, lam_kws, lam_din, trough, Ks, abrasive, wear, cema_cls, repose, particle, moisture, temp, notes
    ("Cement",                1.40, 1.60, 1.65, 1.60, 0.30, 1.00, "Medium",   1.0, "II",  40, 0.1, 0.5,  60, "Portland cement, dry"),
    ("Sand",                  1.60, 1.70, 1.75, 1.70, 0.30, 1.00, "High",     2.0, "III", 35, 2.0, 0.5,  20, "Dry construction sand"),
    ("Fly Ash",               0.90, 1.80, 1.85, 1.80, 0.25, 1.05, "Low",      0.6, "II",  45, 0.05,2.0,  80, "Coal combustion residual"),
    ("Coal",                  0.80, 1.50, 1.55, 1.50, 0.30, 1.00, "Low",      0.5, "I",   38, 25,  8.0,  20, "Bituminous coal"),
    ("Grain (Wheat)",         0.75, 1.20, 1.25, 1.20, 0.45, 1.00, "Low",      0.3, "I",   28, 5.0, 14.0, 20, "Wheat grain, typical"),
    ("Grain (Corn)",          0.72, 1.20, 1.25, 1.20, 0.45, 1.00, "Low",      0.3, "I",   27, 8.0, 15.0, 20, "Corn/maize"),
    ("Limestone",             1.30, 1.60, 1.65, 1.60, 0.30, 1.05, "High",     1.8, "III", 40, 12,  0.5,  20, "Crushed limestone"),
    ("Gypsum",                1.10, 1.60, 1.65, 1.60, 0.30, 1.00, "Medium",   1.0, "II",  40, 1.0, 0.5,  20, "Dry powdered gypsum"),
    ("Salt",                  1.20, 1.50, 1.55, 1.50, 0.35, 1.00, "Low",      0.4, "II",  35, 3.0, 0.1,  20, "Industrial salt"),
    ("Sugar",                 0.80, 1.30, 1.35, 1.30, 0.40, 1.00, "Low",      0.2, "I",   30, 0.5, 0.5,  20, "Granulated sugar"),
    ("Phosphate Rock",        1.50, 1.70, 1.75, 1.70, 0.30, 1.05, "High",     2.5, "III", 40, 15,  1.0,  20, "Ground phosphate rock"),
    ("Wood Chips",            0.25, 1.40, 1.45, 1.40, 0.40, 1.00, "Low",      0.4, "I",   45, 20,  35.0, 20, "Typical wood chips 30x30mm"),
    ("Wood Pellets",          0.65, 1.30, 1.35, 1.30, 0.40, 1.00, "Low",      0.3, "I",   25, 6.0, 8.0,  20, "Biomass pellets 6mm"),
    ("Soda Ash",              0.55, 1.60, 1.65, 1.60, 0.30, 1.00, "Low",      0.5, "II",  40, 0.1, 0.2,  20, "Dense soda ash"),
    ("Alumina",               0.90, 1.80, 1.85, 1.80, 0.25, 1.05, "High",     3.0, "III", 45, 0.1, 0.5,  60, "Calcined alumina"),
    ("Iron Ore",              2.20, 1.90, 1.95, 1.90, 0.25, 1.10, "High",     4.0, "IV",  45, 20,  2.0,  20, "Iron ore fines"),
    ("Clinker",               1.50, 1.70, 1.75, 1.70, 0.25, 1.05, "High",     3.5, "III", 45, 30,  0.5, 200, "Cement clinker, hot"),
    ("Potash (MOP)",          1.10, 1.40, 1.45, 1.40, 0.35, 1.00, "Low",      0.5, "II",  35, 2.0, 0.5,  20, "Muriate of potash"),
    ("Urea Granules",         0.80, 1.30, 1.35, 1.30, 0.40, 1.00, "Low",      0.3, "I",   30, 3.0, 0.3,  20, "Prilled or granular urea"),
    ("Bentonite",             0.95, 1.70, 1.75, 1.70, 0.30, 1.00, "Medium",   1.0, "II",  45, 0.1, 8.0,  20, "Activated bentonite clay"),
    ("PVC Powder",            0.55, 1.40, 1.45, 1.40, 0.35, 1.00, "Low",      0.3, "I",   35, 0.1, 0.1,  20, "PVC resin powder"),
    ("HDPE Pellets",          0.55, 1.20, 1.25, 1.20, 0.45, 1.00, "Low",      0.2, "I",   25, 4.0, 0.1,  20, "High-density polyethylene"),
    ("Coffee Beans",          0.65, 1.20, 1.25, 1.20, 0.45, 1.00, "Low",      0.2, "I",   30, 8.0, 11.0, 20, "Green or roasted coffee"),
    ("Soybean Meal",          0.62, 1.30, 1.35, 1.30, 0.40, 1.00, "Low",      0.4, "I",   35, 1.0, 12.0, 20, "Soybean extracted meal"),
    ("Titanium Dioxide",      1.00, 1.90, 1.95, 1.90, 0.25, 1.05, "Medium",   2.0, "II",  45, 0.02,0.1,  20, "TiO2 pigment powder"),
    ("Silica Sand",           1.60, 1.80, 1.85, 1.80, 0.30, 1.00, "High",     3.0, "IV",  35, 0.5, 0.5,  20, "Industrial silica sand"),
    ("Rock Salt",             1.30, 1.55, 1.60, 1.55, 0.30, 1.00, "Medium",   1.5, "II",  40, 15,  0.5,  20, "Rock salt, crushed"),
    ("Activated Carbon",      0.40, 1.50, 1.55, 1.50, 0.30, 1.00, "Low",      0.4, "I",   35, 1.5, 5.0,  20, "Granular activated carbon"),
    ("Glass Cullet",          1.50, 1.80, 1.85, 1.80, 0.25, 1.00, "High",     4.0, "IV",  35, 15,  0.5,  20, "Recycled glass"),
    ("Calcium Carbonate",     0.95, 1.60, 1.65, 1.60, 0.30, 1.00, "Medium",   1.2, "II",  42, 0.05,0.5,  20, "Precipitated CaCO3"),
]

SEED_BEARINGS = [
    ("UC206", 20.0, 3.0, "Pillow block, light",       30),
    ("UC208", 31.0, 3.0, "Pillow block, light duty",   40),
    ("UC210", 43.0, 3.0, "Pillow block, medium duty",  50),
    ("UC212", 52.0, 3.0, "Pillow block, heavy duty",   60),
    ("UC214", 62.0, 3.0, "Pillow block, extra heavy",  70),
    ("UC216", 70.0, 3.0, "Pillow block, heavy",        80),
    ("SN516", 72.0, 3.0, "Plummer block, medium",      80),
    ("SN518", 90.0, 3.0, "Plummer block, heavy",       90),
    ("SN520", 104.0,3.0, "Plummer block, heavy",       100),
    ("SN222", 120.0,3.0, "Plummer block, heavy duty",  110),
    ("SN224", 140.0,3.0, "Plummer block, extra heavy", 120),
    ("SN228", 193.0,3.0, "Plummer block, max duty",    140),
]

SEED_GEARBOXES = [
    ("GB-5k",   5000,   4.0,  1.00),
    ("GB-10k",  10000,  7.5,  1.00),
    ("GB-20k",  20000,  15.0, 1.00),
    ("GB-40k",  40000,  30.0, 1.10),
    ("GB-80k",  80000,  55.0, 1.10),
    ("GB-160k", 160000, 110.0,1.15),
    ("GB-320k", 320000, 200.0,1.20),
]

SEED_MOTORS = [0.37,0.55,0.75,1.1,1.5,2.2,3.0,4.0,5.5,7.5,11,15,18.5,22,30,37,45,55,75,90,110,132,160,200,250,315]

SEED_COSTS = [
    ("Steel",           2.0,  "Standard carbon steel (S235/A36)"),
    ("Stainless 304",   5.0,  "304L stainless steel"),
    ("Stainless 316",   7.5,  "316L stainless steel"),
    ("WearLiner",       6.0,  "Wear-resistant liner plate (Hardox 400)"),
    ("Hardox 450",      9.0,  "Hardox 450 wear plate"),
    ("Cast Iron",       1.8,  "Grey cast iron"),
    ("Duplex 2205",    12.0,  "Duplex stainless 2205"),
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create schema and seed data if tables are empty."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()

    # Seed materials
    count = conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
    if count == 0:
        conn.executemany("""
            INSERT INTO materials
              (name,bulk_density,lambda_cema,lambda_kws,lambda_din,trough_loading,
               Ks,abrasive,wear_coeff,cema_class,angle_of_repose,particle_size_mm,
               moisture_pct,temperature_c,notes,custom)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
        """, SEED_MATERIALS)

    count = conn.execute("SELECT COUNT(*) FROM bearings").fetchone()[0]
    if count == 0:
        conn.executemany("""
            INSERT INTO bearings (name,C_kN,p,description,bore_mm,custom)
            VALUES (?,?,?,?,?,0)
        """, SEED_BEARINGS)

    count = conn.execute("SELECT COUNT(*) FROM gearboxes").fetchone()[0]
    if count == 0:
        conn.executemany("""
            INSERT INTO gearboxes (model,max_torque_Nm,thermal_power_kW,thermal_sf,custom)
            VALUES (?,?,?,?,0)
        """, SEED_GEARBOXES)

    count = conn.execute("SELECT COUNT(*) FROM motors").fetchone()[0]
    if count == 0:
        conn.executemany("INSERT INTO motors (kW,custom) VALUES (?,0)", [(k,) for k in SEED_MOTORS])

    count = conn.execute("SELECT COUNT(*) FROM costs").fetchone()[0]
    if count == 0:
        conn.executemany("INSERT INTO costs (item,usd_per_kg,notes) VALUES (?,?,?)", SEED_COSTS)

    conn.commit()
    conn.close()
    print(f"[DB] Initialized: {DB_PATH}")


def query(sql: str, params=()) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def execute(sql: str, params=()) -> int:
    """Returns lastrowid."""
    conn = get_connection()
    cur = conn.execute(sql, params)
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid


def get_material_dict(name: str) -> dict:
    rows = query("SELECT * FROM materials WHERE name=?", (name,))
    if not rows:
        raise ValueError(f"Material '{name}' not found in database.")
    return rows[0]


def get_bearing_dict(name: str) -> dict:
    rows = query("SELECT * FROM bearings WHERE name=?", (name,))
    if not rows:
        raise ValueError(f"Bearing '{name}' not found in database.")
    return rows[0]


def get_gearbox_dict(model: str) -> dict:
    rows = query("SELECT * FROM gearboxes WHERE model=?", (model,))
    if not rows:
        raise ValueError(f"Gearbox '{model}' not found in database.")
    return rows[0]


def get_motor_sizes() -> list[float]:
    rows = query("SELECT kW FROM motors ORDER BY kW")
    return [r["kW"] for r in rows]
