"""
ETL Service — orchestrates the full ETL pipeline.
"""
import logging
from sqlalchemy.orm import Session
from services.aggregation_service import aggregate_monthly_to_quarterly

logger = logging.getLogger(__name__)


def run_etl(db: Session, year: int) -> dict:
    """
    Main ETL orchestrator:
      1. Read raw data from fact_kpi_performance
      2. Use dim_period_mapping (via aggregation_service)
      3. Aggregate Month → Quarter
      4. Store in fact_kpi_quarterly
    """
    logger.info(f"Starting ETL pipeline for year={year}")
    try:
        result = aggregate_monthly_to_quarterly(db, year)
        logger.info(f"ETL completed: {result}")
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"ETL failed for year={year}: {e}", exc_info=True)
        db.rollback()
        return {"status": "error", "year": year, "error": str(e)}


def run_etl_all_years(db: Session) -> list:
    """Run ETL for all distinct years found in fact_kpi_performance."""
    from sqlalchemy import text
    rows = db.execute(text("SELECT DISTINCT year FROM fact_kpi_performance ORDER BY year")).fetchall()
    years = [r.year for r in rows]
    if not years:
        logger.warning("No data found in fact_kpi_performance")
        return []

    results = []
    for yr in years:
        results.append(run_etl(db, yr))
    return results
