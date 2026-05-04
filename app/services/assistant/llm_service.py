from __future__ import annotations

import os

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from app.services.assistant.tools import SYSTEM_PROMPT, TOOLS


ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
MODEL_NAME = os.getenv("MODEL_NAME", "glm-4.6v")

_llm = None
_agent = None


def get_llm():
    global _llm
    if _llm is None:
        if not ZHIPU_API_KEY:
            raise RuntimeError("未配置 ZHIPU_API_KEY，无法启动泛财经 LLM Agent。")
        _llm = ChatOpenAI(
            model=MODEL_NAME,
            openai_api_key=ZHIPU_API_KEY,
            openai_api_base=ZHIPU_BASE_URL,
            temperature=0.3,
        )
    return _llm


def get_agent():
    global _agent
    if _agent is None:
        _agent = create_agent(get_llm(), tools=TOOLS, system_prompt=SYSTEM_PROMPT)
    return _agent
