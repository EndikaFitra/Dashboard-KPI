from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RealizationCreate(BaseModel):
    division_id: int
    kpi_id: int
    period_id: int
    year: int
    target: float = Field(..., gt=0)
    realization: float = Field(..., ge=0)


class RealizationUpdate(BaseModel):
    target: Optional[float] = Field(None, gt=0)
    realization: Optional[float] = Field(None, ge=0)


class RealizationResponse(BaseModel):
    fact_id: int
    division_id: int
    kpi_id: int
    period_id: int
    year: int
    target: float
    realization: float
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
