import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from models.division import DimDivision
from models.kpi import DimKpi
from models.period import DimPeriod
from models.fact_raw import FactKpiPerformance
from models.user import User
from schemas.admin import (
    KpiCreate, KpiUpdate, KpiResponse,
    RealizationCreate, RealizationUpdate, RealizationResponse,
)
from schemas.auth import UserCreate, UserResponse, UserUpdate
from services.security import require_admin, hash_password, get_current_user

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
        kpi = _do_insert()
    except IntegrityError:
        # Sequence out of sync — reset and retry once
        db.rollback()
        try:
            db.execute(text(
                "SELECT setval('dim_kpi_kpi_id_seq', "
                "COALESCE((SELECT MAX(kpi_id) FROM dim_kpi), 0) + 1, false)"
            ))
            db.commit()
            kpi = _do_insert()
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Gagal membuat KPI, konflik ID: {exc}"
            )

    # Dual Write — buat file CSV baru untuk KPI ini (Tahap 3)
    from services.csv_sync import create_kpi_csv
    csv_path = create_kpi_csv(
        kpi_id=kpi.kpi_id,
        kpi_name=kpi.kpi_name,
        division_id=kpi.division_id,
    )
    logger.info(f"csv_sync: file CSV baru dibuat → {csv_path.name} (kpi_id={kpi.kpi_id})")

    return kpi



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
    _: User = Depends(get_current_user),
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

    # Simpan nama KPI sebelum dihapus untuk keperluan log
    kpi_name_saved = kpi.kpi_name

    db.delete(kpi)
    db.commit()

    # Dual Write — hapus file CSV milik KPI ini (Tahap 3)
    from services.csv_sync import find_csv_for_kpi, _invalidate_cache
    csv_path = find_csv_for_kpi(kpi_id)
    if csv_path and csv_path.exists():
        try:
            csv_path.unlink()
            _invalidate_cache(kpi_id)
            logger.info(
                f"csv_sync: ✓ File CSV dihapus → {csv_path.name} "
                f"(kpi_id={kpi_id}, kpi_name='{kpi_name_saved}')"
            )
        except Exception as e:
            logger.warning(f"csv_sync: gagal hapus file CSV {csv_path.name} — {e}")
    else:
        logger.warning(f"csv_sync: file CSV untuk kpi_id={kpi_id} tidak ditemukan saat delete")


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

    # Dual Write — sinkronkan ke CSV sumber data (Tahap 2)
    from services.csv_sync import append_realization as csv_append
    synced = csv_append(
        division_id=row.division_id,
        kpi_id=row.kpi_id,
        period_id=row.period_id,
        year=row.year,
        target=row.target,
        realization=row.realization,
    )
    if not synced:
        logger.warning(
            f"csv_sync: gagal sync realisasi baru ke CSV "
            f"(kpi_id={row.kpi_id}, period_id={row.period_id}, year={row.year})"
        )

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

    # Dual Write — sinkronkan perubahan ke CSV sumber data (Tahap 2)
    from services.csv_sync import update_realization as csv_update
    csv_update(
        kpi_id=row.kpi_id,
        period_id=row.period_id,
        year=row.year,
        target=row.target,
        realization=row.realization,
    )

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

    # Simpan info sebelum dihapus untuk sinkronisasi CSV (Tahap 2)
    kpi_id_saved    = row.kpi_id
    period_id_saved = row.period_id
    year_saved      = row.year

    db.delete(row)
    db.commit()

    # Dual Write — hapus baris dari CSV sumber data
    from services.csv_sync import delete_realization as csv_delete
    csv_delete(kpi_id=kpi_id_saved, period_id=period_id_saved, year=year_saved)

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
    payload.username = payload.username.lower()
    if db.query(User).filter(func.lower(User.username) == payload.username).first():
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


# ── ETL Trigger (Fase 6) ─────────────────────────────────────────────────── #

