"""
Database seeder — populates SQLite from data_export.json.
Run once: python -m backend.db.seed
Re-running is safe (uses upsert logic).
"""
import json
import os
import sys

# Allow running as a script from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.db.database import engine, SessionLocal, Base
from backend.models.tables import Material, Bearing, Gearbox, Motor, Drive, CostItem

DATA_FILE = os.path.join(os.path.dirname(__file__), "data_export.json")


def seed(force: bool = False):
    """
    Seed database from data_export.json.
    force=True: re-inserts everything (use after schema changes).
    """
    print("Creating tables…")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Run column migrations FIRST so custom columns exist before queries
    from sqlalchemy import text, inspect as sa_inspect
    inspector = sa_inspect(engine)
    for table_name, col_name, col_type in [
        ("materials",  "custom", "BOOLEAN"),
        ("bearings",   "custom", "BOOLEAN"),
        ("gearboxes",  "custom", "BOOLEAN"),
        ("motors",     "custom", "BOOLEAN"),
        ("drives",     "custom", "BOOLEAN"),
    ]:
        try:
            cols = [c["name"] for c in inspector.get_columns(table_name)]
            if col_name not in cols:
                with engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} DEFAULT 0"))
                    conn.commit()
                print(f"  Migrated: added {col_name} to {table_name}")
        except Exception:
            pass  # table may not exist yet

    with open(DATA_FILE) as f:
        data = json.load(f)

    # ── MATERIALS ──────────────────────────────────────────────────
    print(f"Seeding {len(data['MATS'])} materials…")
    if force:
        db.query(Material).filter(Material.custom == False).delete()
        db.commit()
    existing_mats = {m.name for m in db.query(Material.name).all()}
    new_mats = 0
    for m in data["MATS"]:
        if m["name"] in existing_mats:
            continue
        db.add(Material(
            name           = m.get("name"),
            category       = m.get("category"),
            rho            = m.get("rho", 1.0),
            rho_min        = m.get("rho_min"),
            rho_max        = m.get("rho_max"),
            lambda_ref     = m.get("lambda_ref", 1.0),
            fill_max       = m.get("fill_max", 0.30),
            abr            = m.get("abr", "Medium"),
            cls            = m.get("cls", "II"),
            particle_class = m.get("particle_class", "B6"),
            flowability    = m.get("flowability", 2),
            moist          = m.get("moist", 5.0),
            aor            = m.get("aor", 35.0),
            cohesion       = m.get("cohesion", 0.5),
            temp_max       = m.get("temp_max", 80.0),
            bridging_risk  = m.get("bridging_risk", 0.1),
            flow_regime    = m.get("flow_regime", "funnel_flow"),
            confidence     = m.get("confidence", 0.8),
            source         = m.get("source", "derived"),
            note           = m.get("note", ""),
            cema_code      = m.get("cema_code", ""),
            flags          = m.get("flags", ""),
            app            = m.get("app", ["conv"]),
            custom         = False,
        ))
        new_mats += 1
    print(f"  Added {new_mats} new materials ({len(existing_mats)} already existed)")

    # ── BEARINGS ───────────────────────────────────────────────────
    print(f"Seeding {len(data['BEARINGS'])} bearings…")
    if force:
        db.query(Bearing).filter(Bearing.custom == False).delete()
        db.commit()
    existing_brg = {b.name for b in db.query(Bearing.name).all()}
    new_brg = 0
    for b in data["BEARINGS"]:
        if b["name"] in existing_brg:
            continue
        db.add(Bearing(
            name       = b.get("name"),
            mfr        = b.get("mfr"),
            type       = b.get("type"),
            bore       = b.get("bore"),
            od         = b.get("od"),
            B          = b.get("B"),
            C          = b.get("C"),
            C0         = b.get("C0"),
            p          = b.get("p", 3),
            speed_g    = b.get("speed_g"),
            seal       = b.get("seal"),
            role       = b.get("role"),
            brg_insert = b.get("brg_insert"),
            mass_kg    = b.get("mass_kg"),
            note       = b.get("note", ""),
        ))
        new_brg += 1
    print(f"  Added {new_brg} new bearings")

    # ── GEARBOXES ──────────────────────────────────────────────────
    print(f"Seeding {len(data['GBXS'])} gearboxes…")
    if force:
        db.query(Gearbox).filter(Gearbox.custom == False).delete()
        db.commit()
    existing_gbx = {g.model for g in db.query(Gearbox.model).all()}
    new_gbx = 0
    for g in data["GBXS"]:
        if g["model"] in existing_gbx:
            continue
        db.add(Gearbox(
            model     = g.get("model"),
            type      = g.get("type"),
            stages    = g.get("stages", 1),
            Tn        = g.get("Tn"),
            Pkw       = g.get("Pkw"),
            ratio_min = g.get("ratio_min"),
            ratio_max = g.get("ratio_max"),
            eta       = g.get("eta"),
            mount     = g.get("mount"),
            ip        = g.get("ip"),
            temp_max  = g.get("temp_max"),
            mass_kg   = g.get("mass_kg"),
            note      = g.get("note", ""),
        ))
        new_gbx += 1
    print(f"  Added {new_gbx} new gearboxes")

    # ── MOTORS ─────────────────────────────────────────────────────
    print(f"Seeding {len(data['MOTORS'])} motors…")
    if force:
        db.query(Motor).filter(Motor.custom == False).delete()
        db.commit()
    existing_mot = {m.model for m in db.query(Motor.model).all()}
    new_mot = 0
    for m in data["MOTORS"]:
        mdl = m.get("model") or m.get("frame") or f"MOT-{new_mot}"
        if mdl in existing_mot:
            continue
        db.add(Motor(
            model      = mdl,
            frame      = m.get("frame"),
            Pkw        = m.get("Pkw") or m.get("Pkw_nom"),
            poles      = m.get("poles", 4),
            rpm_50hz   = m.get("rpm_50hz") or m.get("rpm"),
            efficiency = m.get("efficiency") or m.get("eff"),
            ie_class   = m.get("ie_class"),
            ip         = m.get("ip"),
            mass_kg    = m.get("mass_kg"),
            note       = m.get("note", ""),
        ))
        new_mot += 1
    print(f"  Added {new_mot} new motors")

    # ── DRIVES ─────────────────────────────────────────────────────
    print(f"Seeding {len(data['DRIVES'])} drives…")
    if force:
        db.query(Drive).filter(Drive.custom == False).delete()
        db.commit()
    existing_drv = {d.model for d in db.query(Drive.model).all()}
    new_drv = 0
    for d in data["DRIVES"]:
        if d["model"] in existing_drv:
            continue
        db.add(Drive(
            model        = d.get("model"),
            type         = d.get("type"),
            Pkw_max      = d.get("Pkw_max"),
            Vrated       = d.get("Vrated"),
            Irated       = d.get("Irated"),
            overload_pct = d.get("overload_pct"),
            control      = d.get("control"),
            ip           = d.get("ip"),
            features     = d.get("features"),
            note         = d.get("note", ""),
        ))
        new_drv += 1
    print(f"  Added {new_drv} new drives")

    # ── Costs ─────────────────────────────────────────────────
    print(f"Seeding {len(data['COSTS_DB'])} cost items…")
    if force:
        db.query(CostItem).filter(CostItem.custom == False).delete()
        db.commit()
    existing_costs = {c.item for c in db.query(CostItem.item).all()}
    new_costs = 0
    for row in data["COSTS_DB"]:
        if row["item"] not in existing_costs:
            db.add(CostItem(
                item=row["item"],
                usd=row["usd"],
                description=row.get("description"),
                material_group=row.get("material_group"),
                custom=False,
            ))
            new_costs += 1
    db.commit()
    print(f"  Added {new_costs} new cost items")

    # (column migrations now run at top of seed())

    db.commit()
    db.close()
    print("\n✅ Database seeded successfully.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Re-insert all rows even if they already exist (use after schema changes)")
    args = parser.parse_args()
    seed(force=args.force)
