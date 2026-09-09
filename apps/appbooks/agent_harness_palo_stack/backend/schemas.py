"""Pydantic request bodies for the appbook API."""
from __future__ import annotations

from pydantic import BaseModel


class EmbedReq(BaseModel):
    text: str


class WriteReq(BaseModel):
    path: str
    content: str


class SearchReq(BaseModel):
    query: str
    technique: str = "hybrid"
    k: int = 5


class ChatReq(BaseModel):
    message: str
    thread_id: str = "appbook"


class FactReq(BaseModel):
    fact: str


class ToolQuery(BaseModel):
    query: str


class SkillSourceReq(BaseModel):
    name: str
    description: str
    body: str


class AutomationReq(BaseModel):
    name: str
    select_sql: str
    cadence_hours: int = 24
    description: str = ""


class PromoteReq(BaseModel):
    workflow_id: str


class AgentReq(BaseModel):
    prompt: str
    thread_id: str = "appbook"
