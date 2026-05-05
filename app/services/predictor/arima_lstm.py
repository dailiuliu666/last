from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import List
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA, ARIMAResults
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import Dense, Dropout, Input, LSTM
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.optimizers import Adam

from app.core.config import settings
from app.services.predictor.metrics import evaluate_regression


ARIMA_LSTM_TYPE = "ARIMA-LSTM"


def is_arima_lstm_artifact(model_path: str) -> bool:
    return _meta_path(model_path).exists()


def _meta_path(model_path: str | Path) -> Path:
    return Path(model_path).with_suffix(".arima_lstm.joblib")


def _arima_path(model_path: str | Path) -> Path:
    return Path(model_path).with_suffix(".arima.pkl")


def _fit_arima(series: np.ndarray):
    last_error: Exception | None = None
    for order in ((5, 1, 0), (2, 1, 1), (1, 1, 0)):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = ARIMA(series, order=order).fit()
            return result, order
        except Exception as exc:
            last_error = exc
    raise ValueError(f"ARIMA 拟合失败: {last_error}")


def _fitted_values(arima_result, series: np.ndarray) -> np.ndarray:
    fitted = np.asarray(arima_result.predict(start=0, end=len(series) - 1), dtype=float)
    if len(fitted) != len(series):
        fitted = np.resize(fitted, len(series))
    fitted = np.where(np.isfinite(fitted), fitted, series)
    fitted[0] = series[0]
    return fitted


def _create_dataset(feature_scaled: np.ndarray, residual_scaled: np.ndarray, look_back: int):
    x_data = []
    y_data = []
    indices = []
    for i in range(len(feature_scaled) - look_back):
        x_data.append(feature_scaled[i : i + look_back])
        y_data.append(residual_scaled[i + look_back, 0])
        indices.append(i + look_back)
    return np.array(x_data), np.array(y_data), np.array(indices)


def _build_residual_lstm(look_back: int, n_features: int, dropout_rate: float, learning_rate: float):
    model = Sequential(
        [
            Input(shape=(look_back, n_features)),
            LSTM(32, return_sequences=True),
            Dropout(dropout_rate),
            LSTM(16),
            Dropout(dropout_rate),
            Dense(1),
        ]
    )
    model.compile(optimizer=Adam(learning_rate=learning_rate), loss="mean_squared_error", metrics=["mae"])
    return model


def train_arima_lstm(
    data: pd.DataFrame,
    selected_features: List[str],
    selected_target: str,
    look_back: int,
    dropout_rate: float,
    learning_rate: float,
    epochs: int,
    batch_size: int,
):
    if data is None or data.empty:
        raise ValueError("Input data is empty")
    if selected_target not in data.columns:
        raise ValueError(f"Target column not found: {selected_target}")
    if not selected_features:
        raise ValueError("selected_features cannot be empty")

    target_series = data[selected_target].astype(float).values
    arima_result, arima_order = _fit_arima(target_series)
    arima_fitted = _fitted_values(arima_result, target_series)
    residual = target_series - arima_fitted

    feature_scaler = StandardScaler()
    residual_scaler = StandardScaler()
    feature_scaled = feature_scaler.fit_transform(data[selected_features].astype(float).values)
    residual_scaled = residual_scaler.fit_transform(residual.reshape(-1, 1))

    train_size = int(len(feature_scaled) * 0.8)
    x_train, y_train, _ = _create_dataset(feature_scaled[:train_size], residual_scaled[:train_size], look_back)
    x_test, y_test, local_test_indices = _create_dataset(feature_scaled[train_size:], residual_scaled[train_size:], look_back)
    if len(x_train) == 0 or len(x_test) == 0:
        raise ValueError("Not enough samples for current look_back")

    model = _build_residual_lstm(look_back, len(selected_features), dropout_rate, learning_rate)
    early_stop = EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True, verbose=0)
    history = model.fit(
        x_train,
        y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(x_test, y_test),
        callbacks=[early_stop],
        verbose=0,
    )

    global_test_indices = train_size + local_test_indices
    residual_pred_scaled = model.predict(x_test, verbose=0)
    residual_pred = residual_scaler.inverse_transform(residual_pred_scaled).flatten()
    y_pred = arima_fitted[global_test_indices] + residual_pred
    y_true = target_series[global_test_indices]
    metrics = _metrics(y_true, y_pred)

    bundle = {
        "model": model,
        "history": history,
        "metrics": metrics,
        "test_dates": data["date"].iloc[global_test_indices].dt.strftime("%Y-%m-%d").tolist()
        if "date" in data.columns
        else [],
        "arima_result": arima_result,
        "arima_order": arima_order,
        "feature_scaler": feature_scaler,
        "residual_scaler": residual_scaler,
        "selected_features": selected_features,
        "selected_target": selected_target,
        "look_back": look_back,
        "last_target_values": target_series[-look_back:].tolist(),
    }
    return bundle


