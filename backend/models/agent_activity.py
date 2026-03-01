from pydantic import BaseModel, Field
from typing import Literal


class AgentCard(BaseModel):
    name: str
    description: str
    capabilities: list[str]
    endpoint: str
    version: str = "1.0.0"


class A2ATask(BaseModel):
    task_id: str
    from_agent: str
    to_agent: str
    task_type: str
    payload: dict = Field(default_factory=dict)
    status: Literal["submitted", "working", "completed", "failed"] = "submitted"
    result: dict | None = None
    created_at: str = ""
    completed_at: str | None = None
