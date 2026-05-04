from datetime import datetime

import akshare as ak
import pandas as pd


def fetch_stock_data(stock_code: str, start_year: int) -> pd.DataFrame:
    if not (stock_code.isdigit() and len(stock_code) == 6):
        raise ValueError("stock_code must be a 6-digit string")

    market_prefix = "sh" if stock_code.startswith(("5", "6", "9")) else "sz"
    symbol = f"{market_prefix}{stock_code}"
    start_date = datetime(start_year, 1, 1).strftime("%Y%m%d")
    end_date = datetime.now().strftime("%Y%m%d")

    stock_df = ak.stock_zh_a_daily(symbol=symbol, start_date=start_date, end_date=end_date, adjust="qfq")
    if stock_df is None or stock_df.empty:
        raise ValueError("No stock data returned from AKShare")

    stock_df = stock_df.rename(
        columns={
            "date": "date",
            "open": "open",
            "close": "close",
            "high": "high",
            "low": "low",
            "volume": "volume",
            "amount": "amount",
        }
    )
    stock_df["date"] = pd.to_datetime(stock_df["date"])
    stock_df = stock_df.sort_values("date").reset_index(drop=True)
    stock_df.insert(0, "stock_code", stock_code)

    try:
        stock_info = ak.stock_info_a_code_name()
        stock_name = stock_info.loc[stock_info["code"] == stock_code, "name"].iloc[0]
    except Exception:
        stock_name = f"stock_{stock_code}"
    stock_df.insert(1, "stock_name", stock_name)
    return stock_df
