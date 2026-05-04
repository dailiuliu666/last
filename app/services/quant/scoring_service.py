from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models.factor_definition import FactorDefinition
from app.models.factor_value import FactorValue
from app.models.stock_basic import StockBasic


class QuantScoringService:
    def calculate_scores(
        self,
        db: Session,
        trade_date: str,
        factor_ids: Optional[List[str]] = None,
        top_n: int = 20,
    ) -> dict:
        trade_date_obj = self._to_date(trade_date)
        factor_defs_query = db.query(FactorDefinition).filter(FactorDefinition.is_active.is_(True))
        if factor_ids:
            factor_defs_query = factor_defs_query.filter(FactorDefinition.factor_id.in_(factor_ids))
        factor_defs = factor_defs_query.all()
        factor_meta = {
            item.factor_id: {
                "direction": self._factor_direction(item),
                "weight": self._factor_weight(item),
                "factor_name": item.factor_name,
                "factor_type": item.factor_type,
            }
            for item in factor_defs
        }
        selected_factor_ids = sorted(factor_meta.keys())
        if not selected_factor_ids:
            return {"success": False, "message": "No active factor definitions found for scoring"}

        query = db.query(FactorValue).filter(FactorValue.trade_date == trade_date_obj)
        query = query.filter(FactorValue.factor_id.in_(selected_factor_ids))

        rows = query.all()
        if not rows:
            return {
                "success": False,
                "message": f"No factor values found for trade_date={trade_date}",
            }

        df = pd.DataFrame(
            [
                {
                    "ts_code": row.ts_code,
                    "factor_id": row.factor_id,
                    "factor_value": row.factor_value,
                    "z_score": row.z_score,
                }
                for row in rows
            ]
        )

        pivot = (
            df.pivot_table(
                index="ts_code",
                columns="factor_id",
                values="z_score",
                aggfunc="first",
            )
            .fillna(0.0)
            .reset_index()
        )

        factor_columns = [column for column in pivot.columns if column != "ts_code"]
        if not factor_columns:
            return {"success": False, "message": "No factor columns available for scoring"}

        weighted_columns = []
        total_weight = 0.0
        for column in factor_columns:
            meta = factor_meta.get(column, {})
            direction = meta.get("direction", 1)
            weight = meta.get("weight", 1.0)
            adjusted_column = f"__adjusted_{column}"
            pivot[adjusted_column] = pivot[column] * direction * weight
            weighted_columns.append(adjusted_column)
            total_weight += weight
        if total_weight <= 0:
            return {"success": False, "message": "Total factor weight must be greater than 0"}

        pivot["composite_score"] = pivot[weighted_columns].sum(axis=1) / total_weight
        pivot["rank"] = pivot["composite_score"].rank(ascending=False, method="dense").astype(int)
        pivot = pivot.sort_values(["rank", "ts_code"]).reset_index(drop=True)

        stock_map = self._get_stock_map(db, pivot["ts_code"].tolist())
        results = []
        for _, row in pivot.head(top_n).iterrows():
            stock = stock_map.get(row["ts_code"], {})
            results.append(
                {
                    "ts_code": row["ts_code"],
                    "name": stock.get("name"),
                    "industry": stock.get("industry"),
                    "composite_score": float(row["composite_score"]),
                    "rank": int(row["rank"]),
                    "factor_scores": {
                        column: float(row[column])
                        for column in factor_columns
                    },
                    "adjusted_factor_scores": {
                        column: float(row[f"__adjusted_{column}"])
                        for column in factor_columns
                    },
                }
            )

        return {
            "success": True,
            "trade_date": trade_date_obj.isoformat(),
            "factor_ids": factor_columns,
            "factor_meta": factor_meta,
            "count": len(results),
            "results": results,
        }

    def get_stock_factor_snapshot(self, db: Session, ts_code: str, trade_date: str) -> dict:
        trade_date_obj = self._to_date(trade_date)
        rows = (
            db.query(FactorValue)
            .filter(FactorValue.ts_code == ts_code, FactorValue.trade_date == trade_date_obj)
            .order_by(FactorValue.factor_id.asc())
            .all()
        )
        stock = db.get(StockBasic, ts_code)
        if not rows:
            return {
                "success": False,
                "message": f"No factor snapshot found for ts_code={ts_code}, trade_date={trade_date}",
            }

        return {
            "success": True,
            "stock": {
                "ts_code": ts_code,
                "name": stock.name if stock else None,
                "industry": stock.industry if stock else None,
            },
            "trade_date": trade_date_obj.isoformat(),
            "factors": [
                {
                    "factor_id": row.factor_id,
                    "factor_value": row.factor_value,
                    "z_score": row.z_score,
                }
                for row in rows
            ],
        }

    def get_quant_overview(self, db: Session) -> dict:
        stock_basic_count = db.query(StockBasic).count()
        factor_value_count = db.query(FactorValue).count()
        latest_factor = db.query(FactorValue).order_by(FactorValue.trade_date.desc()).first()

        return {
            "success": True,
            "overview": {
                "stock_basic_count": stock_basic_count,
                "factor_value_count": factor_value_count,
                "latest_factor_trade_date": latest_factor.trade_date.isoformat() if latest_factor else None,
            },
        }

    def _get_stock_map(self, db: Session, ts_codes: Iterable[str]) -> dict:
        rows = db.query(StockBasic).filter(StockBasic.ts_code.in_(list(ts_codes))).all()
        return {
            row.ts_code: {
                "name": row.name,
                "industry": row.industry,
            }
            for row in rows
        }

    def _to_date(self, value: str):
        return datetime.strptime(value, "%Y-%m-%d").date() if "-" in value else datetime.strptime(value, "%Y%m%d").date()

    def _factor_direction(self, factor_def: FactorDefinition) -> int:
        params = factor_def.params or {}
        direction = params.get("direction", 1)
        return -1 if direction == -1 else 1

    def _factor_weight(self, factor_def: FactorDefinition) -> float:
        params = factor_def.params or {}
        try:
            weight = float(params.get("weight", 1.0))
        except (TypeError, ValueError):
            return 1.0
        return max(weight, 0.0)
