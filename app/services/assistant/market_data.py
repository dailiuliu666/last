from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import requests


def normalize_stock_code(stock_code: str) -> str:
    cleaned = str(stock_code).strip().upper()
    if cleaned.endswith((".SH", ".SZ")):
        cleaned = cleaned[:-3]
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    if len(digits) != 6:
        raise ValueError("A 股代码必须是 6 位数字，例如 600519 或 000001。")
    return digits


def format_number(value: Any):
    if value is None:
        return "N/A"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return value
    abs_val = abs(numeric)
    sign = "-" if numeric < 0 else ""
    if abs_val >= 1e12:
        return f"{sign}{abs_val / 1e12:.2f}万亿"
    if abs_val >= 1e8:
        return f"{sign}{abs_val / 1e8:.2f}亿"
    if abs_val >= 1e4:
        return f"{sign}{abs_val / 1e4:.2f}万"
    return f"{sign}{abs_val:.2f}"


def format_pct(value):
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return value


def em_scaled(value: Any, scale: float = 100):
    if value in (None, "-", ""):
        return "N/A"
    try:
        return round(float(value) / scale, 2)
    except (TypeError, ValueError):
        return value


def eastmoney_secid(stock_code: str) -> str:
    market = "1" if stock_code.startswith(("5", "6", "9")) else "0"
    return f"{market}.{stock_code}"


def eastmoney_request(url: str, params: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(
        url,
        params=params,
        timeout=(3, 8),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data")
    if not data:
        raise ValueError("东方财富接口没有返回数据。")
    return data


def get_realtime_quote(stock_code: str) -> dict[str, Any]:
    code = normalize_stock_code(stock_code)
    fields = ",".join(
        [
            "f43",
            "f44",
            "f45",
            "f46",
            "f47",
            "f48",
            "f50",
            "f57",
            "f58",
            "f60",
            "f116",
            "f117",
            "f162",
            "f167",
            "f168",
            "f169",
            "f170",
        ]
    )
    data = eastmoney_request(
        "https://push2.eastmoney.com/api/qt/stock/get",
        {"secid": eastmoney_secid(code), "fields": fields},
    )
    return {
        "股票名称": data.get("f58", code),
        "股票代码": data.get("f57", code),
        "最新价": em_scaled(data.get("f43")),
        "涨跌幅": format_pct(em_scaled(data.get("f170"))),
        "涨跌额": em_scaled(data.get("f169")),
        "成交量": format_number(data.get("f47")),
        "成交额": format_number(data.get("f48")),
        "振幅": format_pct(em_scaled(data.get("f50"))),
        "最高": em_scaled(data.get("f44")),
        "最低": em_scaled(data.get("f45")),
        "今开": em_scaled(data.get("f46")),
        "昨收": em_scaled(data.get("f60")),
        "换手率": format_pct(em_scaled(data.get("f168"))),
        "市盈率动态": em_scaled(data.get("f162")),
        "市净率": em_scaled(data.get("f167")),
        "总市值": format_number(data.get("f116")),
        "流通市值": format_number(data.get("f117")),
        "数据源": "东方财富行情接口",
    }


def history_range_from_period(period: str) -> tuple[str, str]:
    today = datetime.now().date()
    period = (period or "1mo").lower()
    mapping = {
        "5d": 7,
        "1mo": 31,
        "3mo": 93,
        "6mo": 186,
        "1y": 366,
        "2y": 732,
        "5y": 1827,
        "ytd": (today - datetime(today.year, 1, 1).date()).days + 1,
        "max": 3650,
    }
    days = mapping.get(period, 31)
    start = today - timedelta(days=days)
    return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")


def get_history_summary(stock_code: str, period: str = "1mo") -> dict[str, Any]:
    code = normalize_stock_code(stock_code)
    start_date, end_date = history_range_from_period(period)
    data = eastmoney_request(
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        {
            "secid": eastmoney_secid(code),
            "klt": "101",
            "fqt": "1",
            "beg": start_date,
            "end": end_date,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        },
    )
    records = []
    for item in data.get("klines") or []:
        date, open_, close, high, low, volume, amount, amplitude, pct, change, turnover = item.split(",")
        records.append(
            {
                "日期": pd.to_datetime(date),
                "开盘": float(open_),
                "收盘": float(close),
                "最高": float(high),
                "最低": float(low),
                "成交量": float(volume),
                "成交额": float(amount),
                "涨跌幅": float(pct),
            }
        )
    if not records:
        raise ValueError(f"未找到 {code} 的历史数据。")
    hist = pd.DataFrame(records)
    summary = {
        "股票代码": code,
        "股票名称": data.get("name") or code,
        "查询周期": period,
        "数据起始": str(hist["日期"].iloc[0]),
        "数据截止": str(hist["日期"].iloc[-1]),
        "起始价格": round(float(hist["收盘"].iloc[0]), 2),
        "最新价格": round(float(hist["收盘"].iloc[-1]), 2),
        "期间涨跌": f"{((hist['收盘'].iloc[-1] / hist['收盘'].iloc[0]) - 1) * 100:.2f}%",
        "期间最高": round(float(hist["最高"].max()), 2),
        "期间最低": round(float(hist["最低"].min()), 2),
        "平均成交量": int(hist["成交量"].mean()),
    }
    recent = []
    for _, row in hist.tail(8).iterrows():
        recent.append(
            {
                "日期": str(row["日期"]),
                "开盘": round(float(row["开盘"]), 2),
                "收盘": round(float(row["收盘"]), 2),
                "最高": round(float(row["最高"]), 2),
                "最低": round(float(row["最低"]), 2),
                "成交量": int(row["成交量"]),
                "涨跌幅": format_pct(row["涨跌幅"]),
            }
        )
    return {"汇总": summary, "近期交易数据": recent}
