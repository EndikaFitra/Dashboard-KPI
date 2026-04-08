from sqlalchemy import Column, Integer, String
from app.database import Base


class DimDivision(Base):
    __tablename__ = "dim_division"

    division_id = Column(Integer, primary_key=True, index=True)
    division_name = Column(String(100), nullable=False)
    evaluation_period = Column(String(1), nullable=False)  # H, Q, M
