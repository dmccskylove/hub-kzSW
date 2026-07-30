"""Pydantic 数据模型"""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: int
    message: str


class ChatResponse(BaseModel):
    reply: str
    skill_used: str | None = None
    memory_items_extracted: int = 0


class FlushResponse(BaseModel):
    user_updates: list[str] = []
    memory_entries: list[str] = []
    summary: str = ""


class SkillInfo(BaseModel):
    name: str
    description: str
    triggers: list[str]
    size_tokens: int = 0


class SystemStatus(BaseModel):
    session_id: int
    message_count: int
    skills_available: list[SkillInfo]
    memory_chars: int
