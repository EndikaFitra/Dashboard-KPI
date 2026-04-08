from sqlalchemy import Column, Integer, String
from app.database import Base


class DimPeriod(Base):
    __tablename__ = "dim_period"

    period_id = Column(Integer, primary_key=True, index=True)
    period_name = Column(String(10), nullable=False)   # Jan, Feb, Q1, H1, etc.
    period_type = Column(String(1), nullable=False)    # M, Q, H
    period_order = Column(Integer, nullable=False)
