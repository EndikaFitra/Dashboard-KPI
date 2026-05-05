import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _seed_default_admin():
    """Create default admin user if none exists (runs once on startup)."""
    from app.database import SessionLocal
    from models.user import User
    from services.security import hash_password

    db = SessionLocal()
    try:
        if db.query(User).filter(User.role == "admin").count() == 0:
            admin = User(
                username="admin",
                email="admin@kpi.local",
                password_hash=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)
            db.commit()
            logger.info("Default admin user created: admin / admin123")
    except Exception as exc:
        logger.error(f"Failed to seed admin: {exc}")
    finally:
        db.close()



def _reset_sequences():
    """
    Sync PostgreSQL auto-increment sequences with the actual max ID in each table.
    Prevents 'duplicate key' errors that occur when rows were inserted with
    explicit IDs (e.g. during seeding/ETL), bypassing the sequence counter.
    """
    from app.database import SessionLocal
    from sqlalchemy import text

    # table_name → (sequence_name, primary_key_column)
    tables = [
        ("dim_kpi",              "dim_kpi_kpi_id_seq",              "kpi_id"),
        ("dim_division",         "dim_division_division_id_seq",     "division_id"),
        ("dim_period",           "dim_period_period_id_seq",         "period_id"),
        ("fact_kpi_performance", "fact_kpi_performance_fact_id_seq", "fact_id"),
        ("users",                "users_id_seq",                     "id"),
    ]
    db = SessionLocal()
    try:
        for table, seq, pk in tables:
            try:
                db.execute(text(
                    f"SELECT setval('{seq}', COALESCE((SELECT MAX({pk}) FROM {table}), 0) + 1, false)"
                ))
            except Exception as e:
                # Sequence or table may not exist yet — skip silently
                logger.debug(f"Sequence reset skipped for {seq}: {e}")
        db.commit()
        logger.info("PostgreSQL sequences synced.")
    except Exception as exc:
        logger.error(f"Failed to reset sequences: {exc}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("KPI Analytics API starting up...")
    from app.database import engine, Base
    import models.division       # noqa
    import models.kpi            # noqa
    import models.period         # noqa
    import models.mapping        # noqa
    import models.fact_raw       # noqa
    import models.user           # noqa  ← NEW
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")
    _seed_default_admin()
    _reset_sequences()   # ← fix duplicate key errors after seeding
    yield
    logger.info("KPI Analytics API shutting down.")


app = FastAPI(
    title="KPI Analytics API",
    version="1.0.0",
    description="Data Warehouse REST API for KPI Performance Monitoring",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import dashboard, kpi, mcp, auth, admin, forecast  # noqa

app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(kpi.router,       prefix="/kpi",       tags=["KPI"])
app.include_router(mcp.router,       prefix="/mcp",       tags=["MCP"])
app.include_router(auth.router,      prefix="/auth",      tags=["Auth"])
app.include_router(admin.router,     prefix="/admin",     tags=["Admin"])
app.include_router(forecast.router,  prefix="/forecast",  tags=["Forecast"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "KPI Analytics API", "version": "1.0.0"}
