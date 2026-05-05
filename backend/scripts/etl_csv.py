"""
ETL Script — CSV to Data Warehouse
====================================
Membaca semua file CSV dari folder backend/data/, lalu melakukan
upsert ke tabel fact_kpi_performance di PostgreSQL.

Strategi upsert (Fase 4):
  INSERT INTO fact_kpi_performance (...)
  ON CONFLICT (kpi_id, period_id, year)
  DO UPDATE SET target = EXCLUDED.target, realization = EXCLUDED.realization

Cara pakai:
  # Load semua file CSV (semua tahun)
  python scripts/etl_csv.py --all

  # Load spesifik satu tahun
  python scripts/etl_csv.py --year 2025

  # Preview tanpa menyimpan ke DB (dry-run)
  python scripts/etl_csv.py --all --dry-run
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime

# ── Path setup ────────────────────────────────────────────────────────────── #
# Agar script bisa dijalankan dari folder backend/ maupun root project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

from app.database import SessionLocal, engine, Base
import models  # noqa — pastikan semua ORM model terdaftar

# ── Logging ───────────────────────────────────────────────────────────────── #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Konstanta ─────────────────────────────────────────────────────────────── #
DATA_DIR = Path(__file__).parent.parent / "data"

REQUIRED_COLUMNS = {"division_id", "kpi_id", "period_id", "year", "target", "realization"}


# ═══════════════════════════════════════════════════════════════════════════ #
# FASE 4 — Fungsi Upsert (aman dijalankan berkali-kali)
# ═══════════════════════════════════════════════════════════════════════════ #
def _ensure_unique_constraint(db):
    """
    Pastikan UNIQUE constraint (kpi_id, period_id, year) ada di tabel.
    Jika sudah ada, skip. Ini dijalankan otomatis saat ETL pertama kali.
    """
    check_sql = text("""
        SELECT COUNT(*) FROM information_schema.table_constraints
        WHERE table_name = 'fact_kpi_performance'
          AND constraint_name = 'uq_kpi_period_year'
    """)
    count = db.execute(check_sql).scalar()
    if count == 0:
        logger.info("Menambahkan UNIQUE constraint (uq_kpi_period_year)...")
        db.execute(text("""
            ALTER TABLE fact_kpi_performance
            ADD CONSTRAINT uq_kpi_period_year UNIQUE (kpi_id, period_id, year)
        """))
        db.commit()
        logger.info("✓ UNIQUE constraint berhasil ditambahkan.")
    else:
        logger.debug("UNIQUE constraint sudah ada, skip.")


def _upsert_batch(db, records: list[dict], dry_run: bool = False) -> tuple[int, int]:
    """
    Lakukan upsert batch ke fact_kpi_performance.
    Mengembalikan (inserted_count, updated_count).

    ON CONFLICT (kpi_id, period_id, year) → UPDATE target & realization.
    """
    if not records:
        return 0, 0

    if dry_run:
        logger.info(f"  [DRY-RUN] Akan upsert {len(records)} baris (tidak disimpan).")
        return len(records), 0

    upsert_sql = text("""
        INSERT INTO fact_kpi_performance
            (division_id, kpi_id, period_id, year, target, realization)
        VALUES
            (:division_id, :kpi_id, :period_id, :year, :target, :realization)
        ON CONFLICT (kpi_id, period_id, year)
        DO UPDATE SET
            target      = EXCLUDED.target,
            realization = EXCLUDED.realization,
            division_id = EXCLUDED.division_id
        RETURNING (xmax = 0) AS is_insert
    """)

    inserted = 0
    updated = 0
    for rec in records:
        result = db.execute(upsert_sql, rec).fetchone()
        if result and result[0]:
            inserted += 1
        else:
            updated += 1

    db.commit()
    return inserted, updated


# ═══════════════════════════════════════════════════════════════════════════ #
# FASE 3 — Alur kerja ETL: Baca → Validasi → Upsert
# ═══════════════════════════════════════════════════════════════════════════ #
def _load_and_validate_csv(filepath: Path, year_filter: int | None = None) -> pd.DataFrame | None:
    """
    Langkah E (Extract) + T (Transform):
    - Baca file CSV
    - Validasi kolom wajib ada
    - Filter per tahun jika diminta
    - Buang baris yang mengandung nilai null atau tidak valid
    """
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        logger.error(f"  ✗ Gagal membaca {filepath.name}: {e}")
        return None

    # Validasi kolom
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        logger.error(f"  ✗ {filepath.name}: kolom tidak lengkap → {missing_cols}")
        return None

    # Buang kolom yang tidak diperlukan
    df = df[list(REQUIRED_COLUMNS)].copy()

    # Buang baris yang ada null
    before = len(df)
    df.dropna(inplace=True)
    dropped = before - len(df)
    if dropped:
        logger.warning(f"  ⚠ {filepath.name}: {dropped} baris dibuang karena nilai kosong")

    # Konversi tipe data
    try:
        df["division_id"] = df["division_id"].astype(int)
        df["kpi_id"]      = df["kpi_id"].astype(int)
        df["period_id"]   = df["period_id"].astype(int)
        df["year"]        = df["year"].astype(int)
        df["target"]      = df["target"].astype(float)
        df["realization"] = df["realization"].astype(float)
    except Exception as e:
        logger.error(f"  ✗ {filepath.name}: gagal konversi tipe data → {e}")
        return None

    # Filter berdasarkan tahun jika diminta
    if year_filter is not None:
        df = df[df["year"] == year_filter]

    if df.empty:
        logger.info(f"  ℹ {filepath.name}: tidak ada data untuk tahun {year_filter}")
        return None

    return df


def _validate_references(db, df: pd.DataFrame, filename: str) -> pd.DataFrame:
    """
    Validasi referensial: pastikan kpi_id dan period_id yang ada di CSV
    memang terdaftar di dim_kpi dan dim_period.
    Baris yang tidak valid akan di-drop dengan peringatan.
    """
    # Ambil valid IDs dari database
    valid_kpi_ids    = {r[0] for r in db.execute(text("SELECT kpi_id FROM dim_kpi")).fetchall()}
    valid_period_ids = {r[0] for r in db.execute(text("SELECT period_id FROM dim_period")).fetchall()}

    before = len(df)

    invalid_kpi = ~df["kpi_id"].isin(valid_kpi_ids)
    if invalid_kpi.any():
        bad = df[invalid_kpi]["kpi_id"].unique().tolist()
        logger.warning(f"  ⚠ {filename}: kpi_id tidak valid di DB → {bad} (baris dibuang)")
        df = df[~invalid_kpi]

    invalid_period = ~df["period_id"].isin(valid_period_ids)
    if invalid_period.any():
        bad = df[invalid_period]["period_id"].unique().tolist()
        logger.warning(f"  ⚠ {filename}: period_id tidak valid di DB → {bad} (baris dibuang)")
        df = df[~invalid_period]

    dropped = before - len(df)
    if dropped:
        logger.warning(f"  ⚠ {filename}: total {dropped} baris dibuang karena referensi tidak valid")

    return df


def run_etl(year_filter: int | None = None, dry_run: bool = False) -> dict:
    """
    Fungsi ETL utama.
    Dipanggil dari CLI (main) maupun dari endpoint FastAPI (Fase 6).

    Returns:
        dict dengan summary hasil ETL
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"ETL STARTED — {'ALL YEARS' if year_filter is None else f'YEAR {year_filter}'}")
    if dry_run:
        logger.info("MODE: DRY-RUN (tidak ada perubahan ke database)")
    logger.info("=" * 60)

    # Pastikan tabel ada
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    summary = {
        "status":         "success",
        "year_filter":    year_filter,
        "dry_run":        dry_run,
        "files_processed": 0,
        "files_skipped":  0,
        "total_inserted": 0,
        "total_updated":  0,
        "total_rows":     0,
        "errors":         [],
        "started_at":     start_time.isoformat(),
    }

    try:
        # Fase 4: pastikan unique constraint ada (idempoten)
        if not dry_run:
            _ensure_unique_constraint(db)

        # Temukan semua file CSV di folder data/
        csv_files = sorted(DATA_DIR.glob("*.csv"))
        if not csv_files:
            logger.warning(f"Tidak ada file CSV di folder: {DATA_DIR}")
            summary["status"] = "warning"
            summary["errors"].append(f"Tidak ada file CSV di {DATA_DIR}")
            return summary

        logger.info(f"Ditemukan {len(csv_files)} file CSV di {DATA_DIR}")
        logger.info("-" * 60)

        for filepath in csv_files:
            logger.info(f"Memproses: {filepath.name}")

            # EXTRACT + TRANSFORM
            df = _load_and_validate_csv(filepath, year_filter)
            if df is None:
                summary["files_skipped"] += 1
                continue

            # Validasi referensial ke database
            df = _validate_references(db, df, filepath.name)
            if df.empty:
                summary["files_skipped"] += 1
                continue

            # LOAD — upsert ke fact_kpi_performance
            records = df.to_dict(orient="records")
            inserted, updated = _upsert_batch(db, records, dry_run=dry_run)

            logger.info(f"  ✓ {filepath.name}: {len(records)} baris "
                        f"(+{inserted} baru, ~{updated} diperbarui)")

            summary["files_processed"] += 1
            summary["total_inserted"]  += inserted
            summary["total_updated"]   += updated
            summary["total_rows"]      += len(records)

    except Exception as e:
        logger.error(f"ETL GAGAL: {e}", exc_info=True)
        summary["status"] = "error"
        summary["errors"].append(str(e))
        db.rollback()
    finally:
        db.close()

    duration = (datetime.now() - start_time).total_seconds()
    summary["duration_seconds"] = round(duration, 2)
    summary["finished_at"] = datetime.now().isoformat()

    logger.info("=" * 60)
    if summary["status"] == "success":
        logger.info(f"✅ ETL SELESAI dalam {duration:.1f} detik")
        logger.info(f"   File diproses  : {summary['files_processed']}")
        logger.info(f"   File dilewati  : {summary['files_skipped']}")
        logger.info(f"   Total baris    : {summary['total_rows']}")
        logger.info(f"   Baru (INSERT)  : {summary['total_inserted']}")
        logger.info(f"   Diperbarui     : {summary['total_updated']}")
    else:
        logger.error(f"❌ ETL GAGAL: {summary['errors']}")
    logger.info("=" * 60)

    return summary


# ═══════════════════════════════════════════════════════════════════════════ #
# FASE 5 — Entry point CLI
# ═══════════════════════════════════════════════════════════════════════════ #
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ETL: Load data CSV ke Data Warehouse PostgreSQL"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="Load semua data dari seluruh tahun yang ada di CSV",
    )
    group.add_argument(
        "--year",
        type=int,
        metavar="YYYY",
        help="Load data untuk satu tahun tertentu (contoh: --year 2025)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview proses ETL tanpa menyimpan apapun ke database",
    )

    args = parser.parse_args()

    year_filter = None if args.all else args.year
    result = run_etl(year_filter=year_filter, dry_run=args.dry_run)

    # Exit code: 0 = sukses, 1 = ada error
    sys.exit(0 if result["status"] in ("success", "warning") else 1)
