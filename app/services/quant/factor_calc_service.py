from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.models.factor_definition import FactorDefinition
from app.models.factor_value import FactorValue
from app.models.stock_basic import StockBasic
from app.models.stock_daily import StockDaily
from app.services.quant.factor_service import FactorService


class FactorCalculationService:
    builtin_handlers = {
        "return_1d": "_calc_return_1d",
        "momentum_5d": "_calc_momentum_5d",
        "momentum_20d": "_calc_momentum_20d",
        "volatility_20d": "_calc_volatility_20d",
        "turnover_amount_20d": "_calc_turnover_amount_20d",
        "volume_ratio_5d_20d": "_calc_volume_ratio_5d_20d",
        "price_position_20d": "_calc_price_position_20d",
    }
    safe_columns = ["open", "high", "low", "close", "vol", "amount"]

    def calculate_for_trade_date(
        self,
        db: Session,
        trade_date: str,
        factor_ids: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> dict:
        factor_defs_query = db.query(FactorDefinition).filter(FactorDefinition.is_active.is_(True))
        if factor_ids:
            factor_defs_query = factor_defs_query.filter(FactorDefinition.factor_id.in_(factor_ids))
        factor_defs = factor_defs_query.order_by(FactorDefinition.factor_id.asc()).all()

        if not factor_defs:
            return {"success": False, "message": "No active factors found"}

        stocks_query = db.query(StockBasic).filter(StockBasic.is_star_board.is_(True)).order_by(StockBasic.ts_code.asc())
        stocks = stocks_query.limit(limit).all() if limit else stocks_query.all()
        if not stocks:
            return {"success": False, "message": "No STAR Market stocks found in local database"}

        trade_date_obj = datetime.strptime(trade_date, "%Y%m%d").date()
        total_saved = 0
        factor_stats = {}

        for factor_def in factor_defs:
            rows = self._calculate_factor(db, stocks, factor_def, trade_date_obj)
            saved = self._upsert_factor_rows(db, rows)
            total_saved += saved
            factor_stats[factor_def.factor_id] = {"saved": saved}

        db.commit()
        return {
            "success": True,
            "trade_date": trade_date,
            "saved": total_saved,
            "factor_stats": factor_stats,
        }

    def calculate_for_date_range(
        self,
        db: Session,
        start_date: str,
        end_date: str,
        factor_ids: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> dict:
        start_date_obj = datetime.strptime(start_date, "%Y%m%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y%m%d").date()

        trade_dates = (
            db.query(StockDaily.trade_date)
            .filter(StockDaily.trade_date >= start_date_obj, StockDaily.trade_date <= end_date_obj)
            .distinct()
            .order_by(StockDaily.trade_date.asc())
            .all()
        )
        if not trade_dates:
            return {"success": False, "message": "No stock_daily trade dates found in the given range"}

        total_saved = 0
        processed_dates = 0
        details = []

        for (trade_date_obj,) in trade_dates:
            result = self.calculate_for_trade_date(
                db,
                trade_date=trade_date_obj.strftime("%Y%m%d"),
                factor_ids=factor_ids,
                limit=limit,
            )
            if result.get("success"):
                processed_dates += 1
                total_saved += int(result.get("saved", 0))
                details.append(
                    {
                        "trade_date": trade_date_obj.isoformat(),
                        "saved": int(result.get("saved", 0)),
                    }
                )

        return {
            "success": True,
            "start_date": start_date,
            "end_date": end_date,
            "processed_dates": processed_dates,
            "saved": total_saved,
            "details": details[-10:],
        }

    def _calculate_factor(self, db: Session, stocks: Iterable[StockBasic], factor_def: FactorDefinition, trade_date_obj):
        handler_name = self.builtin_handlers.get(factor_def.factor_id)
        handler = getattr(self, handler_name) if handler_name else None
        raw_rows = []

        for stock in stocks:
            daily_rows = (
                db.query(StockDaily)
                .filter(StockDaily.ts_code == stock.ts_code, StockDaily.trade_date <= trade_date_obj)
                .order_by(StockDaily.trade_date.asc())
                .all()
            )
            if not daily_rows:
                continue

            df = pd.DataFrame(
                [
                    {
                        "trade_date": row.trade_date,
                        "open": row.open,
                        "high": row.high,
                        "low": row.low,
                        "close": row.close,
                        "vol": row.vol,
                        "amount": row.amount,
                    }
                    for row in daily_rows
                ]
            )
            value = handler(df, trade_date_obj) if handler else self._calc_formula(df, trade_date_obj, factor_def.formula)
            if value is None:
                continue
            raw_rows.append(
                {
                    "ts_code": stock.ts_code,
                    "trade_date": trade_date_obj,
                    "factor_id": factor_def.factor_id,
                    "factor_value": float(value),
                }
            )

        if not raw_rows:
            return []

        raw_df = pd.DataFrame(raw_rows)
        std = raw_df["factor_value"].std()
        mean = raw_df["factor_value"].mean()
        if std and std > 0:
            raw_df["z_score"] = (raw_df["factor_value"] - mean) / std
        else:
            raw_df["z_score"] = 0.0
        return raw_df.to_dict(orient="records")

    def _upsert_factor_rows(self, db: Session, rows: list[dict]) -> int:
        saved = 0
        for row in rows:
            existing = (
                db.query(FactorValue)
                .filter(
                    FactorValue.ts_code == row["ts_code"],
                    FactorValue.trade_date == row["trade_date"],
                    FactorValue.factor_id == row["factor_id"],
                )
                .first()
            )
            if existing is None:
                db.add(FactorValue(**row))
            else:
                existing.factor_value = row["factor_value"]
                existing.z_score = row["z_score"]
            saved += 1
        return saved

    def _calc_formula(self, df: pd.DataFrame, trade_date_obj, formula: str):
        row = df[df["trade_date"] == trade_date_obj]
        if row.empty:
            return None

        valid, _ = FactorService().validate_formula(formula)
        if not valid:
            return None

        safe_locals = {column: pd.to_numeric(df[column], errors="coerce") for column in self.safe_columns}
        try:
            result = eval(compile(formula, "<custom_factor_formula>", "eval"), {"__builtins__": {}}, safe_locals)
        except Exception:
            return None

        if isinstance(result, pd.Series):
            result = result.replace([np.inf, -np.inf], np.nan)
            value = result.iloc[-1]
        else:
            value = result
        if pd.isna(value) or not np.isfinite(float(value)):
            return None
        return float(value)

    def _calc_return_1d(self, df: pd.DataFrame, trade_date_obj):
        row = df[df["trade_date"] == trade_date_obj]
        if row.empty:
            return None
        series = df["close"].pct_change(1)
        value = series.iloc[-1]
        return None if pd.isna(value) else value

    def _calc_momentum_5d(self, df: pd.DataFrame, trade_date_obj):
        row = df[df["trade_date"] == trade_date_obj]
        if row.empty:
            return None
        series = df["close"].pct_change(5)
        value = series.iloc[-1]
        return None if pd.isna(value) else value

    def _calc_momentum_20d(self, df: pd.DataFrame, trade_date_obj):
        row = df[df["trade_date"] == trade_date_obj]
        if row.empty:
            return None
        series = df["close"].pct_change(20)
        value = series.iloc[-1]
        return None if pd.isna(value) else value

    def _calc_volatility_20d(self, df: pd.DataFrame, trade_date_obj):
        row = df[df["trade_date"] == trade_date_obj]
        if row.empty:
            return None
        series = df["close"].pct_change().rolling(20).std()
        value = series.iloc[-1]
        return None if pd.isna(value) else value

    def _calc_turnover_amount_20d(self, df: pd.DataFrame, trade_date_obj):
        row = df[df["trade_date"] == trade_date_obj]
        if row.empty:
            return None
        series = df["amount"].rolling(20).mean()
        value = series.iloc[-1]
        return None if pd.isna(value) else value

    def _calc_volume_ratio_5d_20d(self, df: pd.DataFrame, trade_date_obj):
        row = df[df["trade_date"] == trade_date_obj]
        if row.empty:
            return None
        denominator = df["vol"].rolling(20).mean()
        series = df["vol"].rolling(5).mean() / denominator
        value = series.iloc[-1]
        return None if pd.isna(value) or value in (float("inf"), float("-inf")) else value

    def _calc_price_position_20d(self, df: pd.DataFrame, trade_date_obj):
        row = df[df["trade_date"] == trade_date_obj]
        if row.empty:
            return None
        rolling_low = df["low"].rolling(20).min()
        rolling_high = df["high"].rolling(20).max()
        series = (df["close"] - rolling_low) / (rolling_high - rolling_low)
        value = series.iloc[-1]
        return None if pd.isna(value) or value in (float("inf"), float("-inf")) else value
