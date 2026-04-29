import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from models.division import DimDivision
from models.kpi import DimKpi
from models.period import DimPeriod
from models.fact_raw import FactKpiPerformance
from models.user import User
from schemas.admin import (
    KpiCreate, KpiUpdate, KpiResponse,
    RealizationCreate, RealizationUpdate, RealizationResponse,
    EtlRequest,
)
from schemas.auth import UserCreate, UserResponse, UserUpdate
from services.security import require_admin, hash_password
from services.etl_service import run_etl, run_etl_all_years

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Meta endpoints (reference data for forms) ────────────────────────────── #

@router.get("/meta/divisions")
def get_divisions(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Return all divisions with their evaluation period type."""
    rows = db.query(DimDivision).order_by(DimDivision.division_id).all()
    return [
        {
            "division_id": d.division_id,
            "division_name": d.division_name,
            "evaluation_period": d.evaluation_period,  # M / Q / H
        }
        for d in rows
    ]


@router.get("/meta/periods")
def get_periods(
    period_type: str | None = None,
    kpi_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Return dim_period rows.
    - Jika kpi_id diberikan: otomatis filter sesuai evaluation_period KPI tersebut.
    - Jika period_type diberikan: filter manual (M/Q/H).
    """
    # Jika kpi_id diberikan, baca evaluation_period dari KPI tersebut
    if kpi_id:
        kpi = db.query(DimKpi).filter(DimKpi.kpi_id == kpi_id).first()
        if kpi:
            period_type = kpi.evaluation_period

    q = db.query(DimPeriod)
    if period_type:
        q = q.filter(DimPeriod.period_type == period_type.upper())
    rows = q.order_by(DimPeriod.period_order).all()
    return [
        {
            "period_id":    p.period_id,
            "period_name":  p.period_name,
            "period_type":  p.period_type,
            "period_order": p.period_order,
        }
        for p in rows
    ]


@router.get("/meta/realizations")
def get_realizations(
    division_id: int | None = None,
    kpi_id: int | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List existing realization records for admin editing."""
    q = (
        db.query(
            FactKpiPerformance,
            DimKpi.kpi_name,
            DimPeriod.period_name,
        )
        .join(DimKpi,    FactKpiPerformance.kpi_id    == DimKpi.kpi_id)
        .join(DimPeriod, FactKpiPerformance.period_id == DimPeriod.period_id)
    )
    if division_id: q = q.filter(FactKpiPerformance.division_id == division_id)
    if kpi_id:      q = q.filter(FactKpiPerformance.kpi_id == kpi_id)
    if year:        q = q.filter(FactKpiPerformance.year == year)
    rows = q.order_by(FactKpiPerformance.year, DimPeriod.period_order).all()
    return [
        {
            "fact_id":     f.fact_id,
            "division_id": f.division_id,
            "kpi_id":      f.kpi_id,
            "kpi_name":    kpi_name,
            "period_id":   f.period_id,
            "period_name": period_name,
            "year":        f.year,
            "target":      f.target,
            "realization": f.realization,
            "achievement": round((f.realization / f.target * 100), 1) if f.target else 0,
        }
        for f, kpi_name, period_name in rows
    ]


# ── KPI CRUD ─────────────────────────────────────────────────────────────── #

@router.post("/kpi", response_model=KpiResponse, status_code=201)
def create_kpi(
    payload: KpiCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy import text

    def _do_insert():
        kpi = DimKpi(**payload.model_dump())
        db.add(kpi)
        db.commit()
        db.refresh(kpi)
        return kpi

    try:
        return _do_insert()
    except IntegrityError:
        # Sequence out of sync — reset and retry once
        db.rollback()
        try:
            db.execute(text(
                "SELECT setval('dim_kpi_kpi_id_seq', "
                "COALESCE((SELECT MAX(kpi_id) FROM dim_kpi), 0) + 1, false)"
            ))
            db.commit()
            return _do_insert()
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Gagal membuat KPI, konflik ID: {exc}"
            )


@router.get("/kpi/{kpi_id}", response_model=KpiResponse)
def get_kpi(
    kpi_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    kpi = db.query(DimKpi).filter(DimKpi.kpi_id == kpi_id).first()
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI tidak ditemukan")
    return kpi


@router.get("/kpi", response_model=list[KpiResponse])
def list_kpi(
    division_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(DimKpi)
    if division_id:
        q = q.filter(DimKpi.division_id == division_id)
    return q.order_by(DimKpi.division_id, DimKpi.kpi_id).all()


@router.put("/kpi/{kpi_id}", response_model=KpiResponse)
def update_kpi(
    kpi_id: int,
    payload: KpiUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    kpi = db.query(DimKpi).filter(DimKpi.kpi_id == kpi_id).first()
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI tidak ditemukan")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(kpi, field, val)
    db.commit()
    db.refresh(kpi)
    return kpi


@router.delete("/kpi/{kpi_id}", status_code=204)
def delete_kpi(
    kpi_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    kpi = db.query(DimKpi).filter(DimKpi.kpi_id == kpi_id).first()
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI tidak ditemukan")
    db.delete(kpi)
    db.commit()


# ── Realization CRUD ─────────────────────────────────────────────────────── #

@router.post("/realization", response_model=RealizationResponse, status_code=201)
def create_realization(
    payload: RealizationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = FactKpiPerformance(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/realization/{fact_id}", response_model=RealizationResponse)
def update_realization(
    fact_id: int,
    payload: RealizationUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = db.query(FactKpiPerformance).filter(FactKpiPerformance.fact_id == fact_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Realization record tidak ditemukan")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(row, field, val)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/realization/{fact_id}", status_code=204)
def delete_realization(
    fact_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Hapus satu record realisasi KPI berdasarkan fact_id."""
    row = db.query(FactKpiPerformance).filter(FactKpiPerformance.fact_id == fact_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Realization record tidak ditemukan")
    db.delete(row)
    db.commit()


# ── ETL Trigger ──────────────────────────────────────────────────────────── #

@router.post("/run-etl")
def trigger_etl(
    payload: EtlRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        if payload.all_years:
            results = run_etl_all_years(db)
            return {"status": "success", "results": results}
        else:
            result = run_etl(db, payload.year)
            if result["status"] != "success":
                raise HTTPException(status_code=500, detail=result.get("error", "ETL failed"))
            return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"ETL error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ── User Management ──────────────────────────────────────────────────────── #

@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username sudah digunakan")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email sudah digunakan")
    if payload.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role harus 'admin' atau 'user'")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    # Prevent admin from deactivating themselves
    if user.user_id == current_admin.user_id and payload.is_active is False:
        raise HTTPException(status_code=400, detail="Tidak dapat menonaktifkan akun sendiri")

    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(user, field, val)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if user.user_id == current_admin.user_id:
        raise HTTPException(status_code=400, detail="Tidak dapat menghapus akun sendiri")
    db.delete(user)
    db.commit()
