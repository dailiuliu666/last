from sqlalchemy import Column, JSON, String, Text

from app.core.database import Base
from app.models.base import TimestampMixin


class MLModelDefinition(Base, TimestampMixin):
    __tablename__ = "ml_model_definition"

    model_id = Column(String(64), primary_key=True)
    model_name = Column(String(128), nullable=False)
    model_type = Column(String(32), nullable=False)
    target_type = Column(String(32), nullable=False)
    factor_list = Column(JSON, nullable=False)
    model_params = Column(JSON)
    training_config = Column(JSON)
    artifact_path = Column(Text)
