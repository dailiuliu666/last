from typing import List, Optional

from pydantic import BaseModel, Field


class CustomFactorCreate(BaseModel):
    factor_id: str
    factor_name: str
    factor_type: str
    formula: str
    description: Optional[str] = None
    direction: int = Field(default=1, description="1 means higher is better, -1 means lower is better")
    weight: float = Field(default=1.0, ge=0)


class QuantModelCreate(BaseModel):
    model_id: str
    model_name: str
    model_type: str
    target_type: str
    factor_list: List[str] = Field(default_factory=list)


class QuantModelTrainRequest(BaseModel):
    model_id: str
    start_date: str
    end_date: str


class QuantModelPredictRequest(BaseModel):
    model_id: str
    trade_date: str


class QuantScoreRequest(BaseModel):
    trade_date: str
    factor_ids: List[str] = Field(default_factory=list)
