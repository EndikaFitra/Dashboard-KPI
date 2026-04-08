"""
Migration: Add weight column to dim_kpi and populate with correct values.

Run this ONCE on an existing database after seed.py has been run.
If you are doing a fresh setup, seed.py already includes weight — skip this script.

Usage:
    python scripts/migrate_add_weight.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine

WEIGHTS = {
    # Network — kpi_id: weight
    1: 5.0,
    2: 35.0,
    3: 60.0,
    # Software Engineer
    4: 25.0,
    5: 25.0,
    6: 20.0,
    7: 30.0,
    # Sales Executive
    8:  60.0,
    9:  30.0,
    10: 10.0,
    # HR Officer
    11: 20.0,
    12: 20.0,
    13: 20.0,
    14: 20.0,
    15: 20.0,
}


def run():
    with engine.connect() as conn:
        # 1. Add column if it doesn't exist
        conn.execute(text("""
            ALTER TABLE dim_kpi
            ADD COLUMN IF NOT EXISTS weight FLOAT NOT NULL DEFAULT 0.0;
        """))
        print("✓ Column 'weight' ensured on dim_kpi")

        # 2. Populate weights per kpi_id
        for kpi_id, weight in WEIGHTS.items():
            conn.execute(
                text("UPDATE dim_kpi SET weight = :w WHERE kpi_id = :id"),
                {"w": weight, "id": kpi_id}
            )
        conn.commit()
        print("✓ Weights updated for all KPIs")

        # 3. Verify
        rows = conn.execute(
            text("SELECT kpi_id, kpi_name, weight FROM dim_kpi ORDER BY kpi_id")
        ).fetchall()
        print("\nCurrent weight values:")
        for r in rows:
            print(f"  [{r.kpi_id:>2}] {r.kpi_name:<60} {r.weight}%")


if __name__ == "__main__":
    run()
    print("\n✅ Migration complete.")
