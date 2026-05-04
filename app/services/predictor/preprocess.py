from typing import List

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def prepare_sequences(
    data: pd.DataFrame,
    selected_features: List[str],
    selected_target: str,
    look_back: int,
):
    if data is None or data.empty:
        raise ValueError("Input data is empty")
    if not selected_features:
        raise ValueError("selected_features cannot be empty")
    if selected_target not in data.columns:
        raise ValueError(f"Target column not found: {selected_target}")

    feature_scaler = StandardScaler()
    target_scaler = StandardScaler()
    feature_data = data[selected_features].astype(float).values
    target_data = data[selected_target].astype(float).values.reshape(-1, 1)
    feature_scaled = feature_scaler.fit_transform(feature_data)
    target_scaled = target_scaler.fit_transform(target_data)

    def create_dataset(feat_data, tgt_data, window):
        x_data = []
        y_data = []
        for i in range(len(feat_data) - window):
            x_data.append(feat_data[i : i + window])
            y_data.append(tgt_data[i + window, 0])
        return np.array(x_data), np.array(y_data)

    train_size = int(len(feature_scaled) * 0.8)
    x_train, y_train = create_dataset(feature_scaled[:train_size], target_scaled[:train_size], look_back)
    x_test, y_test = create_dataset(feature_scaled[train_size:], target_scaled[train_size:], look_back)
    if len(x_train) == 0 or len(x_test) == 0:
        raise ValueError("Not enough samples for current look_back")

    return {
        "x_train": x_train,
        "y_train": y_train,
        "x_test": x_test,
        "y_test": y_test,
        "feature_scaler": feature_scaler,
        "target_scaler": target_scaler,
        "train_size": train_size,
    }
