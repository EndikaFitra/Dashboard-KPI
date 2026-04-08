from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class DimPeriodMapping(Base):
    __tablename__ = "dim_period_mapping"

    mapping_id = Column(Integer, primary_key=True, index=True)
    source_period_id = Column(Integer, ForeignKey("dim_period.period_id"), nullable=False)
    target_period_id = Column(Integer, ForeignKey("dim_period.period_id"), nullable=False)
    target_type = Column(String(1), nullable=False)  # Q
