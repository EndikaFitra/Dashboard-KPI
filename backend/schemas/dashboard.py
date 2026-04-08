from pydantic import BaseModel
from typing import List, Optional


class KpiSummary(BaseModel):
    kpi_id: int
    kpi_name: str
    unit: str
    visualization_type: str
    weight: float
    quarter: str
    year: int
    target: float
    realization: float
    achievement: float
    status: str  # green, yellow, red

    model_config = {"from_attributes": True}


class DivisionOverview(BaseModel):
    division_id: int
    division_name: str
    evaluation_period: str
    avg_achievement: float
    status: str
    total_kpis: int
    achieved_kpis: int   # >= 100
    warning_kpis: int    # 80-99
    danger_kpis: int     # < 80


class OverviewResponse(BaseModel):
    year: int
    divisions: List[DivisionOverview]
    company_avg: float
    total_kpis: int
    achieved_kpis: int
    warning_kpis: int
    danger_kpis: int


class DivisionDetailResponse(BaseModel):
    division_id: int
    division_name: str
    evaluation_period: str
    year: int
    avg_achievement: float
    status: str
    kpis: List[KpiSummary]


class TrendPoint(BaseModel):
    period: str
    achievement: float
    year: int


class TrendResponse(BaseModel):
    division_id: int
    division_name: str
    current_year: int
    current_trend: List[TrendPoint]
    previous_trend: List[TrendPoint]


class UnderperformKpi(BaseModel):
    division_id: int
    division_name: str
    kpi_id: int
    kpi_name: str
    unit: str
    quarter: str
    year: int
    target: float
    realization: float
    achievement: float
    gap: float


class UnderperformResponse(BaseModel):
    year: int
    count: int
    items: List[UnderperformKpi]
