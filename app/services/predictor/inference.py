from datetime import timedelta
from typing import List

import numpy as np
import pandas as pd


def predict_one(model, train_bundle: dict):
    last_sequence = train_bundle["x_test"][-1].reshape(1, train_bundle["x_test"][-1].shape[0], train_bundle["x_test"][-1].shape[1])
    pred_scaled = model.predict(last_sequence, verbose=0)
    pred_value = train_bundle["target_scaler"].inverse_transform(pred_scaled)[0, 0]
    true_value = train_bundle["target_scaler"].inverse_transform(train_bundle["y_test"][-1].reshape(-1, 1))[0, 0]
    return {
        "predicted_value": float(pred_value),
        "true_value": float(true_value),
        "absolute_error": float(abs(pred_value - true_value)),
    }


def predict_future_days(model, data: pd.DataFrame, train_bundle: dict, selected_features: List[str], look_back: int, days_to_predict: int):
    last_feature_data = data[selected_features].astype(float).values[-look_back:]
    last_feature_scaled = train_bundle["feature_scaler"].transform(last_feature_data)
    last_sequence = last_feature_scaled.reshape(1, look_back, len(selected_features))

    future_scaled = []
    for _ in range(days_to_predict):
        next_pred_scaled = model.predict(last_sequence, verbose=0)
        future_scaled.append(next_pred_scaled[0, 0])
        next_frame = np.roll(last_sequence, -1, axis=1)
        next_frame[0, -1, :] = next_pred_scaled[0, 0]
        last_sequence = next_frame

    future_prices = train_bundle["target_scaler"].inverse_transform(np.array(future_scaled).reshape(-1, 1)).flatten()

    future_dates = []
    current_date = pd.to_datetime(data["date"].iloc[-1]).to_pydatetime()
    while len(future_dates) < days_to_predict:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:
            future_dates.append(current_date.strftime("%Y-%m-%d"))

    return [
        {"date": date_value, "predicted_price": float(price)}
        for date_value, price in zip(future_dates, future_prices)
    ]