@router.post("/etl/run", tags=["ETL"])
def trigger_etl(
    year: Optional[int] = Query(None, description="Filter tahun tertentu. Kosongkan untuk load semua tahun."),
    dry_run: bool = Query(False, description="Jika true, preview proses ETL tanpa menyimpan ke database."),
    _: "User" = Depends(require_admin),
):
    """
    Trigger proses ETL dari file CSV di folder backend/data/ ke database.

    - **year**: isi untuk load satu tahun saja (contoh: 2025), kosongkan untuk semua tahun.
    - **dry_run**: jika `true`, ETL berjalan tapi tidak ada yang disimpan ke DB (mode preview).

    Hanya admin yang dapat mengakses endpoint ini.
    """
    try:
        from scripts.etl_csv import run_etl
        result = run_etl(year_filter=year, dry_run=dry_run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ETL gagal dijalankan: {str(e)}")

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail={
            "message": "ETL selesai dengan error",
            "errors":  result.get("errors", []),
            "summary": result,
        })

    return {
        "message": "ETL berhasil dijalankan" + (" (dry-run)" if dry_run else ""),
        "summary": result,
    }


@router.get("/etl/status", tags=["ETL"])
def etl_data_status(
    db: Session = Depends(get_db),
    _: "User" = Depends(require_admin),
):
    """
    Cek status data di Data Warehouse:
    - Jumlah total baris di fact_kpi_performance
    - Tahun-tahun yang sudah tersedia
    - Jumlah baris per tahun
    """
    from sqlalchemy import text

    total = db.execute(
        text("SELECT COUNT(*) FROM fact_kpi_performance")
    ).scalar()

    per_year = db.execute(
        text("""
            SELECT year, COUNT(*) as row_count
            FROM fact_kpi_performance
            GROUP BY year
            ORDER BY year DESC
        """)
    ).fetchall()

    return {
        "total_rows": total,
        "years": [
            {"year": r.year, "row_count": r.row_count}
            for r in per_year
        ],
    }


# ── CSV Maintenance (Tahap 4) ─────────────────────────────────────────────── #

@router.get("/csv/status", tags=["CSV"])
def csv_status(
    _: "User" = Depends(require_admin),
):
    """
    Cek status semua file CSV di folder data/:
    - Daftar file yang ada
    - kpi_id yang terkandung di setiap file
    - Jumlah baris data per file
    """
    from services.csv_sync import DATA_DIR
    import pandas as pd

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_files = sorted(DATA_DIR.glob("*.csv"))

    result = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            kpi_ids  = df["kpi_id"].unique().tolist() if "kpi_id" in df.columns else []
            years    = sorted(df["year"].unique().tolist()) if "year" in df.columns else []
            row_count = len(df)
        except Exception as e:
            kpi_ids   = []
            years     = []
            row_count = -1

        result.append({
            "filename":  f.name,
            "kpi_ids":   kpi_ids,
            "years":     years,
            "row_count": row_count,
        })

    return {
        "data_dir":    str(DATA_DIR),
        "total_files": len(result),
        "files":       result,
    }


@router.post("/csv/rebuild/{kpi_id}", tags=["CSV"])
def csv_rebuild(
    kpi_id: int,
    db: Session = Depends(get_db),
    _: "User" = Depends(require_admin),
):
    """
    Rebuild file CSV untuk satu KPI dari data yang ada di database.

    Gunakan endpoint ini jika file CSV dan database tidak sinkron
    (misalnya setelah import langsung ke DB tanpa melalui website).

    Hanya admin yang dapat mengakses endpoint ini.
    """
    from services.csv_sync import rebuild_csv_from_db, find_csv_for_kpi

    csv_path = find_csv_for_kpi(kpi_id)
    if csv_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"File CSV untuk kpi_id={kpi_id} tidak ditemukan di folder data/. "
                   "Pastikan file sudah dibuat terlebih dahulu."
        )

    success = rebuild_csv_from_db(kpi_id, db)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal rebuild CSV untuk kpi_id={kpi_id}"
        )

    # Hitung jumlah baris setelah rebuild
    import pandas as pd
    try:
        row_count = len(pd.read_csv(csv_path))
    except Exception:
        row_count = -1

    return {
        "message":   f"CSV berhasil di-rebuild dari database",
        "kpi_id":    kpi_id,
        "filename":  csv_path.name,
        "row_count": row_count,
    }
