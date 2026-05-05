# 股价预测论文实验交接文档

当前日期：2026-05-05

## 1. 当前任务定位

当前任务不是继续开发 Web 系统，而是切换到“论文实验工作流”，围绕股价预测模块产出：

1. 不同行业代表股票的预测实验结果
2. 不同模型之间的指标对比
3. 可直接用于论文插图的高清图表
4. 可直接用于论文表格的指标汇总
5. 可直接写进论文正文的实验分析材料

## 2. 工作方式结论

不要复制整个项目，也不要新建一份独立预测小项目。

正确做法是：

```text
在当前主项目内，单独建立论文实验目录：
experiments/predictor_paper/
```

理由：

- 避免系统代码和论文实验代码分叉
- 保证论文实验与系统预测逻辑一致
- 方便后续统一修改模型、指标和图表
- 能把 notebook、图表、表格、分析结论集中管理

## 3. 环境结论

继续使用现有 `conda` 环境：

```text
finance
```

当前已确认可用：

- TensorFlow
- pandas
- scikit-learn
- statsmodels
- matplotlib

当前还缺：

- `jupyter`
- `seaborn`

推荐下一窗口先执行：

```powershell
conda activate finance
pip install jupyter seaborn
```

## 4. 当前预测模块已具备能力

模型：

- `LSTM`
- `CNN`
- `CNN-LSTM`
- `ARIMA-LSTM`

指标：

- `R²`
- `MAE`
- `MSE`
- `RMSE`
- `MAPE`

图表：

- 特征相关性热力图
- 训练曲线图
- 测试集真实值 vs 预测值对比图
- 误差趋势图
- 未来 5 日预测图

相关代码位置：

```text
app/services/predictor/data_fetcher.py
app/services/predictor/preprocess.py
app/services/predictor/trainer.py
app/services/predictor/arima_lstm.py
app/services/predictor/metrics.py
app/routers/predictor.py
```

## 5. 论文实验目标

建议论文实验主题明确成：

```text
比较不同预测模型在科创板不同行业代表股票上的预测表现，
分析模型在行业差异下的适用性与稳定性。
```

实验维度：

1. 不同行业
2. 不同模型
3. 统一训练参数
4. 统一评价指标

## 6. 股票选择策略

建议从科创板主要行业中选 **4 到 6 个行业**，每个行业选 **1 只代表股票**。

优先行业建议：

1. 半导体
2. 医药生物
3. 高端装备 / 机械
4. 新能源 / 电力设备
5. 软件 / 计算机
6. 新材料

选择原则：

- 必须是科创板股票
- 历史日线数据较完整
- 行业代表性较强
- 避免停牌异常样本
-预计预测效果会比较好

重要现状：

当前本地 `graduation_finance.db` 里的 `stock_basic` 科创板数据为空，不能直接靠本地 SQLite 做行业筛选。

因此下一窗口必须先做：

1. 从 Tushare 或 AkShare 获取科创板股票清单
2. 按行业统计候选股票
3. 人工确认每个行业最终代表股票

## 7. 实验统一口径

第一轮实验建议统一参数，不做参数搜索，先保证横向对比公平。

建议固定：

```text
selected_features = [open, close, high, low, volume, amount]
selected_target = close
look_back = 50
epochs = 80
batch_size = 32
dropout_rate = 0.2
learning_rate = 0.001
```

所有股票都跑这 4 个模型：

- `LSTM`
- `CNN`
- `CNN-LSTM`
- `ARIMA-LSTM`

## 8. 第一轮实验范围

为了控制工作量，建议第一轮只做：

```text
4 个行业 × 1 只股票 × 4 个模型
```

总计：

```text
16 组实验
```

如果第一轮跑通、图表和表格齐全，再扩展到 5 到 6 个行业。

## 9. 目录结构建议

下一窗口直接创建：

```text
experiments/
  predictor_paper/
    predictor_paper_experiment.ipynb
    predictor_runner.py
    stock_selection.csv
    outputs/
      metrics/
        metrics_summary.csv
        metrics_summary.xlsx
        stock_model_metrics_long.csv
      charts/
        single_stock/
        comparison/
      notes/
        experiment_notes.md
        analysis_summary.md
```

