import asyncio
import logging
import os
import tempfile
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select

from ..agent_factory import agent_factory
from ..database import async_session, get_db
from ..execution_engine import execution_engine
from ..models import Agent, Message, Result, Session
from ..orchestrator import orchestrator
from ..result_aggregator import result_aggregator
from ..ws_manager import ws_manager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
logger = logging.getLogger(__name__)


class CreateSessionRequest(BaseModel):
    description: str

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if len(v) < 10:
            raise ValueError("description must be at least 10 characters")
        if len(v) > 5000:
            raise ValueError("description must be at most 5000 characters")
        return v


@router.post("/")
async def create_session(req: CreateSessionRequest):
    async with async_session() as db:
        session = Session(
            description=req.description,
            status="draft",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

    try:
        org_data = await orchestrator.analyze(req.description)
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestrator error: {str(e)}")

    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one()
        session.title = org_data.get("title", "AI Organization")
        await db.commit()
        await db.refresh(session)

    try:
        agents = await agent_factory.create_agents(session_id, org_data, req.description)
    except Exception as e:
        logger.error(f"AgentFactory failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent creation error: {str(e)}")

    async with async_session() as db:
        await db.execute(
            Session.__table__.update()
            .where(Session.id == session_id)
            .values(total_agents=len(agents), updated_at=datetime.utcnow())
        )
        await db.commit()

    for ag in agents:
        await ws_manager.broadcast(session_id, ws_manager.agent_created(ag))

    return {
        "session_id": session_id,
        "title": org_data.get("title", "AI Organization"),
        "summary": org_data.get("summary", ""),
        "status": "draft",
        "agents": [
            {
                "id": ag.id,
                "role": ag.role,
                "display_name": ag.display_name,
                "emoji": ag.emoji,
                "model": ag.model,
                "layer": ag.layer,
                "task": ag.task,
                "dependencies": ag.dependencies,
            }
            for ag in agents
        ],
    }


@router.get("/")
async def list_sessions(limit: int = 20, offset: int = 0):
    async with async_session() as db:
        result = await db.execute(
            select(Session)
            .order_by(Session.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        sessions = result.scalars().all()
    return [
        {
            "session_id": s.id,
            "title": s.title,
            "status": s.status,
            "total_agents": s.total_agents,
            "completed_agents": s.completed_agents,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]


@router.get("/{session_id}")
async def get_session(session_id: str):
    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        agents_result = await db.execute(
            select(Agent)
            .where(Agent.session_id == session_id)
            .order_by(Agent.layer, Agent.created_at)
        )
        agents = agents_result.scalars().all()

        msgs_result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp.desc())
            .limit(50)
        )
        messages = msgs_result.scalars().all()

    return {
        "session_id": session.id,
        "title": session.title,
        "description": session.description,
        "status": session.status,
        "total_agents": session.total_agents,
        "completed_agents": session.completed_agents,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "agents": [
            {
                "id": ag.id,
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
                "created_at": ag.created_at.isoformat() if ag.created_at else None,
                "completed_at": ag.completed_at.isoformat() if ag.completed_at else None,
            }
            for ag in agents
        ],
        "messages": [
            {
                "id": m.id,
                "from_agent_id": m.from_agent_id,
                "to_agent_id": m.to_agent_id,
                "type": m.type,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in reversed(messages)
        ],
    }


@router.post("/{session_id}/run")
async def run_session(session_id: str):
    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.status == "running":
            return {"status": "already_running"}

        agents_result = await db.execute(
            select(Agent)
            .where(Agent.session_id == session_id)
            .order_by(Agent.layer, Agent.created_at)
        )
        agents = agents_result.scalars().all()

        session.status = "running"
        session.updated_at = datetime.utcnow()
        await db.commit()

    asyncio.create_task(execution_engine.execute_session(session_id, list(agents), ws_manager))
    return {"status": "running"}


@router.post("/{session_id}/pause")
async def pause_session(session_id: str):
    execution_engine.cancel(session_id)
    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if session:
            session.status = "paused"
            session.updated_at = datetime.utcnow()
            await db.commit()
    return {"status": "paused"}


@router.get("/{session_id}/results")
async def get_results(session_id: str):
    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        results_q = await db.execute(
            select(Result).where(Result.session_id == session_id)
        )
        results = results_q.scalars().all()

    if not results and session.status == "completed":
        async with async_session() as db2:
            await result_aggregator.aggregate(session_id, db2)
        async with async_session() as db3:
            results_q = await db3.execute(
                select(Result).where(Result.session_id == session_id)
            )
            results = results_q.scalars().all()

    return {
        "session_id": session_id,
        "results": [
            {
                "id": r.id,
                "format": r.format,
                "content": r.content,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ],
    }


@router.get("/{session_id}/export")
async def export_session(session_id: str, format: str = "markdown"):
    async with async_session() as db:
        result = await db.execute(
            select(Result).where(
                Result.session_id == session_id,
                Result.format == format,
            )
        )
        r = result.scalar_one_or_none()

    if not r:
        async with async_session() as db2:
            await result_aggregator.aggregate(session_id, db2)
        async with async_session() as db3:
            result = await db3.execute(
                select(Result).where(
                    Result.session_id == session_id,
                    Result.format == format,
                )
            )
            r = result.scalar_one_or_none()

    if not r:
        raise HTTPException(status_code=404, detail="Results not yet available")

    ext = "md" if format == "markdown" else "json"
    suffix = f".{ext}"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    ) as f:
        f.write(r.content)
        tmp_path = f.name

    return FileResponse(
        path=tmp_path,
        filename=f"agentos_{session_id}.{ext}",
        media_type="text/plain" if format == "markdown" else "application/json",
        headers={"Content-Disposition": f'attachment; filename="agentos_{session_id}.{ext}"'},
    )


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str):
    async with async_session() as db:
        for model in (Agent, Message, Result):
            items = await db.execute(
                model.__table__.delete().where(
                    model.__table__.c.session_id == session_id
                )
            )
        result = await db.execute(
            Session.__table__.delete().where(Session.__table__.c.id == session_id)
        )
        await db.commit()
