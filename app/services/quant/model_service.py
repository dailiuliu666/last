from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy.orm import Session

try:
    import xgboost as xgb
except Exception:  # pragma: no cover
    xgb = None

try:
    import lightgbm as lgb
except Exception:  # pragma: no cover
    lgb = None

from app.models.factor_value import FactorValue
from app.models.ml_model_definition import MLModelDefinition
from app.models.ml_prediction import MLPrediction
from app.models.stock_basic import StockBasic
from app.models.stock_daily import StockDaily
from app.models.train_run import TrainRun


class QuantModelService:
    supported_model_types = {"random_forest", "xgboost", "lightgbm"}
    supported_target_types = {"return_5d", "return_20d"}

    def capabilities(self) -> dict:
        return {
            "model_types": sorted(self.supported_model_types),
            "target_types": sorted(self.supported_target_types),
        }

    def create_model_definition(
        self,
        db: Session,
        model_id: str,
        model_name: str,
        model_type: str,
        target_type: str,
        factor_list: list[str],
    ) -> dict:
        if model_type not in self.supported_model_types:
            return {"success": False, "message": f"Unsupported model_type: {model_type}"}
        if target_type not in self.supported_target_types:
            return {"success": False, "message": f"Unsupported target_type: {target_type}"}
        if not factor_list:
            return {"success": False, "message": "factor_list cannot be empty"}

        existing = db.get(MLModelDefinition, model_id)
        if existing:
            existing.model_name = model_name
            existing.model_type = model_type
            existing.target_type = target_type
            existing.factor_list = factor_list
        else:
            db.add(
                MLModelDefinition(
                    model_id=model_id,
                    model_name=model_name,
                    model_type=model_type,
                    target_type=target_type,
                    factor_list=factor_list,
                    model_params={},
                    training_config={},
                )
            )
        db.commit()
        return {"success": True, "message": "Model definition saved", "model_id": model_id}

    def train_model(
        self,
        db: Session,
        model_id: str,
        start_date: str,
        end_date: str,
    ) -> dict:
        model_def = db.get(MLModelDefinition, model_id)
        if not model_def:
            return {"success": False, "message": f"Model not found: {model_id}"}

        train_run = TrainRun(
            module="quant",
            run_name=f"train_{model_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status="running",
            params={
                "model_id": model_id,
                "model_type": model_def.model_type,
                "target_type": model_def.target_type,
                "factor_list": model_def.factor_list,
                "start_date": start_date,
                "end_date": end_date,
            },
            metrics={},
            message="Training started",
        )
        db.add(train_run)
        db.commit()
        db.refresh(train_run)

        dataset = self._build_training_dataset(db, model_def.factor_list, model_def.target_type, start_date, end_date)
        if dataset.empty:
            train_run.status = "failed"
            train_run.message = "Training dataset is empty. Calculate factor history for a date range before training."
            db.commit()
            return {
                "success": False,
                "message": train_run.message,
                "train_run_id": train_run.id,
            }

        try:
            feature_columns = model_def.factor_list
            x = dataset[feature_columns].astype(float)
            y = dataset["target"].astype(float)

            model = self._build_estimator(model_def.model_type)
            model.fit(x, y)

            predictions = model.predict(x)
            mae = float(np.mean(np.abs(predictions - y)))
            r2 = float(self._safe_r2(y.to_numpy(), predictions))

            artifact_dir = Path("model_artifacts")
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = artifact_dir / f"{model_id}.joblib"
            joblib.dump(model, artifact_path)

            metrics = {"mae": mae, "r2": r2, "row_count": int(len(dataset))}
            model_def.artifact_path = str(artifact_path)
            model_def.model_params = {"feature_columns": feature_columns}
            model_def.training_config = {
                "start_date": start_date,
                "end_date": end_date,
                "row_count": int(len(dataset)),
                "trained_at": datetime.now().isoformat(),
                "train_run_id": train_run.id,
            }
            train_run.status = "success"
            train_run.metrics = metrics
            train_run.message = "Model training completed"
            db.commit()
        except Exception as exc:
            train_run.status = "failed"
            train_run.message = str(exc)
            db.commit()
            raise

        return {
            "success": True,
            "message": "Model training completed",
            "model_id": model_id,
            "train_run_id": train_run.id,
            "artifact_path": str(artifact_path),
            "metrics": metrics,
        }

    def predict_scores(self, db: Session, model_id: str, trade_date: str) -> dict:
        model_def = db.get(MLModelDefinition, model_id)
        if not model_def:
            return {"success": False, "message": f"Model not found: {model_id}"}
        if not model_def.artifact_path:
            return {"success": False, "message": "Model has not been trained yet"}

        model = joblib.load(model_def.artifact_path)
        trade_date_obj = self._to_date(trade_date)
        query = db.query(FactorValue).filter(FactorValue.trade_date == trade_date_obj)
        query = query.filter(FactorValue.factor_id.in_(model_def.factor_list))
        rows = query.all()
        if not rows:
            return {"success": False, "message": f"No factor values found for trade_date={trade_date}"}

        df = pd.DataFrame(
            [
                {
                    "ts_code": row.ts_code,
                    "factor_id": row.factor_id,
                    "z_score": row.z_score,
                }
                for row in rows
            ]
        )
        pivot = (
            df.pivot_table(index="ts_code", columns="factor_id", values="z_score", aggfunc="first")
            .fillna(0.0)
            .reset_index()
        )
        missing_columns = [column for column in model_def.factor_list if column not in pivot.columns]
        for column in missing_columns:
            pivot[column] = 0.0
        feature_df = pivot[model_def.factor_list].astype(float)
        predicted = model.predict(feature_df)
        pivot["predicted_value"] = predicted
        pivot["rank"] = pivot["predicted_value"].rank(ascending=False, method="dense").astype(int)
        pivot = pivot.sort_values(["rank", "ts_code"]).reset_index(drop=True)

        saved = 0
        for _, row in pivot.iterrows():
            existing = (
                db.query(MLPrediction)
                .filter(
                    MLPrediction.model_id == model_id,
                    MLPrediction.ts_code == row["ts_code"],
                    MLPrediction.trade_date == trade_date_obj,
                )
                .first()
            )
            payload = {
                "predicted_value": float(row["predicted_value"]),
                "score": float(row["predicted_value"]),
            }
            if existing is None:
                db.add(
                    MLPrediction(
                        model_id=model_id,
                        ts_code=row["ts_code"],
                        trade_date=trade_date_obj,
                        **payload,
                    )
                )
            else:
                existing.predicted_value = payload["predicted_value"]
                existing.score = payload["score"]
            saved += 1
        db.commit()

        top_rows = pivot.head(20)
        return {
            "success": True,
            "model_id": model_id,
            "trade_date": trade_date_obj.isoformat(),
            "saved": saved,
            "results": [
                {
                    "ts_code": row["ts_code"],
                    "predicted_value": float(row["predicted_value"]),
                    "rank": int(row["rank"]),
                }
                for _, row in top_rows.iterrows()
            ],
        }

    def get_stock_prediction_snapshot(self, db: Session, model_id: str, ts_code: str, trade_date: str) -> dict:
        trade_date_obj = self._to_date(trade_date)
        row = (
            db.query(MLPrediction)
            .filter(
                MLPrediction.model_id == model_id,
                MLPrediction.ts_code == ts_code,
                MLPrediction.trade_date == trade_date_obj,
            )
            .first()
        )
        if row is None:
            return {
                "success": False,
                "message": f"No ML prediction found for model_id={model_id}, ts_code={ts_code}, trade_date={trade_date}",
            }

        stock = db.get(StockBasic, ts_code)
        return {
            "success": True,
            "trade_date": trade_date_obj.isoformat(),
            "model_id": model_id,
            "stock": {
                "ts_code": ts_code,
                "name": stock.name if stock else None,
                "industry": stock.industry if stock else None,
            },
            "prediction": {
                "predicted_value": row.predicted_value,
                "score": row.score,
            },
        }

    def list_model_definitions(self, db: Session) -> list[dict]:
        rows = db.query(MLModelDefinition).order_by(MLModelDefinition.model_id.asc()).all()
        return [
            {
                "model_id": row.model_id,
                "model_name": row.model_name,
                "model_type": row.model_type,
                "target_type": row.target_type,
                "factor_list": row.factor_list,
                "artifact_path": row.artifact_path,
                "training_config": row.training_config,
            }
            for row in rows
        ]

    def _build_estimator(self, model_type: str):
        if model_type == "random_forest":
            return RandomForestRegressor(n_estimators=120, max_depth=8, random_state=42, n_jobs=-1)
        if model_type == "xgboost":
            if xgb is None:
                raise ValueError("xgboost is not available in the current environment")
            return xgb.XGBRegressor(n_estimators=120, max_depth=6, learning_rate=0.08, random_state=42, n_jobs=4)
        if model_type == "lightgbm":
            if lgb is None:
                raise ValueError("lightgbm is not available in the current environment")
            return lgb.LGBMRegressor(n_estimators=120, max_depth=6, learning_rate=0.08, random_state=42, verbose=-1)
        raise ValueError(f"Unsupported model_type: {model_type}")

    def _build_training_dataset(
        self,
        db: Session,
        factor_list: list[str],
        target_type: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        factor_rows = (
            db.query(FactorValue)
            .filter(FactorValue.factor_id.in_(factor_list))
            .filter(FactorValue.trade_date >= self._to_date(start_date))
            .filter(FactorValue.trade_date <= self._to_date(end_date))
            .all()
        )
        if not factor_rows:
            return pd.DataFrame()

        factor_df = pd.DataFrame(
            [
                {
                    "ts_code": row.ts_code,
                    "trade_date": row.trade_date,
                    "factor_id": row.factor_id,
                    "z_score": row.z_score,
                }
                for row in factor_rows
            ]
        )
        feature_df = (
            factor_df.pivot_table(index=["ts_code", "trade_date"], columns="factor_id", values="z_score", aggfunc="first")
            .fillna(0.0)
            .reset_index()
        )

        price_rows = (
            db.query(StockDaily)
            .filter(StockDaily.trade_date >= self._to_date(start_date))
            .filter(StockDaily.trade_date <= self._to_date(end_date))
            .all()
        )
        if not price_rows:
            return pd.DataFrame()

        price_df = pd.DataFrame(
            [
                {
                    "ts_code": row.ts_code,
                    "trade_date": row.trade_date,
                    "close": row.close,
                }
                for row in price_rows
            ]
        ).sort_values(["ts_code", "trade_date"])

        period = 5 if target_type == "return_5d" else 20
        price_df["future_close"] = price_df.groupby("ts_code")["close"].shift(-period)
        price_df["target"] = (price_df["future_close"] - price_df["close"]) / price_df["close"]
        target_df = price_df[["ts_code", "trade_date", "target"]].dropna()

        merged = feature_df.merge(target_df, on=["ts_code", "trade_date"], how="inner").dropna()
        return merged

    def _to_date(self, value: str):
        return datetime.strptime(value, "%Y-%m-%d").date() if "-" in value else datetime.strptime(value, "%Y%m%d").date()

    def _safe_r2(self, y_true, y_pred) -> float:
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        if ss_tot == 0:
            return 0.0
        return 1 - ss_res / ss_tot
