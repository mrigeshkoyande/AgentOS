import json
import logging
from datetime import datetime

from sqlalchemy import select

from .database import async_session
from .models import Agent, Message, Result, Session

logger = logging.getLogger(__name__)


class ResultAggregator:
    async def aggregate(self, session_id: str, db=None) -> Result | None:
        use_own_db = db is None
        if use_own_db:
            db_ctx = async_session()
            db = await db_ctx.__aenter__()
        try:
            return await self._do_aggregate(session_id, db)
        finally:
            if use_own_db:
                await db_ctx.__aexit__(None, None, None)

    async def _do_aggregate(self, session_id: str, db) -> Result | None:
        existing = await db.execute(
            select(Result).where(
                Result.session_id == session_id,
                Result.format == "markdown",
            )
        )
        if existing.scalar_one_or_none():
            return None

        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            return None

        agents_result = await db.execute(
            select(Agent)
            .where(Agent.session_id == session_id)
            .order_by(Agent.layer, Agent.created_at)
        )
        agents = agents_result.scalars().all()

        msgs_result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp)
        )
        messages = msgs_result.scalars().all()

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        title = session.title or "AgentOS Report"

        md_lines = [
            f"# {title}",
            f"**AgentOS Report** | {now}",
            "",
            "## Executive Summary",
            "",
            session.description,
            "",
            "## Agent Reports",
            "",
        ]

        agent_dicts = []
        for ag in agents:
            md_lines += [
                f"### {ag.emoji} {ag.display_name}",
                f"**Role:** {ag.role} | **Model:** {ag.model} | **Layer:** {ag.layer}",
                "",
                f"**Task:** {ag.task}",
                "",
                ag.output or "_No output_",
                "",
                "---",
                "",
            ]
            agent_dicts.append(
                {
                    "id": ag.id,
                    "role": ag.role,
                    "display_name": ag.display_name,
                    "emoji": ag.emoji,
                    "model": ag.model,
                    "layer": ag.layer,
                    "status": ag.status,
                    "task": ag.task,
                    "output": ag.output,
                    "tokens_used": ag.tokens_used,
                }
            )

        if messages:
            md_lines += ["## Inter-Agent Messages", ""]
            for msg in messages:
                from_id = msg.from_agent_id or "system"
                to_id = msg.to_agent_id or "broadcast"
                content_preview = (msg.content or "")[:200]
                md_lines.append(f"- **{from_id} → {to_id}** ({msg.type}): {content_preview}")
            md_lines.append("")

        markdown_content = "\n".join(md_lines)

        json_content = json.dumps(
            {
                "session_id": session_id,
                "title": title,
                "generated_at": now,
                "description": session.description,
                "agents": agent_dicts,
                "messages": [
                    {
                        "id": m.id,
                        "from_agent_id": m.from_agent_id,
                        "to_agent_id": m.to_agent_id,
                        "type": m.type,
                        "content": m.content,
                        "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    }
                    for m in messages
                ],
            },
            indent=2,
        )

        md_result = Result(
            session_id=session_id,
            format="markdown",
            content=markdown_content,
            created_at=datetime.utcnow(),
        )
        json_result = Result(
            session_id=session_id,
            format="json",
            content=json_content,
            created_at=datetime.utcnow(),
        )
        db.add(md_result)
        db.add(json_result)
        await db.commit()

        logger.info(f"Results aggregated for session {session_id}")
        return md_result


result_aggregator = ResultAggregator()
