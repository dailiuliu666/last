from sqlalchemy import Boolean, Column, JSON, String, Text

from app.core.database import Base
from app.models.base import TimestampMixin


class FactorDefinition(Base, TimestampMixin):
    __tablename__ = "factor_definition"

    factor_id = Column(String(64), primary_key=True)
    factor_name = Column(String(128), nullable=False)
    factor_type = Column(String(32), nullable=False, index=True)
    formula = Column(Text, nullable=False)
    description = Column(Text)
    params = Column(JSON)
    is_builtin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
