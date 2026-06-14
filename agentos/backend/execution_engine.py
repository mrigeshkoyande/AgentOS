import asyncio
import json
import logging
import time
from datetime import datetime

from sqlalchemy import select, update

from .ai.kimi_client import kimi
from .database import async_session
from .message_bus import message_bus
from .models import Agent, Session

logger = logging.getLogger(__name__)


class ExecutionEngine:
    def __init__(self):
        self._cancel_flags: dict[str, bool] = {}

    async def execute_session(self, session_id: str, agents: list[Agent], ws):
        self._cancel_flags[session_id] = False
        start_time = time.time()

        layers: dict[int, list[Agent]] = {}
        for a in agents:
            layers.setdefault(a.layer, []).append(a)

        try:
            for layer_num in sorted(layers.keys()):
                if self._cancel_flags.get(session_id):
                    break

                layer_agents = layers[layer_num]
                await ws.broadcast(
                    session_id,
                    ws.layer_started(layer_num, [a.role for a in layer_agents]),
                )

                await asyncio.gather(
                    *[
                        self.execute_agent(a, session_id, agents, ws)
                        for a in layer_agents
                    ],
                    return_exceptions=True,
                )

                await ws.broadcast(session_id, ws.layer_done(layer_num))

            async with async_session() as db:
                status = "paused" if self._cancel_flags.get(session_id) else "completed"
                await db.execute(
                    update(Session)
                    .where(Session.id == session_id)
                    .values(status=status, updated_at=datetime.utcnow())
                )
                await db.commit()

            elapsed = time.time() - start_time
            await ws.broadcast(session_id, ws.session_done(session_id, elapsed))

            # Trigger result aggregation
            if not self._cancel_flags.get(session_id):
                from .result_aggregator import result_aggregator
                async with async_session() as db:
                    await result_aggregator.aggregate(session_id, db)

        except Exception as e:
            logger.error(f"execute_session error for {session_id}: {e}", exc_info=True)
        finally:
            self._cancel_flags.pop(session_id, None)

    async def execute_agent(
        self, agent: Agent, session_id: str, all_agents: list[Agent], ws
    ):
        try:
            async with async_session() as db:
                await db.execute(
                    update(Agent)
                    .where(Agent.id == agent.id)
                    .values(status="running")
                )
                await db.commit()

            await ws.broadcast(session_id, ws.agent_started(agent.id, agent.role))

            dep_context = await self._build_dep_context(agent, all_agents)

            system_prompt = agent.system_prompt.replace(
                "{dependency_outputs}", dep_context
            )
            user_prompt = (
                f"Please complete your assigned task now. {agent.task}\n\n"
                f"Provide thorough, actionable output. End with a SUMMARY: section."
            )

            output_parts = []
            async for token in kimi.stream_generate(system_prompt, user_prompt):
                output_parts.append(token)
                await ws.broadcast(session_id, ws.agent_token(agent.id, token))

            full_output = "".join(output_parts)

            await message_bus.process_output(
                session_id, agent, full_output, all_agents, ws
            )

            summary = full_output[:300]
            tokens_used = len(full_output) // 4

            async with async_session() as db:
                await db.execute(
                    update(Agent)
                    .where(Agent.id == agent.id)
                    .values(
                        status="done",
                        output=full_output,
                        output_summary=summary,
                        tokens_used=tokens_used,
                        completed_at=datetime.utcnow(),
                    )
                )
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session = result.scalar_one_or_none()
                if session:
                    await db.execute(
                        update(Session)
                        .where(Session.id == session_id)
                        .values(
                            completed_agents=Session.completed_agents + 1,
                            updated_at=datetime.utcnow(),
                        )
                    )
                await db.commit()

            agent.status = "done"
            agent.output = full_output
            agent.output_summary = summary

            await ws.broadcast(
                session_id, ws.agent_done(agent.id, agent.role, summary, tokens_used)
            )

        except Exception as e:
            logger.error(f"execute_agent error for {agent.id} ({agent.role}): {e}", exc_info=True)
            async with async_session() as db:
                await db.execute(
                    update(Agent)
                    .where(Agent.id == agent.id)
                    .values(status="error")
                )
                await db.commit()
            agent.status = "error"
            await ws.broadcast(session_id, ws.agent_error(agent.id, agent.role, str(e)))

    async def _build_dep_context(self, agent: Agent, all_agents: list[Agent]) -> str:
        try:
            deps = json.loads(agent.dependencies or "[]")
        except json.JSONDecodeError:
            deps = []

        if not deps:
            return "No dependencies — you are working independently."

        parts = []
        for dep_role in deps:
            dep_agent = next(
                (a for a in all_agents if a.role.lower() == dep_role.lower()), None
            )
            if dep_agent and dep_agent.output_summary:
                parts.append(
                    f"**{dep_agent.display_name} ({dep_agent.role})**:\n{dep_agent.output_summary}"
                )
            elif dep_agent:
                async with async_session() as db:
                    result = await db.execute(
                        select(Agent).where(Agent.id == dep_agent.id)
                    )
                    fresh = result.scalar_one_or_none()
                    if fresh and fresh.output_summary:
                        parts.append(
                            f"**{fresh.display_name} ({fresh.role})**:\n{fresh.output_summary}"
                        )
                        dep_agent.output_summary = fresh.output_summary

        return "\n\n".join(parts) if parts else "Dependencies not yet available."

    def cancel(self, session_id: str):
        self._cancel_flags[session_id] = True


execution_engine = ExecutionEngine()
