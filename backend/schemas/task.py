from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class TaskCreate(BaseModel):
    session_id: str
    prompt: str

class TaskResponse(BaseModel):
    task_id: str
    status: str

class TaskDetails(BaseModel):
    id: str
    session_id: str
    prompt: str
    status: str
    selected_agent_id: Optional[str] = None
    match_score: Optional[float] = None
    reason: Optional[str] = None
    skipped_agents: List[Dict[str, Any]] = []
    created_at: str
    completed_at: Optional[str] = None
    execution_time_ms: Optional[int] = None
    result: Optional[str] = None

class AgentResponse(BaseModel):
    id: str
    name: str
    role: str
    capabilities: List[str]
    tools: List[str] = []
    model: Optional[str] = None
    cubicle: Optional[str] = None
    status: str
    enabled: bool
    tasks_completed: int
    tokens_used: int
    execution_time_sum: int
