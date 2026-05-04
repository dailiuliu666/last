from __future__ import annotations

import asyncio
import json
import re
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage

from app.services.assistant.llm_service import get_agent
from app.services.assistant.tools import TOOLS


def extract_stock_codes(message: str) -> list[str]:
    codes = re.findall(r"(?<!\d)([0-9]{6})(?!\d)", message or "")
    unique_codes: list[str] = []
    for code in codes:
        if code not in unique_codes:
            unique_codes.append(code)
    return unique_codes


def select_fast_tools(message: str) -> list[dict] | None:
    codes = extract_stock_codes(message)
    if not codes:
        return None

    text = message or ""
    if len(codes) > 1 or any(word in text for word in ("对比", "比较", "横向")):
        return [{"name": "compare_stocks", "args": {"stock_codes": ",".join(codes)}, "title": "多股横向对比"}]

    code = codes[0]
    wants_history = any(word in text for word in ("走势", "日线", "历史", "近一个月", "区间", "K线", "k线"))
    wants_financial = any(word in text for word in ("财务", "指标", "营收", "利润", "ROE", "roe", "资产负债", "现金流", "基本面", "质量"))
    wants_news = any(word in text for word in ("新闻", "消息", "资讯", "公告"))
    wants_research = any(word in text for word in ("研报", "盈利预测", "机构", "评级", "分析师"))
    wants_analysis = any(word in text for word in ("分析", "综合", "风险", "估值"))

    selected = [{"name": "get_stock_info", "args": {"stock_code": code}, "title": "实时行情与估值"}]
    if wants_history or wants_analysis:
        selected.append({"name": "get_stock_history", "args": {"stock_code": code, "period": "1mo"}, "title": "近一个月日线走势"})
    if wants_financial or wants_analysis:
        selected.append({"name": "get_financial_statement", "args": {"stock_code": code}, "title": "核心财务指标"})
    if wants_news:
        selected.append({"name": "get_stock_news", "args": {"stock_code": code}, "title": "个股新闻"})
    if wants_research or wants_analysis:
        selected.append({"name": "get_recommendations", "args": {"stock_code": code}, "title": "研报与盈利预测"})
    return selected


async def stream_chat_events(message: str) -> AsyncGenerator[dict, None]:
    fast_tools = select_fast_tools(message)
    if fast_tools:
        async for item in _stream_fast_tools(message, fast_tools):
            yield item
        return

    yield {"event": "message", "data": _stream_intro()}
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def produce_agent_events() -> None:
        try:
            agent = get_agent()
            events = agent.astream({"messages": [HumanMessage(content=message)]}, stream_mode="messages")
            async for msg, metadata in events:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        await queue.put(
                            {
                                "event": "tool_call",
                                "data": json.dumps({"name": tc["name"], "args": tc["args"]}, ensure_ascii=False),
                            }
                        )
                elif hasattr(msg, "content") and msg.content:
                    text = msg.content
                    if isinstance(text, list):
                        for item in text:
                            if isinstance(item, dict) and item.get("type") == "text":
                                await queue.put({"event": "message", "data": item.get("text", "")})
                    else:
                        await queue.put({"event": "message", "data": text})
            await queue.put({"event": "done", "data": "[DONE]"})
        except Exception as exc:
            await queue.put({"event": "message", "data": generic_chat_fallback(message, str(exc))})
            await queue.put({"event": "done", "data": "[DONE]"})

    task = asyncio.create_task(produce_agent_events())
    deadline = asyncio.get_running_loop().time() + 90
    try:
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                task.cancel()
                yield {
                    "event": "message",
                    "data": "\n\n> 本次分析已超过 90 秒，已停止继续等待。建议把问题拆成行情、财务、新闻、研报等单项查询后再测试。",
                }
                yield {"event": "done", "data": "[DONE]"}
                return
            try:
                item = await asyncio.wait_for(queue.get(), timeout=min(5, remaining))
            except asyncio.TimeoutError:
                yield {
                    "event": "ping",
                    "data": json.dumps({"message": "仍在处理数据源或等待模型生成，请稍候..."}, ensure_ascii=False),
                }
                continue
            yield item
            if item.get("event") == "done":
                return
    finally:
        if not task.done():
            task.cancel()


async def _stream_fast_tools(message: str, selected_tools: list[dict]) -> AsyncGenerator[dict, None]:
    yield {
        "event": "message",
        "data": "我将使用快速工具模式处理这个股票问题：先逐项查询数据，每拿到一项就立即展示，避免长时间等待完整 Agent。\n\n",
    }
    outputs: list[tuple[str, str]] = []
    for spec in selected_tools:
        yield {"event": "tool_call", "data": json.dumps({"name": spec["name"], "args": spec["args"]}, ensure_ascii=False)}
        yield {"event": "message", "data": f"\n\n### {spec['title']}\n正在调用 `{spec['name']}` 获取数据...\n"}
        result = await invoke_tool_with_timeout(spec["name"], spec["args"])
        outputs.append((spec["title"], result))
        yield {"event": "message", "data": f"\n```text\n{_truncate_text(result, 2500)}\n```\n"}

    yield {"event": "message", "data": _build_fast_summary(message, outputs)}
    yield {"event": "done", "data": "[DONE]"}


async def invoke_tool_with_timeout(tool_name: str, args: dict, timeout: int = 18) -> str:
    tool_map = {tool.name: tool for tool in TOOLS}
    selected = tool_map.get(tool_name)
    if selected is None:
        return f"未找到工具: {tool_name}"
    try:
        result = await asyncio.wait_for(asyncio.to_thread(selected.invoke, args), timeout=timeout)
        return str(result)
    except asyncio.TimeoutError:
        return f"{tool_name} 超过 {timeout} 秒未返回，已跳过该项。建议稍后单独查询这个功能。"
    except Exception as exc:
        return f"{tool_name} 调用失败: {exc}"


def _build_fast_summary(message: str, outputs: list[tuple[str, str]]) -> str:
    failed = [title for title, content in outputs if "超时" in content or "失败" in content or "出错" in content]
    success = [title for title, content in outputs if title not in failed]
    lines = ["\n\n### 阶段性总结", f"本次问题：{message}", ""]
    if success:
        lines.append(f"已成功获取：{'、'.join(success)}。")
    if failed:
        lines.append(f"以下数据源本次不稳定或超时：{'、'.join(failed)}。")
    lines.extend(
        [
            "你可以基于上面的原始数据继续追问，例如“根据这些数据总结风险点”或“只解释估值是否偏高”。",
            "以上内容仅用于教学和研究展示，不构成投资建议。",
        ]
    )
    return "\n".join(lines)


def _truncate_text(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[:max_chars] + "\n...（内容已截断）"


def _stream_intro() -> str:
    return "我先根据你的问题判断需要调用哪些财经数据工具。如果某个数据源较慢，我会尽量保留已拿到的数据并继续生成阶段性结论。\n\n"


def generic_chat_fallback(message: str, error: str) -> str:
    return f"""### 当前泛问答暂不可用

你的问题：{message}

普通聊天 Agent 需要调用 LLM，但当前 LLM 服务返回错误：

```text
{error}
```

现在可稳定使用的是 A 股代码类问答，例如：

- 查询 600519 的实时行情、市值、市盈率和成交额
- 分析 600519 的估值、财务质量、近期走势和主要风险
- 对比 002594,300750,601012 的估值、市值、成交额和财务质量
- 最近 600519 有哪些新闻和研报观点

如果要恢复“不带股票代码”的泛财经问答，需要更新 `.env` 里的 LLM API Key。"""
