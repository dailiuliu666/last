ASSISTANT_CAPABILITIES = {
    "runtime": {
        "service": "主平台 FastAPI 内置模块",
        "main_chat": "股票代码类问题优先走本地快速工具；泛财经问答懒加载 LLM Agent。",
        "mcp": "当前主平台迁移版不依赖 MCP。",
    },
    "tools": [
        {
            "name": "get_stock_info",
            "use_when": "实时行情、最新价、涨跌幅、成交额、市盈率、市净率、市值。",
        },
        {
            "name": "get_stock_history",
            "use_when": "历史日线、近一个月走势、区间涨跌、开收盘价、成交量。",
        },
        {
            "name": "get_financial_statement",
            "use_when": "财务指标、营业收入、净利润、归母净利润、净资产。",
        },
        {
            "name": "get_stock_news",
            "use_when": "某只股票相关新闻、市场消息、新闻链接。",
        },
        {
            "name": "get_recommendations",
            "use_when": "盈利预测、机构预测、研报摘要、评级。",
        },
        {
            "name": "compare_stocks",
            "use_when": "多只股票横向比较。",
        },
        {
            "name": "search_financial_news",
            "use_when": "关键词财经新闻搜索。",
        },
    ],
}
