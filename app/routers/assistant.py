from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from sse_starlette.sse import EventSourceResponse

from app.schemas.assistant import ChatRequest, ChatResponse, ToolInfo
from app.services.assistant.capabilities import ASSISTANT_CAPABILITIES
from app.services.assistant.llm_service import get_agent
from app.services.assistant.stream_service import generic_chat_fallback, stream_chat_events
from app.services.assistant.tools import TOOLS


router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.get("/health")
def assistant_health():
    return {
        "status": "healthy",
        "runtime_mode": "main-platform-local-tools",
        "tools_count": len(TOOLS),
    }


@router.get("/tools", response_model=list[ToolInfo])
def assistant_tools():
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "args_schema": tool.args_schema.model_json_schema()
            if getattr(tool, "args_schema", None) is not None
            else {},
        }
        for tool in TOOLS
    ]


@router.get("/capabilities")
def assistant_capabilities():
    return ASSISTANT_CAPABILITIES


@router.post("/chat", response_model=ChatResponse)
async def assistant_chat(request: ChatRequest):
    try:
        agent = get_agent()
        result = await agent.ainvoke({"messages": [HumanMessage(content=request.message)]})
        return ChatResponse(response=result["messages"][-1].content)
    except Exception as exc:
        return ChatResponse(response=generic_chat_fallback(request.message, str(exc)))


@router.get("/chat/stream")
async def assistant_stream_chat(message: str):
    return EventSourceResponse(stream_chat_events(message))
