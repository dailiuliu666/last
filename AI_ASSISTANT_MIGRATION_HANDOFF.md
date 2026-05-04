# AI 助手迁移状态说明

当前日期：2026-05-04

## 当前结论

AI 助手已经完成第一阶段正式迁移，成为主平台 FastAPI 内置模块。

主平台只需要启动一个服务：

```powershell
cd "D:\My_Project\last\graduation_finance_platform"
conda activate finance
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

访问地址：

```text
http://127.0.0.1:8001/assistant
```

AI 助手由主平台直接提供。

## 已迁移结构

```text
app/routers/assistant.py
app/schemas/assistant.py
app/services/assistant/
  capabilities.py
  llm_service.py
  market_data.py
  stream_service.py
  tools.py
app/templates/assistant/index.html
app/static/js/assistant.js
```

## 当前接口

```text
GET  /assistant
GET  /api/assistant/health
GET  /api/assistant/tools
GET  /api/assistant/capabilities
POST /api/assistant/chat
GET  /api/assistant/chat/stream
```

## 当前工具能力

```text
get_stock_info
get_stock_history
get_financial_statement
get_stock_news
get_recommendations
compare_stocks
search_financial_news
think
```

股票代码类问题优先走快速工具模式，逐项流式返回；泛财经问题走 LLM Agent 兜底。保留工具超时、SSE 心跳和 90 秒总超时。

## 验证记录

已验证：

```text
conda run -n finance python -m py_compile ...
GET /assistant -> 200
GET /api/assistant/health -> healthy
GET /api/assistant/tools -> 8 tools
```

真实工具调用 `600519` 快速行情可返回东方财富数据。

## 后续注意

- 不要把预测模块迁回 AI 助手，预测仍属于主平台独立模块。
- 后续可以继续优化 `/assistant` 前端体验和 README/API 文档。
