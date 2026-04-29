import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from services.mcp_tools import (
    get_overview_kpi,
    get_division_kpi,
    get_kpi_trend,
    get_underperforming_kpi,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/years")
def get_available_years(db: Session = Depends(get_db)):
    """Return distinct years that have data in fact_kpi_performance, sorted descending."""
    from sqlalchemy import text
    rows = db.execute(text(
        "SELECT DISTINCT year FROM fact_kpi_performance ORDER BY year DESC"
    )).fetchall()
    return [r.year for r in rows]


@router.get("/overview")
def overview(
    year: int = Query(2025, description="Year to query"),
    db: Session = Depends(get_db),
):
    """Company-wide KPI overview for a given year."""
    logger.info(f"GET /dashboard/overview year={year}")
    try:
        return get_overview_kpi(db, year)
    except Exception as e:
        logger.error(f"Overview error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/division/{division_id}")
def division_detail(
    division_id: int,
    year: int = Query(2025, description="Year to query"),
    db: Session = Depends(get_db),
):
    """KPI detail for a single division."""
    logger.info(f"GET /dashboard/division/{division_id} year={year}")
    try:
        result = get_division_kpi(db, division_id, year)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Division detail error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend/{division_id}")
def trend(
    division_id: int,
    year: int = Query(2025, description="Current year"),
    db: Session = Depends(get_db),
):
    """Year-over-year trend for a division."""
    logger.info(f"GET /dashboard/trend/{division_id} year={year}")
    try:
        result = get_kpi_trend(db, division_id, year)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trend error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/underperform")
def underperform(
    year: int = Query(2025, description="Year to query"),
    db: Session = Depends(get_db),
):
    """KPIs with achievement < 80% for a given year."""
    logger.info(f"GET /dashboard/underperform year={year}")
    try:
        return get_underperforming_kpi(db, year)
    except Exception as e:
        logger.error(f"Underperform error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
