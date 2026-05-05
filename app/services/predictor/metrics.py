from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def evaluate_regression(y_true, y_pred) -> dict:
    """Return lightweight regression metrics and chart-ready series."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    errors = y_pred - y_true
    mae = float(mean_absolute_error(y_true, y_pred))
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(np.sqrt(mse))
    try:
        r2 = float(r2_score(y_true, y_pred))
    except Exception:
        r2 = 0.0

    non_zero = np.abs(y_true) > 1e-8
    mape = float(np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100) if np.any(non_zero) else 0.0
    summary = {
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "mape": mape,
        "r2": r2,
    }
    return {
        **summary,
        "metrics_formatted": format_metrics(summary),
        "metrics_table": metrics_table(summary),
        "predictions": y_pred.tolist(),
        "actuals": y_true.tolist(),
        "errors": errors.tolist(),
        "absolute_errors": np.abs(errors).tolist(),
    }


def format_metrics(metrics: dict) -> dict:
    return {
        "mae": f"{metrics.get('mae', 0):.4f}",
        "mse": f"{metrics.get('mse', 0):.4f}",
        "rmse": f"{metrics.get('rmse', 0):.4f}",
        "mape": f"{metrics.get('mape', 0):.2f}%",
        "r2": f"{metrics.get('r2', 0):.4f}",
    }


def metrics_table(metrics: dict) -> list[dict]:
    formatted = format_metrics(metrics)
    return [
        {"metric": "R²", "name": "决定系数", "value": formatted["r2"]},
        {"metric": "MAE", "name": "平均绝对误差", "value": formatted["mae"]},
        {"metric": "MSE", "name": "均方误差", "value": formatted["mse"]},
        {"metric": "RMSE", "name": "均方根误差", "value": formatted["rmse"]},
        {"metric": "MAPE", "name": "平均绝对百分比误差", "value": formatted["mape"]},
    ]


def numeric_correlation_payload(data, columns: list[str] | None = None) -> dict:
    """Build an ECharts-friendly correlation matrix for numeric stock features."""
    numeric = data.select_dtypes(include=["number"]).copy()
    if columns:
        selected = [column for column in columns if column in numeric.columns]
        if selected:
            numeric = numeric[selected]
    if numeric.empty:
        return {"columns": [], "matrix": [], "values": []}
    corr = numeric.corr().fillna(0).round(4)
    corr_columns = list(corr.columns)
    values = [
        [col_index, row_index, float(corr.iloc[row_index, col_index])]
        for row_index in range(len(corr_columns))
        for col_index in range(len(corr_columns))
    ]
    return {
        "columns": corr_columns,
        "matrix": corr.values.tolist(),
        "values": values,
    }
