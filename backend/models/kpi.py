from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class DimKpi(Base):
    __tablename__ = "dim_kpi"

    kpi_id = Column(Integer, primary_key=True, index=True)
    division_id = Column(Integer, ForeignKey("dim_division.division_id"), nullable=False, index=True)
    kpi_name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False)
    visualization_type = Column(String(50), default="bar")
    default_target = Column(Float, nullable=False)
    weight = Column(Float, nullable=False, default=0.0)  # % weight e.g. 35.0 for 35%
    evaluation_period = Column(String(1), nullable=False, default="Q")  # M=Monthly, Q=Quarterly, H=Half Year

    division = relationship("DimDivision", backref="kpis")
