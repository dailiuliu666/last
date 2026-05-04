# 毕设项目迁移文档

## 1. 项目背景

这是一个毕业设计项目，目标是构建一个统一平台，整合以下 3 个模块：

1. 量化模块
2. 股票预测模块
3. AI 财经助手模块

技术路线：

- 后端：FastAPI
- 前端：Jinja2 + 原生 JavaScript + CSS
- 数据库：MySQL
- 运行环境：conda `finance`

新项目目录：

`D:\My_Project\last\graduation_finance_platform`

---

## 2. 当前项目路径

### 2.1 新平台项目
`D:\My_Project\last\graduation_finance_platform`

### 2.2 AI 助手独立项目
`D:\My_Project\Agent系统\从零构建 AI 财经助手：LangChain + MCP + 多 Agent 实战教程`

### 2.3 股票预测参考源文件
`C:\Users\dell\Desktop\预测股票代码\6main_clean.py`

---

## 3. 当前运行方式

进入 conda 环境：

```powershell
conda activate finance
cd D:\My_Project\last\graduation_finance_platform
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

访问地址：

- 首页：`http://127.0.0.1:8001/`
- 量化模块：`http://127.0.0.1:8001/quant`
- 预测模块：`http://127.0.0.1:8001/predictor`
- AI 助手页：`http://127.0.0.1:8001/assistant`
- Swagger：`http://127.0.0.1:8001/docs`

---

## 4. 数据库状态

当前数据库已经统一为 **MySQL**，不要改回 SQLite。

`.env` 中已经使用 MySQL 配置：

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DB=graduation_finance`

数据库已经创建，表也已经初始化。

---

## 5. 已完成工作

## 5.1 平台层

已经完成：

- FastAPI 新项目骨架
- 页面路由
- MySQL 接通
- 项目已能正常启动
- 统一门户的基础页面已存在

关键文件：

- `app/main.py`
- `app/core/config.py`
- `app/core/database.py`
- `app/routers/pages.py`

---

## 5.2 量化模块

量化模块已经形成真实可运行链路。

### 已完成的能力

1. 科创板基础资料同步
2. 科创板日线同步
3. 内置因子初始化
4. 单日因子计算
5. 区间批量因子计算
6. 基础评分
7. ML 模型定义
8. ML 模型训练
9. ML 预测
10. 个股因子快照
11. 基础评分和 ML 结果对比
12. 前端量化展示页

### 当前主要接口

- `GET /api/quant/overview`
- `POST /api/quant/sync/star-board/basic`
- `POST /api/quant/sync/star-board/daily`
- `POST /api/quant/factors/bootstrap`
- `POST /api/quant/factors/calculate`
- `POST /api/quant/factors/calculate-range`
- `GET /api/quant/factors`
- `POST /api/quant/factors/custom`
- `POST /api/quant/scores`
- `GET /api/quant/models`
- `POST /api/quant/models`
- `POST /api/quant/models/train`
- `POST /api/quant/models/predict`
- `GET /api/quant/stocks/{ts_code}/factors`
- `GET /api/quant/models/{model_id}/stocks/{ts_code}/prediction`

### 当前量化页面

`app/templates/quant/dashboard.html`

已具备：

- 数据同步操作
- 因子初始化和计算
- 基础评分展示
- 模型定义与训练
- ML 预测
- 个股分析
- 基础评分和 ML 结果对比
- 数据概览卡片
- 日志输出区

### 量化模块功能理解

量化模块本质上是：

- 先确定股票池（科创板）
- 计算多因子
- 对股票横向打分排序
- 再用 ML 模型学习“因子 -> 未来收益”的关系

它偏向：

- 量化选股
- 股票排序
- 结果对比

不是单纯的个股 K 线分析器。

---

## 5.3 预测模块

预测模块已经完成服务化和第一版 Web 展示。

### 已完成能力

1. 获取股票数据
2. 数据预览
3. 模型训练
4. 单点预测
5. 未来 5 日预测
6. 已保存模型列表
7. 模型加载校验
8. 模型选择
9. 训练效果指标展示
10. 训练曲线可视化
11. 测试集真实值 vs 预测值对比
12. 未来 5 日预测图表

### 当前支持模型

- `LSTM`
- `CNN`
- `CNN-LSTM`

### 当前页面

`app/templates/predictor/index.html`

### 当前已展示指标

- `MAE`
- `MSE`
- `RMSE`
- `R²`
- `方向准确率`

### 参考源代码

预测模块的设计参考：

`C:\Users\dell\Desktop\预测股票代码\6main_clean.py`

其桌面版中的以下可视化思路已移植到 Web：

- 训练曲线
- 测试集预测对比
- 未来 5 日预测展示

---

## 5.4 AI 助手模块

### 当前状态

AI 助手已经完成第一阶段正式迁移，现在是主平台内置模块。

访问地址：

`http://127.0.0.1:8001/assistant`

