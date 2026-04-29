import os, sys
sys.path.insert(0, "d:/projek_kp_2/backend")
os.chdir("d:/projek_kp_2/backend")
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='" + "dim_kpi" + "' AND column_name='" + "evaluation_period" + "'")).fetchone()
    if result:
        print("Column already exists")
    else:
        conn.execute(text("ALTER TABLE dim_kpi ADD COLUMN evaluation_period VARCHAR(1) NOT NULL DEFAULT " + "'Q'"))
        conn.execute(text("UPDATE dim_kpi k SET evaluation_period = (SELECT d.evaluation_period FROM dim_division d WHERE d.division_id = k.division_id)"))
        conn.commit()
        print("Migration done")
    rows = conn.execute(text("SELECT kpi_id, kpi_name, evaluation_period FROM dim_kpi ORDER BY kpi_id")).fetchall()
    for r in rows:
        print(f"  KPI {r.kpi_id}: {r.kpi_name[:30]} -> {r.evaluation_period}")
