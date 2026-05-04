from sqlalchemy import Column, Date, Float, Integer, String, UniqueConstraint

from app.core.database import Base
from app.models.base import TimestampMixin


class FactorValue(Base, TimestampMixin):
    __tablename__ = "factor_value"
    __table_args__ = (UniqueConstraint("ts_code", "trade_date", "factor_id", name="uq_factor_value_key"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(16), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    factor_id = Column(String(64), nullable=False, index=True)
    factor_value = Column(Float)
    z_score = Column(Float)
