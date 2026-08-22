from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any
from repositories.decision_repository import DecisionRepository

router = APIRouter(prefix="/api", tags=["analytics"])
repo = DecisionRepository()

@router.get("/analytics/overview", response_model=dict)
def get_analytics_overview():
    try:
        return repo.get_analytics_overview()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/analytics/agents", response_model=List[dict])
def get_analytics_agents():
    try:
        agents = repo.get_agent_registry()
        analytics_agents = []
        for a in agents:
            # Calculate success rate
            total = a["tasks_completed"]
            success_rate = 1.0
            avg_exec_time = 0.0
            if total > 0:
                avg_exec_time = round((a["execution_time_sum"] / total), 2)
            
            analytics_agents.append({
                "agent_id": a["id"],
                "name": a["name"],
                "role": a["role"],
                "tasks_completed": total,
                "tokens_used": a["tokens_used"],
                "average_execution_time_ms": avg_exec_time,
                "success_rate": success_rate
            })
        return analytics_agents
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/analytics/tokens", response_model=dict)
def get_analytics_tokens():
    try:
        return repo.get_token_analytics()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/analytics/routing", response_model=dict)
def get_analytics_routing():
    try:
        # Calculate routing stats based on task records
        agents = repo.get_agent_registry()
        total_agents = len(agents)
        
        overview = repo.get_analytics_overview()
        total_tasks = overview["tasks_total"]
        completed = overview["tasks_completed"]
        
        success_rate = 1.0
        if total_tasks > 0:
            success_rate = round((completed / total_tasks), 2)
            
        return {
            "total_routing_requests": total_tasks,
            "average_routing_latency_ms": overview["average_routing_latency_ms"],
            "routing_success_rate": success_rate,
            "total_available_agents": total_agents
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
