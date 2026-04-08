from sqlalchemy import Column, Integer, Float, String
from app.database import Base


class FactKpiQuarterly(Base):
    __tablename__ = "fact_kpi_quarterly"

    id = Column(Integer, primary_key=True, index=True)
    division_id = Column(Integer, nullable=False, index=True)
    kpi_id = Column(Integer, nullable=False, index=True)
    quarter = Column(String(2), nullable=False, index=True)  # Q1, Q2, Q3, Q4
    year = Column(Integer, nullable=False, index=True)
    target = Column(Float, nullable=False)
    realization = Column(Float, nullable=False)
    achievement = Column(Float, nullable=False)  # realization/target * 100
