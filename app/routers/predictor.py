from pathlib import Path

from fastapi import APIRouter

from app.schemas.predictor import FetchDataRequest, LoadModelRequest, PredictFutureRequest, TrainModelRequest
from app.services.predictor.data_fetcher import fetch_stock_data
from app.services.predictor.inference import predict_future_days, predict_one
from app.services.predictor.preprocess import prepare_sequences
from app.services.predictor.trainer import evaluate_test_set, load_saved_model, save_model, train_model


router = APIRouter(prefix="/api/predictor", tags=["predictor"])


def resolve_default_model_path(stock_code: str, model_type: str, selected_target: str) -> Path:
    artifact_name = f"{stock_code}_{model_type}_{selected_target}.keras"
    return Path("model_artifacts") / artifact_name


@router.post("/fetch-data")
def fetch_data(payload: FetchDataRequest):
    data = fetch_stock_data(payload.stock_code, payload.start_year)
    return {
        "success": True,
        "columns": list(data.columns),
        "count": len(data),
        "preview": data.head(10).to_dict(orient="records"),
    }


@router.post("/train")
def train(payload: TrainModelRequest):
    data = fetch_stock_data(payload.stock_code, payload.start_year)
    bundle = prepare_sequences(data, payload.selected_features, payload.selected_target, payload.look_back)
    model, history = train_model(
        bundle,
        payload.model_type,
        payload.look_back,
        len(payload.selected_features),
        payload.dropout_rate,
        payload.learning_rate,
        payload.epochs,
        payload.batch_size,
    )
    artifact_name = f"{payload.stock_code}_{payload.model_type}_{payload.selected_target}.keras"
    artifact_path = save_model(model, artifact_name)
    metrics = evaluate_test_set(model, bundle)
    look_back = payload.look_back
    start_index = bundle["train_size"] + look_back
    end_index = start_index + len(metrics["predictions"])
    test_dates = data["date"].iloc[start_index:end_index].dt.strftime("%Y-%m-%d").tolist()
    return {
        "success": True,
        "artifact_path": artifact_path,
        "history": {key: [float(item) for item in value] for key, value in history.history.items()},
        "metrics": metrics,
        "test_dates": test_dates,
    }


@router.post("/predict-one")
def predict_single(payload: TrainModelRequest):
    data = fetch_stock_data(payload.stock_code, payload.start_year)
    bundle = prepare_sequences(data, payload.selected_features, payload.selected_target, payload.look_back)
    model_path = resolve_default_model_path(payload.stock_code, payload.model_type, payload.selected_target)
    if not model_path.exists():
        return {"success": False, "message": f"Model file not found: {model_path}"}
    model = load_saved_model(str(model_path))
    return {"success": True, "result": predict_one(model, bundle)}


@router.post("/predict-future")
def predict_future(payload: PredictFutureRequest):
    if not Path(payload.model_path).exists():
        return {"success": False, "message": f"Model file not found: {payload.model_path}"}
    data = fetch_stock_data(payload.stock_code, payload.start_year)
    bundle = prepare_sequences(data, payload.selected_features, payload.selected_target, payload.look_back)
    model = load_saved_model(payload.model_path)
    result = predict_future_days(model, data, bundle, payload.selected_features, payload.look_back, payload.days_to_predict)
    return {"success": True, "predictions": result}


@router.get("/models")
def list_models():
    model_dir = Path("model_artifacts")
    model_dir.mkdir(parents=True, exist_ok=True)
    return {
        "success": True,
        "models": [
            {"name": item.name, "path": str(item)}
            for item in model_dir.glob("*.keras")
        ],
    }


@router.post("/load-model")
def load_model_meta(payload: LoadModelRequest):
    model_path = Path(payload.model_path)
    if not model_path.exists():
        return {"success": False, "message": f"Model file not found: {payload.model_path}"}
    load_saved_model(str(model_path))
    return {"success": True, "message": "Model loaded successfully", "model_path": str(model_path)}
