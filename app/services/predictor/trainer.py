from pathlib import Path

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import Conv1D, Dense, Dropout, Flatten, Input, LSTM, MaxPooling1D
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.optimizers import Adam

from app.core.config import settings


def build_model(model_type: str, look_back: int, n_features: int, dropout_rate: float, learning_rate: float):
    model = Sequential()
    model.add(Input(shape=(look_back, n_features)))

    if model_type == "LSTM":
        model.add(LSTM(32, return_sequences=True))
        model.add(Dropout(dropout_rate))
        model.add(LSTM(32))
        model.add(Dropout(dropout_rate))
    elif model_type == "CNN":
        model.add(Conv1D(filters=64, kernel_size=3, activation="relu"))
        model.add(MaxPooling1D(pool_size=2))
        model.add(Conv1D(filters=32, kernel_size=3, activation="relu"))
        model.add(MaxPooling1D(pool_size=2))
        model.add(Flatten())
        model.add(Dense(64, activation="relu"))
        model.add(Dropout(dropout_rate))
    elif model_type == "CNN-LSTM":
        model.add(Conv1D(filters=64, kernel_size=3, activation="relu"))
        model.add(MaxPooling1D(pool_size=2))
        model.add(Conv1D(filters=32, kernel_size=3, activation="relu"))
        model.add(LSTM(32, activation="tanh"))
        model.add(Dropout(dropout_rate))
    else:
        raise ValueError(f"Unsupported model_type: {model_type}")

    model.add(Dense(1))
    model.compile(optimizer=Adam(learning_rate=learning_rate), loss="mean_squared_error", metrics=["mae"])
    return model


def train_model(train_bundle: dict, model_type: str, look_back: int, n_features: int, dropout_rate: float, learning_rate: float, epochs: int, batch_size: int):
    model = build_model(model_type, look_back, n_features, dropout_rate, learning_rate)
    early_stop = EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True, verbose=0)
    history = model.fit(
        train_bundle["x_train"],
        train_bundle["y_train"],
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(train_bundle["x_test"], train_bundle["y_test"]),
        callbacks=[early_stop],
        verbose=0,
    )
    return model, history


def save_model(model, file_name: str) -> str:
    model_dir = Path(settings.predictor_model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    target = model_dir / file_name
    model.save(target)
    return str(target)


def load_saved_model(model_path: str):
    return load_model(model_path)


def evaluate_test_set(model, train_bundle: dict):
    y_pred_scaled = model.predict(train_bundle["x_test"], verbose=0)
    y_pred = train_bundle["target_scaler"].inverse_transform(y_pred_scaled).flatten()
    y_true = train_bundle["target_scaler"].inverse_transform(train_bundle["y_test"].reshape(-1, 1)).flatten()
    mae = float(mean_absolute_error(y_true, y_pred))
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(np.sqrt(mse))
    try:
        r2 = float(r2_score(y_true, y_pred))
    except Exception:
        r2 = 0.0

    direction_acc = 0.0
    if len(y_true) > 1 and len(y_pred) > 1:
        true_diff = np.diff(y_true)
        pred_diff = np.diff(y_pred)
        direction_acc = float(np.mean((true_diff >= 0) == (pred_diff >= 0)))

    return {
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "r2": r2,
        "directional_accuracy": direction_acc,
        "predictions": y_pred.tolist(),
        "actuals": y_true.tolist(),
    }
