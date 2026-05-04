from sqlalchemy import Column, Date, Float, Integer, String, UniqueConstraint

from app.core.database import Base
from app.models.base import TimestampMixin


class StockDaily(Base, TimestampMixin):
    __tablename__ = "stock_daily"
    __table_args__ = (UniqueConstraint("ts_code", "trade_date", name="uq_stock_daily_code_date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(16), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    vol = Column(Float)
    amount = Column(Float)
