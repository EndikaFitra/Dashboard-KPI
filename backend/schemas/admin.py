"""Pydantic schemas for admin data management endpoints."""
from pydantic import BaseModel
from typing import Optional


# ── dim_kpi ──────────────────────────────────────────────────────────────── #
class KpiCreate(BaseModel):
    division_id:       int
    kpi_name:          str
    unit:              str
    visualization_type: str = "bar"
    default_target:    float
    weight:            float  # 0.0 – 100.0


class KpiUpdate(BaseModel):
    kpi_name:          Optional[str]   = None
    unit:              Optional[str]   = None
    visualization_type: Optional[str] = None
    default_target:    Optional[float] = None
    weight:            Optional[float] = None


class KpiResponse(BaseModel):
    kpi_id:            int
    division_id:       int
    kpi_name:          str
    unit:              str
    visualization_type: str
    default_target:    float
    weight:            float

    model_config = {"from_attributes": True}


# ── fact_kpi_performance ─────────────────────────────────────────────────── #
class RealizationCreate(BaseModel):
    division_id: int
    kpi_id:      int
    period_id:   int
    year:        int
    target:      float
    realization: float


class RealizationUpdate(BaseModel):
    target:      Optional[float] = None
    realization: Optional[float] = None


class RealizationResponse(BaseModel):
    fact_id:     int
    division_id: int
    kpi_id:      int
    period_id:   int
    year:        int
    target:      float
    realization: float

    model_config = {"from_attributes": True}


# ── ETL ──────────────────────────────────────────────────────────────────── #
class EtlRequest(BaseModel):
    year: int = 2025
    all_years: bool = False
