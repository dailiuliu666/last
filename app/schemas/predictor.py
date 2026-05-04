from typing import List, Optional

from pydantic import BaseModel


class FetchDataRequest(BaseModel):
    stock_code: str
    start_year: int


class PrepareDataRequest(BaseModel):
    csv_path: Optional[str] = None
    selected_features: List[str]
    selected_target: str
    look_back: int = 30


class TrainModelRequest(BaseModel):
    stock_code: str
    start_year: int
    selected_features: List[str]
    selected_target: str
    model_type: str = "LSTM"
    look_back: int = 30
    dropout_rate: float = 0.2
    learning_rate: float = 0.001
    epochs: int = 20
    batch_size: int = 32


class PredictFutureRequest(BaseModel):
    model_path: str
    stock_code: str
    start_year: int
    selected_features: List[str]
    selected_target: str
    look_back: int = 30
    days_to_predict: int = 5


class LoadModelRequest(BaseModel):
    model_path: str