def save_arima_lstm_bundle(bundle: dict, file_name: str) -> str:
    model_dir = Path(settings.predictor_model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / file_name
    bundle["model"].save(model_path)
    bundle["arima_result"].save(_arima_path(model_path))
    joblib.dump(
        {
            "model_type": ARIMA_LSTM_TYPE,
            "arima_order": bundle["arima_order"],
            "feature_scaler": bundle["feature_scaler"],
            "residual_scaler": bundle["residual_scaler"],
            "selected_features": bundle["selected_features"],
            "selected_target": bundle["selected_target"],
            "look_back": bundle["look_back"],
            "last_target_values": bundle["last_target_values"],
        },
        _meta_path(model_path),
    )
    return str(model_path)


def load_arima_lstm_bundle(model_path: str):
    return {
        "model": load_model(model_path),
        "arima_result": ARIMAResults.load(_arima_path(model_path)),
        "meta": joblib.load(_meta_path(model_path)),
    }


def predict_arima_lstm_one(model_path: str, data: pd.DataFrame, selected_features: List[str], selected_target: str, look_back: int):
    bundle = load_arima_lstm_bundle(model_path)
    model = bundle["model"]
    meta = bundle["meta"]
    arima_result = bundle["arima_result"]
    selected_features = meta.get("selected_features") or selected_features
    selected_target = meta.get("selected_target") or selected_target
    look_back = int(meta.get("look_back") or look_back)

    target_series = data[selected_target].astype(float).values
    feature_scaled = meta["feature_scaler"].transform(data[selected_features].astype(float).values)
    train_size = int(len(feature_scaled) * 0.8)
    x_test, _, local_indices = _create_dataset(feature_scaled[train_size:], np.zeros((len(feature_scaled[train_size:]), 1)), look_back)
    if len(x_test) == 0:
        raise ValueError("Not enough samples for current look_back")

    global_index = train_size + local_indices[-1]
    residual_scaled = model.predict(x_test[-1:].reshape(1, look_back, len(selected_features)), verbose=0)
    residual_value = meta["residual_scaler"].inverse_transform(residual_scaled)[0, 0]
    arima_fitted = _fitted_values(arima_result, target_series)
    predicted = float(arima_fitted[min(global_index, len(arima_fitted) - 1)] + residual_value)
    true_value = float(target_series[min(global_index, len(target_series) - 1)])
    return {
        "predicted_value": predicted,
        "true_value": true_value,
        "absolute_error": float(abs(predicted - true_value)),
        "arima_component": float(arima_fitted[min(global_index, len(arima_fitted) - 1)]),
        "lstm_residual_component": float(residual_value),
    }


def predict_arima_lstm_future(
    model_path: str,
    data: pd.DataFrame,
    selected_features: List[str],
    selected_target: str,
    look_back: int,
    days_to_predict: int,
):
    bundle = load_arima_lstm_bundle(model_path)
    model = bundle["model"]
    meta = bundle["meta"]
    arima_result = bundle["arima_result"]
    selected_features = meta.get("selected_features") or selected_features
    selected_target = meta.get("selected_target") or selected_target
    look_back = int(meta.get("look_back") or look_back)

    feature_scaler = meta["feature_scaler"]
    residual_scaler = meta["residual_scaler"]
    last_feature_data = data[selected_features].astype(float).values[-look_back:]
    last_sequence = feature_scaler.transform(last_feature_data).reshape(1, look_back, len(selected_features))
    arima_forecast = np.asarray(arima_result.forecast(steps=days_to_predict), dtype=float)

    predictions = []
    for index in range(days_to_predict):
        residual_scaled = model.predict(last_sequence, verbose=0)
        residual_value = residual_scaler.inverse_transform(residual_scaled)[0, 0]
        final_value = float(arima_forecast[index] + residual_value)
        predictions.append(final_value)

        next_frame = np.roll(last_sequence, -1, axis=1)
        next_frame[0, -1, :] = next_frame[0, -2, :]
        for feature_index, feature_name in enumerate(selected_features):
            if feature_name == selected_target:
                next_frame[0, -1, feature_index] = (
                    final_value - feature_scaler.mean_[feature_index]
                ) / feature_scaler.scale_[feature_index]
        last_sequence = next_frame

    future_dates = []
    current_date = pd.to_datetime(data["date"].iloc[-1]).to_pydatetime()
    while len(future_dates) < days_to_predict:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:
            future_dates.append(current_date.strftime("%Y-%m-%d"))

    return [
        {
            "date": date_value,
            "predicted_price": float(price),
            "model_type": ARIMA_LSTM_TYPE,
        }
        for date_value, price in zip(future_dates, predictions)
    ]


def _metrics(y_true: np.ndarray, y_pred: np.ndarray):
    return evaluate_regression(y_true, y_pred)


def history_namespace(history: dict):
    return SimpleNamespace(history=history)
