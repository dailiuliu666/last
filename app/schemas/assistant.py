from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户问题")


class ChatResponse(BaseModel):
    response: str = Field(..., description="助手回答")


class ToolInfo(BaseModel):
    name: str
    description: str
    args_schema: dict = Field(default_factory=dict)