## 10. 要产出的图表

### 单只股票级别

每只股票、每个模型建议生成：

1. 特征相关性热力图
2. 训练损失曲线图
3. 真实值 vs 预测值对比折线图
4. 误差趋势图

### 跨模型 / 跨行业对比级别

建议至少生成：

1. 同一股票不同模型的 `MAE` 柱状图
2. 同一股票不同模型的 `RMSE` 柱状图
3. 不同行业股票在同一模型下的 `MAPE` 对比图
4. 各模型平均 `R²` / `RMSE` 汇总柱状图

图表要求：

- 白底
- 线条清晰
- 图例简洁
- 支持导出高清 PNG
- 能直接作为论文插图使用

## 11. 要产出的表格

建议至少产出：

### 表 1：实验样本股票信息表

字段：

- 行业板块
- 股票代码
- 股票名称
- 起止时间
- 样本数

### 表 2：单股多模型指标对比表

字段：

- 股票代码
- 模型名称
- R²
- MAE
- MSE
- RMSE
- MAPE

### 表 3：各行业最佳模型汇总表

字段：

- 行业
- 股票代码
- 最优模型
- 依据指标
- 结论说明

### 表 4：所有模型平均指标汇总表

字段：

- 模型名称
- 平均 R²
- 平均 MAE
- 平均 MSE
- 平均 RMSE
- 平均 MAPE

## 12. 论文分析写作建议

直接些这部分的论文，符合本科毕业设计论文要求，分析不要泛泛写“模型效果较好”，而要绑定具体指标和行业差异。

可写的分析角度：

1. 哪种模型在多数行业上更稳定
2. `ARIMA-LSTM` 是否在趋势更明显股票上占优
3. `CNN-LSTM` 是否在波动更强股票上更有优势
4. 不同行业是否会导致预测误差结构不同
5. 哪个指标最能体现模型优劣

示例写法：

```text
在半导体代表股票上，ARIMA-LSTM 的 RMSE 最低，且 MAPE 也优于其他模型，
说明在该样本上，趋势项与残差项分离建模可以提升预测稳定性。
```

## 13. 下一窗口执行顺序

1. 安装 `jupyter` 和 `seaborn`
2. 创建 `experiments/predictor_paper/` 目录结构
3. 新建 notebook
4. 获取科创板股票清单并按行业筛选候选股票
5. 人工确认第一轮 4 个行业代表股票
6. 封装统一实验函数
7. 先跑 1 只股票 × 4 个模型做 smoke test
8. 确认图表和指标表输出正常
9. 再批量跑第一轮 16 组实验
10. 导出表格、图片和分析摘要

## 14. 新窗口可直接使用的任务指令

把下面这段直接发给新窗口：

```text
我们现在不继续开发 Web 系统，而是切换到论文实验工作流。

项目路径：
D:\My_Project\last\graduation_finance_platform

请先阅读根目录：
PAPER_PREDICTOR_EXPERIMENT_HANDOFF.md

任务边界：
1. 不复制整个项目
2. 在主项目内单独建立：
   experiments/predictor_paper/
3. 使用现有 conda 环境：
   finance
4. 如缺依赖，先安装：
   pip install jupyter seaborn

实验目标：
围绕股价预测模块做论文实验，选取科创板 4 个主要行业，每个行业 1 只代表股票，
分别运行：
- LSTM
- CNN
- CNN-LSTM
- ARIMA-LSTM

统一输出：
1. 指标：
   - R²
   - MAE
   - MSE
   - RMSE
   - MAPE
2. 图表：
   - 特征相关性热力图
   - 训练损失图
   - 真实值 vs 预测值对比图
   - 误差趋势图
3. 文件：
   - CSV / Excel 指标汇总表
   - 高清 PNG 图表
   - 简短实验分析结论

执行顺序：
1. 建立 experiments/predictor_paper/ 目录和 notebook
2. 获取科创板行业股票清单
3. 确认第一轮 4 个行业代表股票
4. 先跑 1 只股票 × 4 模型 smoke test
5. 再跑第一轮全部实验

限制：
1. 不改现有神经网络核心结构
2. 尽量复用当前 predictor 模块代码
3. 重点是论文实验可复现，不是系统页面
```
