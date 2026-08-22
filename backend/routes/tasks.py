from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from typing import List, Optional
from schemas.task import TaskCreate, TaskResponse, TaskDetails, AgentResponse
from services.orchestration.dispatch_service import DispatchService
from repositories.decision_repository import DecisionRepository

router = APIRouter(prefix="/api", tags=["tasks"])
repo = DecisionRepository()
dispatch_service = DispatchService()

# --- Tasks ---

@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, background_tasks: BackgroundTasks):
    try:
        task_id = repo.create_task(payload.session_id, payload.prompt)
        # Run state machine execution asynchronously in the background
        background_tasks.add_task(dispatch_service.run_task_execution, task_id)
        return {"task_id": task_id, "status": "RECEIVED"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/tasks/{id}", response_model=TaskDetails)
def get_task_details(id: str):
    task = repo.get_task(id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task

@router.post("/tasks/{id}/retry", response_model=dict)
async def retry_task(id: str, background_tasks: BackgroundTasks):
    task = repo.get_task(id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    # Reset status and trigger execution again
    repo.update_task(id, {"status": "RECEIVED", "completed_at": None, "result": None})
    if task["selected_agent_id"]:
        repo.update_agent_status(task["selected_agent_id"], "IDLE")
        
    background_tasks.add_task(dispatch_service.run_task_execution, id)
    return {"status": "success", "message": "Task execution retried successfully"}

@router.post("/tasks/{id}/cancel", response_model=dict)
async def cancel_task(id: str):
    task = repo.get_task(id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
    repo.update_task(id, {"status": "CANCELLED"})
    if task["selected_agent_id"]:
        repo.update_agent_status(task["selected_agent_id"], "IDLE")
        await dispatch_service.broadcast_state(id, task["session_id"], "IDLE", {
            "agent_id": task["selected_agent_id"],
            "status": "IDLE"
        })
        
    return {"status": "success", "message": "Task execution cancelled successfully"}

# --- Agents ---

@router.get("/agents", response_model=List[AgentResponse])
def get_agents():
    return repo.get_agent_registry()

@router.get("/agents/{agent_id}", response_model=AgentResponse)
def get_agent_details(agent_id: str):
    agent = repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent
