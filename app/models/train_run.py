from sqlalchemy import Column, Integer, JSON, String, Text

from app.core.database import Base
from app.models.base import TimestampMixin


class TrainRun(Base, TimestampMixin):
    __tablename__ = "train_run"

    id = Column(Integer, primary_key=True, autoincrement=True)
    module = Column(String(32), nullable=False, index=True)
    run_name = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, index=True)
    params = Column(JSON)
    metrics = Column(JSON)
    message = Column(Text)
