import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..database import async_session
from ..models import Agent, Message, Session

router = APIRouter(tags=["agents"])
logger = logging.getLogger(__name__)


@router.get("/api/sessions/{session_id}/agents")
async def list_agents(session_id: str):
    async with async_session() as db:
        result = await db.execute(
            select(Agent)
            .where(Agent.session_id == session_id)
            .order_by(Agent.layer, Agent.created_at)
        )
        agents = result.scalars().all()
    return [
        {
            "id": ag.id,
            "session_id": ag.session_id,
            "role": ag.role,
            "display_name": ag.display_name,
            "emoji": ag.emoji,
            "model": ag.model_override or ag.model,
            "layer": ag.layer,
            "status": ag.status,
            "task": ag.task,
            "dependencies": ag.dependencies,
            "output_summary": ag.output_summary,
            "tokens_used": ag.tokens_used,
        }
        for ag in agents
    ]


class ModelOverrideRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_id: str


@router.patch("/api/agents/{agent_id}/model")
async def override_model(agent_id: str, req: ModelOverrideRequest):
    async with async_session() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        sess_result = await db.execute(
            select(Session).where(Session.id == agent.session_id)
        )
        session = sess_result.scalar_one_or_none()
        if session and session.status == "running":
            raise HTTPException(status_code=400, detail="Cannot change model while session is running")

        agent.model_override = req.model_id
        await db.commit()
    return {"agent_id": agent_id, "model_override": req.model_id}


@router.get("/api/agents/{agent_id}/output")
async def get_agent_output(agent_id: str):
    async with async_session() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": agent_id,
        "role": agent.role,
        "display_name": agent.display_name,
        "output": agent.output,
        "tokens_used": agent.tokens_used,
        "status": agent.status,
    }


@router.get("/api/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    async with async_session() as db:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp)
        )
        messages = result.scalars().all()
    return [
        {
            "id": m.id,
            "from_agent_id": m.from_agent_id,
            "to_agent_id": m.to_agent_id,
            "type": m.type,
            "content": m.content,
            "resolved": m.resolved,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
        }
        for m in messages
    ]
