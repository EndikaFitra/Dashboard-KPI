from sqlalchemy import Column, Integer, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base


class FactKpiPerformance(Base):
    __tablename__ = "fact_kpi_performance"

    fact_id = Column(Integer, primary_key=True, index=True)
    division_id = Column(Integer, nullable=False, index=True)
    kpi_id = Column(Integer, nullable=False, index=True)
    period_id = Column(Integer, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    target = Column(Float, nullable=False)
    realization = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