AI 助手由主平台直接提供。

### 当前接口

- `GET /api/assistant/health`
- `GET /api/assistant/tools`
- `GET /api/assistant/capabilities`
- `POST /api/assistant/chat`
- `GET /api/assistant/chat/stream`

### 当前能力

- 实时行情、市值、市盈率、市净率、成交额
- 历史日线行情
- 财务指标
- 个股新闻
- 研报、盈利预测、机构观点
- 多股横向对比
- 财经新闻搜索
- LLM Agent 兜底回答

股票代码类问题优先走快速工具模式，支持 SSE 流式返回、工具超时、心跳提示和 90 秒总超时。

---

## 6. 当前最大未完成任务

## 6.1 任务一：首页重构 + 整体展示优化

AI 助手入口已经可用，下一步可以开始做首页重构和整体展示优化。

### 目标

让整个系统更像成品毕设，而不是多个功能页拼接。

### 建议改造内容

1. 首页模块卡片
2. 系统总览说明
3. 三大模块介绍
4. 平台能力说明
5. 更丰富的前端布局
6. 更多状态卡片和可视化面板
7. 更适合答辩展示的视觉结构

---

## 6.2 任务二：前端代码量和展示复杂度提升

这是一个重要额外要求。

### 背景

毕业设计有 **5000 行代码要求**。

因此后续开发时：

- 前端可以更复杂一些
- 可以增加更多面板、说明区、图表区、状态区
- 可以合理增加可视化、交互和展示层代码

### 可增加的内容方向

1. 首页总览面板
2. 系统流程说明区
3. 数据统计区
4. 模块状态区
5. 历史记录区
6. 图表联动区
7. 个股详情增强区
8. ML 结果分析区
9. 训练日志和状态进度区
10. 导出、过滤、切换视图等 UI

---

## 7. 建议的后续优先级

建议按下面顺序继续：

### 第一优先级
做首页重构与整体展示优化。

### 第二优先级
优化 AI 助手页面 UI 和交互细节。

### 第三优先级
继续扩展前端复杂度和展示丰富度，以满足代码量与答辩效果。

### 第四优先级
之后再决定是否继续加新功能，或继续深挖量化模块。

---

## 8. 对后续开发者的要求

如果是新窗口继续接手，请遵守以下原则：

1. 不要推翻现有结构重做
2. 保持 MySQL，不要切回 SQLite
3. 保持 AI 助手作为主平台内置模块
4. 前端尽量做得更丰富一些
5. 代码量要求较高，可以合理增加展示层代码
6. 量化模块和预测模块现有功能已经打通，不要破坏已有链路

---

## 9. 新窗口接手时可直接使用的简短说明

请继续接手：

`D:\My_Project\last\graduation_finance_platform`

当前量化模块、预测模块和 AI 助手都已经基本打通。AI 助手已迁入主平台 `/api/assistant/...`。

下一步重点做首页重构、整体展示优化，以及 AI 助手页面细节优化。

注意：
- 数据库必须保持 MySQL
- 不要改回 SQLite
- 保持 AI 助手主平台内置结构
- 前端尽量做复杂、美观、面板丰富
- 我有 5000 行代码要求，后续可以增加展示层和可视化代码量
- 不要推翻当前已完成的量化与预测模块结构
