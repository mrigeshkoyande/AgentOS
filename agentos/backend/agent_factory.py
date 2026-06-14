import json
import logging
from datetime import datetime

from .models import Agent
from .database import async_session

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_TEMPLATE = """\
You are {display_name}, a {role} in an AI organization working on: {org_description}
Your task: {task}
Context from colleagues who completed before you:
{dependency_outputs}
COMMUNICATION PROTOCOL (use ONLY when needed):

To ask another agent a question, embed in your response:

QUESTION_TO:[Role Name]
Your specific question here
END_QUESTION

Rules: max 2 questions, be thorough, end with a SUMMARY: section (2-3 sentences of key decisions/outputs)."""


def _assign_layers(agents_data: list[dict]) -> dict[str, int]:
    role_to_layer: dict[str, int] = {}
    role_set = {a["role"] for a in agents_data}

    def get_layer(role: str, visiting: set) -> int:
        if role in role_to_layer:
            return role_to_layer[role]
        if role in visiting:
            return 0  # circular dependency → layer 0
        agent = next((a for a in agents_data if a["role"] == role), None)
        if not agent:
            return 0
        visiting = visiting | {role}
        deps = [d for d in agent.get("depends_on_roles", []) if d in role_set]
        if not deps:
            layer = 0
        else:
            layer = max(get_layer(d, visiting) for d in deps) + 1
        role_to_layer[role] = layer
        return layer

    for a in agents_data:
        get_layer(a["role"], set())

    return role_to_layer


class AgentFactory:
    async def create_agents(
        self, session_id: str, org_data: dict, description: str
    ) -> list[Agent]:
        agents_data = org_data["agents"]
        role_to_layer = _assign_layers(agents_data)

        agents = []
        async with async_session() as db:
            for a in agents_data:
                system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
                    display_name=a["display_name"],
                    role=a["role"],
                    org_description=description,
                    task=a["task"],
                    dependency_outputs="{dependency_outputs}",
                )
                agent = Agent(
                    session_id=session_id,
                    role=a["role"],
                    display_name=a["display_name"],
                    emoji=a.get("emoji", "🤖"),
                    task=a["task"],
                    dependencies=json.dumps(a.get("depends_on_roles", [])),
                    layer=role_to_layer.get(a["role"], 0),
                    system_prompt=system_prompt,
                    created_at=datetime.utcnow(),
                )
                db.add(agent)
                agents.append(agent)

            await db.commit()
            for ag in agents:
                await db.refresh(ag)

        return agents


agent_factory = AgentFactory()
