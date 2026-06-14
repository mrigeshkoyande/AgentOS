import json
import logging

from .ai.kimi_client import kimi

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are the Global Orchestrator for AgentOS. Analyze the user's goal and design an optimal team of 4-8 specialized AI agents to accomplish it.
For each agent specify:

role: job title (e.g. "CEO", "CTO", "Frontend Developer")
display_name: "First Name — Role" (give a realistic name)
emoji: single relevant emoji
task: specific 2-3 sentence task for this agent
depends_on_roles: list of role names this agent needs output from (empty if independent)

Respond ONLY with valid JSON, no markdown fences, no explanation:

{
  "title": "short title for this organization",
  "summary": "2 sentence summary",
  "agents": [
    {
      "role": "CEO",
      "display_name": "Sarah Chen — CEO",
      "emoji": "👩‍💼",
      "task": "...",
      "depends_on_roles": []
    }
  ]
}"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
    if text.endswith("```"):
        text = text[: text.rfind("```")]
    return text.strip()


def _validate(data: dict):
    assert "title" in data, "missing title"
    assert "summary" in data, "missing summary"
    assert "agents" in data and isinstance(data["agents"], list), "missing agents list"
    for a in data["agents"]:
        for key in ("role", "display_name", "emoji", "task", "depends_on_roles"):
            assert key in a, f"agent missing field: {key}"


class GlobalOrchestrator:
    async def analyze(self, description: str) -> dict:
        raw = await kimi.generate(_SYSTEM_PROMPT, description)
        logger.debug(f"Orchestrator raw response (first 500): {raw[:500]}")

        for attempt in range(2):
            try:
                cleaned = _strip_fences(raw)
                data = json.loads(cleaned)
                _validate(data)
                return data
            except (json.JSONDecodeError, AssertionError) as e:
                if attempt == 0:
                    logger.warning(f"JSON parse failed ({e}), retrying orchestrator...")
                    raw = await kimi.generate(_SYSTEM_PROMPT, description)
                else:
                    logger.error(f"Orchestrator failed twice. Raw: {raw[:1000]}")
                    raise ValueError(f"Orchestrator could not produce valid JSON: {e}") from e

        raise RuntimeError("Orchestrator analysis failed")


orchestrator = GlobalOrchestrator()
