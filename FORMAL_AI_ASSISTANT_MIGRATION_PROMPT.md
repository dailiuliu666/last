# AI 助手正式迁移完成记录

## 迁移结果

AI 助手已经迁入主平台：

```text
D:\My_Project\last\graduation_finance_platform
```

现在主平台只启动一个 FastAPI 服务，端口 `8001`。`/assistant` 页面直接使用主平台模板、静态资源和 `/api/assistant/...` 接口。

## 启动方式

```powershell
cd "D:\My_Project\last\graduation_finance_platform"
conda activate finance
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

AI 助手由主平台直接提供。

## 已完成文件

```text
app/routers/assistant.py
app/schemas/assistant.py
app/services/assistant/capabilities.py
app/services/assistant/llm_service.py
app/services/assistant/market_data.py
app/services/assistant/stream_service.py
app/services/assistant/tools.py
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

## 设计约束

- 股票预测模块保持主平台独立模块，不迁回 AI 助手。
- 股票代码类问题优先走快速工具模式。
- 保留 SSE 心跳、工具超时、90 秒总超时。
- LLM/Agent 懒加载，避免主平台启动时阻塞。

## 下一步

后续工作可以集中在：

1. 优化 AI 助手页面 UI。
2. 补充接口文档和演示问题。
3. 做全平台联调和演示流程整理。
