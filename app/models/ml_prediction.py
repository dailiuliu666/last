from sqlalchemy import Column, Date, Float, Integer, String, UniqueConstraint

from app.core.database import Base
from app.models.base import TimestampMixin


class MLPrediction(Base, TimestampMixin):
    __tablename__ = "ml_prediction"
    __table_args__ = (UniqueConstraint("model_id", "ts_code", "trade_date", name="uq_ml_prediction_key"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(64), nullable=False, index=True)
    ts_code = Column(String(16), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    predicted_value = Column(Float)
    score = Column(Float)
