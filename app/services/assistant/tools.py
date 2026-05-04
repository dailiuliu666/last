from __future__ import annotations

import concurrent.futures
import json
import os
from datetime import datetime, timedelta
from typing import Any

import akshare as ak
import pandas as pd
from langchain_core.tools import tool

from app.services.assistant.market_data import get_history_summary, get_realtime_quote, normalize_stock_code


TOOL_TIMEOUT_SECONDS = int(os.getenv("AI_TOOL_TIMEOUT_SECONDS", "15"))


def _format_number(value: Any):
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


def _round(value, n: int = 2):
    if value is None:
        return "N/A"
    try:
        return round(float(value), n)
    except (TypeError, ValueError):
        return value


def _load_name_map() -> pd.DataFrame:
    return ak.stock_info_a_code_name()


def _lookup_stock_name(stock_code: str) -> str:
    try:
        stock_info = _load_name_map()
        match = stock_info.loc[stock_info["code"] == stock_code, "name"]
        if not match.empty:
            return str(match.iloc[0])
    except Exception:
        pass
    return stock_code


def _with_timeout(label: str, func, timeout: int = TOOL_TIMEOUT_SECONDS):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        future.cancel()
        return f"{label} 数据源响应超过 {timeout} 秒，已跳过该项。建议稍后重试或单独查询。"
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _history_df(stock_code: str, period: str = "1mo") -> pd.DataFrame:
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
    start = today - timedelta(days=mapping.get(period, 31))
    market_prefix = "sh" if stock_code.startswith(("5", "6", "9")) else "sz"
    df = ak.stock_zh_a_daily(
        symbol=f"{market_prefix}{stock_code}",
        start_date=start.strftime("%Y%m%d"),
        end_date=today.strftime("%Y%m%d"),
        adjust="qfq",
    )
    if df is None or df.empty:
        raise ValueError(f"未找到 {stock_code} 的历史数据。")
    df = df.rename(
        columns={
            "date": "日期",
            "open": "开盘",
            "close": "收盘",
            "high": "最高",
            "low": "最低",
            "volume": "成交量",
            "amount": "成交额",
        }
    ).copy()
    df["日期"] = pd.to_datetime(df["日期"])
    df["涨跌幅"] = df["收盘"].pct_change().fillna(0) * 100
    return df


@tool
def get_stock_info(stock_code: str) -> str:
    """获取 A 股基本信息，包括最新价格、涨跌幅、成交额、市盈率与总市值。"""
    try:
        quote = get_realtime_quote(normalize_stock_code(stock_code))
        return json.dumps(quote, ensure_ascii=False, indent=2)
    except Exception as exc:
        return f"获取 A 股 {stock_code} 快速行情时出错: {exc}"


@tool
def get_stock_history(stock_code: str, period: str = "1mo") -> str:
    """获取 A 股历史行情数据。period 可选 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max。"""
    try:
        code = normalize_stock_code(stock_code)
        try:
            result = get_history_summary(code, period)
        except Exception:
            hist = _history_df(code, period)
            result = {
                "汇总": {
                    "股票代码": code,
                    "股票名称": _lookup_stock_name(code),
                    "查询周期": period,
                    "数据起始": str(hist["日期"].iloc[0]),
                    "数据截止": str(hist["日期"].iloc[-1]),
                    "起始价格": _round(hist["收盘"].iloc[0]),
                    "最新价格": _round(hist["收盘"].iloc[-1]),
                    "期间涨跌": f"{((hist['收盘'].iloc[-1] / hist['收盘'].iloc[0]) - 1) * 100:.2f}%",
                    "期间最高": _round(hist["最高"].max()),
                    "期间最低": _round(hist["最低"].min()),
                    "平均成交量": int(hist["成交量"].mean()),
                },
                "近期交易数据": hist.tail(8).to_dict(orient="records"),
            }
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
    except Exception as exc:
        return f"获取 A 股 {stock_code} 历史数据时出错: {exc}"


