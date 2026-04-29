"""
ETL Service — DEPRECATED.

Sejak revisi sistem ke perhitungan per-indikator (on-the-fly),
proses ETL batch Month→Quarter tidak lagi diperlukan.

Dashboard dan MCP Tools sekarang langsung menghitung dari
fact_kpi_performance menggunakan aggregation_service.calculate_division_report().

Endpoint /admin/run-etl dipertahankan untuk backward compatibility,
namun tidak melakukan operasi apapun yang berarti.
"""
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def run_etl(db: Session, year: int) -> dict:
    """
    DEPRECATED — Perhitungan sekarang dilakukan on-the-fly.
    Tidak ada lagi proses agregasi ke fact_kpi_quarterly.
    """
    logger.info(f"ETL endpoint called for year={year} — no-op (sistem sudah on-the-fly)")
    return {
        "status": "success",
        "year": year,
        "message": "ETL tidak diperlukan. Dashboard sudah menghitung langsung dari data realisasi.",
        "processed": 0,
        "upserted": 0,
    }


def run_etl_all_years(db: Session) -> list:
    """DEPRECATED — no-op."""
    from sqlalchemy import text
    rows = db.execute(text("SELECT DISTINCT year FROM fact_kpi_performance ORDER BY year")).fetchall()
    years = [r.year for r in rows]
    logger.info(f"ETL all years called — no-op for years {years}")
    return [
        {
            "status": "success",
            "year": yr,
            "message": "ETL tidak diperlukan. Perhitungan dilakukan on-the-fly.",
            "processed": 0,
            "upserted": 0,
        }
        for yr in years
    ]
