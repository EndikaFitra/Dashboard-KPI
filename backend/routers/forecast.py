"""
Forecast Router — ARIMA Forecasting Endpoints

GET /forecast/mrr  →  MRR forecasting dengan model ARIMA
"""

import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from services.forecasting_service import get_mrr_forecast

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/mrr")
def forecast_mrr(
    p: int = Query(2, ge=0, le=10, description="ARIMA p (AR order)"),
    d: int = Query(0, ge=0, le=2, description="ARIMA d (differencing order)"),
    q: int = Query(3, ge=0, le=10, description="ARIMA q (MA order)"),
    n_forecast: int = Query(4, ge=1, le=12, description="Jumlah quarter forecast"),
    db: Session = Depends(get_db),
):
    """
    MRR Forecasting menggunakan ARIMA.

    - Default order: (2, 0, 3) berdasarkan uji ACF/PACF
    - Default forecast: 4 quarter ke depan
    - Data diambil dinamis dari data warehouse
    """
    logger.info(f"Forecast MRR: ARIMA({p},{d},{q}), steps={n_forecast}")
    return get_mrr_forecast(db, order=(p, d, q), n_forecast=n_forecast)
