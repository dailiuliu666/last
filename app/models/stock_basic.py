from sqlalchemy import Boolean, Column, Date, String

from app.core.database import Base
from app.models.base import TimestampMixin


class StockBasic(Base, TimestampMixin):
    __tablename__ = "stock_basic"

    ts_code = Column(String(16), primary_key=True)
    symbol = Column(String(16), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    area = Column(String(64))
    industry = Column(String(64))
    market = Column(String(32))
    list_date = Column(Date)
    is_star_board = Column(Boolean, default=False, nullable=False)
