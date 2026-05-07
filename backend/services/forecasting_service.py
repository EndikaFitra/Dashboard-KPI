"""
Forecasting Service — MRR ARIMA Forecasting

Mengambil data MRR dari data warehouse (fact_kpi_performance),
fit model ARIMA(p,d,q), forecast n langkah ke depan,
dan menghitung MAPE sebagai evaluasi.

Referensi kode asli: notebook ARIMA MRR milik user.
- ARIMA order default: (2, 0, 3)
- d=0 karena uji ADF menunjukkan data stasioner
- p=2 dan q=3 ditentukan dari plot ACF/PACF
"""

import logging
import numpy as np
import pandas as pd
from sqlalchemy import asc
from sqlalchemy.orm import Session
from statsmodels.tsa.arima.model import ARIMA

from models.fact_raw import FactKpiPerformance

logger = logging.getLogger(__name__)

# MRR KPI constants
MRR_KPI_ID = 8
MRR_DIVISION_ID = 3

# Mapping period_id → quarter order
PERIOD_TO_QUARTER = {13: 1, 14: 2, 15: 3, 16: 4}
QUARTER_LABELS = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}


def _build_time_series(rows: list) -> pd.Series:
    """
    Konversi rows dari DB menjadi pandas Series dengan DatetimeIndex quarterly.
    Setiap row memiliki atribut: year, period_id, realization.
    """
    records = []
    for row in rows:
        q = PERIOD_TO_QUARTER.get(row.period_id)
        if q is None:
            continue
        # Buat tanggal akhir quarter sebagai index (sesuai freq QE)
        month = q * 3  # Q1->3, Q2->6, Q3->9, Q4->12
        date = pd.Timestamp(year=row.year, month=month, day=1) + pd.offsets.MonthEnd(0)
        records.append({"date": date, "mrr": float(row.realization)})

    df = pd.DataFrame(records)
    df = df.sort_values("date").drop_duplicates(subset="date", keep="last")
    df = df.set_index("date")
    df = df.asfreq("QE")

    return df["mrr"]


def _generate_forecast_labels(last_year: int, last_quarter: int, steps: int) -> list:
    """
    Generate label string untuk forecast periods.
    Misal: last=2026-Q1, steps=4 → ['2026-Q2', '2026-Q3', '2026-Q4', '2027-Q1']
    """
    labels = []
    y, q = last_year, last_quarter
    for _ in range(steps):
        q += 1
        if q > 4:
            q = 1
            y += 1
        labels.append(f"{y}-{QUARTER_LABELS[q]}")
    return labels


def get_mrr_forecast(
    db: Session,
    order: tuple = (2, 0, 3),
    n_forecast: int = 4,
) -> dict:
    """
    Main forecasting function.

    1. Query data MRR dari fact_kpi_performance
    2. Bentuk time series quarterly
    3. Fit ARIMA(p, d, q)
    4. Forecast n_forecast quarter ke depan
    5. Hitung MAPE dari fitted vs actual
    6. Return structured dict untuk frontend

    Parameters
    ----------
    db : Session
        SQLAlchemy database session
    order : tuple
        ARIMA (p, d, q) order. Default (2, 0, 3).
    n_forecast : int
        Jumlah quarter yang di-forecast. Default 4.

    Returns
    -------
    dict
        {kpi_name, arima_order, data_points, mape, actual, fitted, forecast}
    """
    # ── 1. Query data MRR ────────────────────────────────────────────────── #
    rows = (
        db.query(FactKpiPerformance)
        .filter(
            FactKpiPerformance.kpi_id == MRR_KPI_ID,
            FactKpiPerformance.division_id == MRR_DIVISION_ID,
        )
        .order_by(
            asc(FactKpiPerformance.year),
            asc(FactKpiPerformance.period_id),
        )
        .all()
    )

    if len(rows) < 5:
        return {
            "error": "Data MRR tidak cukup untuk forecasting (minimal 5 data points).",
            "data_points": len(rows),
        }

    # ── 2. Bentuk time series ────────────────────────────────────────────── #
    series = _build_time_series(rows)
    logger.info(f"MRR time series: {len(series)} data points, range {series.index[0]} – {series.index[-1]}")

    # ── 3. Fit ARIMA ─────────────────────────────────────────────────────── #
    model = ARIMA(series, order=order)
    model_fit = model.fit()
    logger.info(f"ARIMA{order} fitted. AIC={model_fit.aic:.2f}")

    # ── 4. Fitted values ─────────────────────────────────────────────────── #
    fitted_values = model_fit.fittedvalues

    # ── 5. Forecast ──────────────────────────────────────────────────────── #
    forecast_result = model_fit.get_forecast(steps=n_forecast)
    forecast_mean = forecast_result.predicted_mean

    # ── 6. MAPE ──────────────────────────────────────────────────────────── #
    # Persis seperti kode notebook user:
    #   mape = np.mean(np.abs((actual - fitted) / actual)) * 100
    actual_values = series.values
    fitted_arr = fitted_values.values
    mape = float(np.mean(np.abs((actual_values - fitted_arr) / actual_values)) * 100)
    # Hitung MAE (Mean Absolute Error)
    mae = float(np.mean(np.abs(actual_values - fitted_arr)))

    # ── 7. Build response ────────────────────────────────────────────────── #
    # Tentukan year/quarter terakhir dari data
    last_row = rows[-1]
    last_year = last_row.year
    last_quarter = PERIOD_TO_QUARTER.get(last_row.period_id, 4)

    # Actual series
    actual_list = []
    for row in rows:
        q = PERIOD_TO_QUARTER.get(row.period_id)
        if q is None:
            continue
        actual_list.append({
            "label": f"{row.year}-{QUARTER_LABELS[q]}",
            "value": float(row.realization),
        })

    # Fitted series (aligned with actual)
    fitted_list = []
    for i, row in enumerate(rows):
        q = PERIOD_TO_QUARTER.get(row.period_id)
        if q is None:
            continue
        label = f"{row.year}-{QUARTER_LABELS[q]}"
        fv = float(fitted_arr[i]) if i < len(fitted_arr) else None
        fitted_list.append({"label": label, "value": fv})

    # Forecast series
    forecast_labels = _generate_forecast_labels(last_year, last_quarter, n_forecast)
    forecast_list = []
    for i, label in enumerate(forecast_labels):
        forecast_list.append({
            "label": label,
            "value": float(forecast_mean.iloc[i]),
        })

    return {
        "kpi_name": "MRR",
        "arima_order": list(order),
        "data_points": len(series),
        "mape": round(mape, 4),
        # "aic": round(float(model_fit.aic), 2),
        "mae": round(mae, 2), # Meggantikan aic
        "actual": actual_list,
        "fitted": fitted_list,
        "forecast": forecast_list,
    }
