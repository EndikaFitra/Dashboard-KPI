import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from models.fact_raw import FactKpiPerformance
from schemas.kpi import RealizationCreate, RealizationUpdate, RealizationResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/realization", response_model=RealizationResponse, status_code=201)
def create_realization(
    payload: RealizationCreate,
    db: Session = Depends(get_db),
):
    """Insert a new raw KPI realization record."""
    logger.info(f"POST /kpi/realization division={payload.division_id} kpi={payload.kpi_id}")
    record = FactKpiPerformance(
        division_id=payload.division_id,
        kpi_id=payload.kpi_id,
        period_id=payload.period_id,
        year=payload.year,
        target=payload.target,
        realization=payload.realization,
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except Exception as e:
        db.rollback()
        logger.error(f"Insert realization error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    return record


@router.put("/realization/{fact_id}", response_model=RealizationResponse)
def update_realization(
    fact_id: int,
    payload: RealizationUpdate,
    db: Session = Depends(get_db),
):
    """Update target and/or realization for an existing raw record."""
    logger.info(f"PUT /kpi/realization/{fact_id}")
    record = db.query(FactKpiPerformance).filter(FactKpiPerformance.fact_id == fact_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Realization record {fact_id} not found")

    if payload.target is not None:
        record.target = payload.target
    if payload.realization is not None:
        record.realization = payload.realization

    try:
        db.commit()
        db.refresh(record)
    except Exception as e:
        db.rollback()
        logger.error(f"Update realization error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    return record
