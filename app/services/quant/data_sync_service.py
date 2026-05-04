from datetime import datetime
from typing import Optional

import pandas as pd
import tushare as ts
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.stock_basic import StockBasic
from app.models.stock_daily import StockDaily


class QuantDataSyncService:
    def __init__(self) -> None:
        self.token = settings.tushare_token
        self.pro = ts.pro_api(self.token) if self.token else None

    def health(self) -> dict:
        return {
            "tushare_configured": bool(self.token),
            "timestamp": datetime.now().isoformat(),
        }

    def _require_client(self):
        if not self.pro:
            raise ValueError("TUSHARE_TOKEN not configured")
        return self.pro

    def sync_star_board_basic(self, db: Session) -> dict:
        pro = self._require_client()
        df = pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,area,industry,market,list_date",
        )

        if df is None or df.empty:
            return {"success": False, "message": "No stock_basic data returned from Tushare"}

        # Prefer market label when available, and keep a symbol prefix fallback.
        star_df = df[
            (df["market"].fillna("").str.contains("科创板"))
            | (df["symbol"].fillna("").str.startswith("688"))
        ].copy()

        if star_df.empty:
            return {"success": False, "message": "No STAR Market symbols found in Tushare response"}

        created = 0
        updated = 0

        for _, row in star_df.iterrows():
            item = db.get(StockBasic, row["ts_code"])
            list_date = None
            if pd.notna(row.get("list_date")) and str(row.get("list_date")).strip():
                list_date = datetime.strptime(str(row["list_date"]), "%Y%m%d").date()

            payload = {
                "symbol": str(row.get("symbol") or ""),
                "name": str(row.get("name") or ""),
                "area": str(row.get("area") or "") or None,
                "industry": str(row.get("industry") or "") or None,
                "market": str(row.get("market") or "") or None,
                "list_date": list_date,
                "is_star_board": True,
            }

            if item is None:
                db.add(StockBasic(ts_code=str(row["ts_code"]), **payload))
                created += 1
            else:
                for key, value in payload.items():
                    setattr(item, key, value)
                updated += 1

        db.commit()
        return {
            "success": True,
            "message": "STAR Market stock_basic sync completed",
            "count": int(len(star_df)),
            "created": created,
            "updated": updated,
        }

    def sync_star_board_daily(
        self,
        db: Session,
        start_date: str,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        pro = self._require_client()
        query = db.query(StockBasic).filter(StockBasic.is_star_board.is_(True)).order_by(StockBasic.ts_code.asc())
        stocks = query.limit(limit).all() if limit else query.all()

        if not stocks:
            return {"success": False, "message": "No STAR Market stocks found in local database"}

        end_date = end_date or datetime.now().strftime("%Y%m%d")
        inserted = 0
        updated = 0
        synced_symbols = 0

        for stock in stocks:
            daily_df = pro.daily(
                ts_code=stock.ts_code,
                start_date=start_date,
                end_date=end_date,
            )
            if daily_df is None or daily_df.empty:
                continue

            synced_symbols += 1

            for _, row in daily_df.iterrows():
                trade_date = datetime.strptime(str(row["trade_date"]), "%Y%m%d").date()
                existing = (
                    db.query(StockDaily)
                    .filter(StockDaily.ts_code == stock.ts_code, StockDaily.trade_date == trade_date)
                    .first()
                )
                payload = {
                    "open": float(row["open"]) if pd.notna(row["open"]) else None,
                    "high": float(row["high"]) if pd.notna(row["high"]) else None,
                    "low": float(row["low"]) if pd.notna(row["low"]) else None,
                    "close": float(row["close"]) if pd.notna(row["close"]) else None,
                    "vol": float(row["vol"]) if pd.notna(row["vol"]) else None,
                    "amount": float(row["amount"]) if pd.notna(row["amount"]) else None,
                }

                if existing is None:
                    db.add(
                        StockDaily(
                            ts_code=stock.ts_code,
                            trade_date=trade_date,
                            **payload,
                        )
                    )
                    inserted += 1
                else:
                    for key, value in payload.items():
                        setattr(existing, key, value)
                    updated += 1

        db.commit()
        return {
            "success": True,
            "message": "STAR Market daily sync completed",
            "symbols": len(stocks),
            "synced_symbols": synced_symbols,
            "inserted": inserted,
            "updated": updated,
            "start_date": start_date,
            "end_date": end_date,
        }