@tool
def get_financial_statement(stock_code: str, statement_type: str = "indicator") -> str:
    """获取 A 股核心财务指标。statement_type 当前支持 indicator/income/balance/cashflow。"""

    def load():
        code = normalize_stock_code(stock_code)
        df = ak.stock_financial_abstract(symbol=code)
        if df is None or df.empty:
            return f"未找到 {code} 的财务指标数据"
        period_columns = [column for column in df.columns if str(column).isdigit()]
        latest_periods = period_columns[:6]
        records = []
        for _, row in df.head(18).fillna("").iterrows():
            item = {"分类": row.get("选项", ""), "指标": row.get("指标", "")}
            for period in latest_periods:
                item[period] = row.get(period, "")
            records.append(item)
        return json.dumps(
            {
                "股票代码": code,
                "股票名称": _lookup_stock_name(code),
                "请求类型": statement_type,
                "说明": "使用新浪财经关键指标接口，返回近几期核心财务指标。",
                "最近报告期": latest_periods,
                "数据": records,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    try:
        return _with_timeout(f"A 股 {stock_code} 财务指标", load)
    except Exception as exc:
        return f"获取 A 股 {stock_code} 财务指标时出错: {exc}"


@tool
def get_stock_news(stock_code: str) -> str:
    """获取 A 股个股新闻。"""

    def load():
        code = normalize_stock_code(stock_code)
        news = ak.stock_news_em(symbol=code)
        if news is None or news.empty:
            return f"未找到 {code} 的相关新闻"
        news_list = []
        for _, row in news.head(8).iterrows():
            news_list.append(
                {
                    "标题": row.get("新闻标题", ""),
                    "发布时间": str(row.get("发布时间", "")),
                    "文章来源": row.get("文章来源", ""),
                    "新闻链接": row.get("新闻链接", ""),
                }
            )
        return json.dumps(news_list, ensure_ascii=False, indent=2)

    try:
        return _with_timeout(f"A 股 {stock_code} 新闻", load)
    except Exception as exc:
        return f"获取 A 股 {stock_code} 新闻时出错: {exc}"


@tool
def get_recommendations(stock_code: str) -> str:
    """获取 A 股研报与盈利预测摘要。"""

    def load():
        code = normalize_stock_code(stock_code)
        forecast = ak.stock_profit_forecast_ths(symbol=code)
        reports = ak.stock_research_report_em(symbol=code)
        forecast_records = forecast.head(8).fillna("").to_dict(orient="records") if forecast is not None and not forecast.empty else []
        report_records = reports.head(8).fillna("").to_dict(orient="records") if reports is not None and not reports.empty else []
        if not forecast_records and not report_records:
            return f"未找到 {code} 的机构预测或研报摘要"
        return json.dumps(
            {
                "股票代码": code,
                "股票名称": _lookup_stock_name(code),
                "盈利预测": forecast_records,
                "研报摘要": report_records,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    try:
        return _with_timeout(f"A 股 {stock_code} 研报摘要", load)
    except Exception as exc:
        return f"获取 A 股 {stock_code} 研报摘要时出错: {exc}"


@tool
def compare_stocks(stock_codes: str) -> str:
    """对比多只 A 股的关键指标。传入格式如 600519,000858,300750。"""

    def load():
        codes = [normalize_stock_code(item) for item in stock_codes.split(",") if item.strip()]
        comparison = []
        for code in codes:
            try:
                quote = get_realtime_quote(code)
                comparison.append(
                    {
                        "股票代码": quote.get("股票代码"),
                        "股票名称": quote.get("股票名称"),
                        "最新价": quote.get("最新价"),
                        "涨跌幅": quote.get("涨跌幅"),
                        "换手率": quote.get("换手率"),
                        "市盈率动态": quote.get("市盈率动态"),
                        "市净率": quote.get("市净率"),
                        "总市值": quote.get("总市值"),
                        "成交额": quote.get("成交额"),
                        "数据源": quote.get("数据源"),
                    }
                )
            except Exception as exc:
                comparison.append(
                    {
                        "股票代码": code,
                        "股票名称": _lookup_stock_name(code),
                        "状态": "快速行情接口暂未返回",
                        "错误": str(exc),
                        "建议": "可稍后重试，或单独查询该股票的行情/财务数据。",
                    }
                )
        return json.dumps(comparison, ensure_ascii=False, indent=2)

    try:
        return _with_timeout(f"A 股对比 {stock_codes}", load)
    except Exception as exc:
        return f"对比 A 股时出错: {exc}"


@tool
def search_financial_news(query: str) -> str:
    """搜索财经新闻和市场信息，优先基于东方财富/财经资讯聚合源。"""

    def load():
        news = ak.stock_news_em(symbol=query)
        if news is None or news.empty:
            return f"未找到关于“{query}”的财经新闻"
        news_list = []
        for _, row in news.head(8).iterrows():
            news_list.append(
                {
                    "标题": row.get("新闻标题", ""),
                    "发布时间": str(row.get("发布时间", "")),
                    "文章来源": row.get("文章来源", ""),
                    "新闻链接": row.get("新闻链接", ""),
                }
            )
        return json.dumps(news_list, ensure_ascii=False, indent=2)

    try:
        return _with_timeout(f"财经新闻 {query}", load)
    except Exception as exc:
        return f"搜索财经新闻时出错: {exc}"


@tool
def think(reflection: str) -> str:
    """用于在复杂分析中整理思路和中间结论。"""
    return f"思考已记录: {reflection}"


SYSTEM_PROMPT = (
    "你是一位专业的 A 股财经研究分析师，擅长股票分析、财务数据解读、研报摘要和量价趋势研判。"
    "你只能回答与股票、公司、财务指标和市场新闻相关的问题。请优先调用工具获取事实数据，再给出中文分析结论。"
    "对于投资建议，请明确提示风险，不做无依据预测。当前助手不提供模型训练或价格预测功能；"
    "如果用户需要预测，请引导其使用平台中的独立股票预测模块。"
)


TOOLS = [
    get_stock_info,
    get_stock_history,
    get_financial_statement,
    get_stock_news,
    get_recommendations,
    compare_stocks,
    search_financial_news,
    think,
]
