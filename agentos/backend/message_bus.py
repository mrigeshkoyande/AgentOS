import re
import logging
from datetime import datetime

from .models import Message
from .database import async_session

logger = logging.getLogger(__name__)

_QUESTION_RE = re.compile(
    r"QUESTION_TO:\s*\[(.+?)\]\n(.*?)END_QUESTION", re.DOTALL
)


class MessageBus:
    def parse_questions(self, text: str) -> list[dict]:
        results = []
        for m in _QUESTION_RE.finditer(text):
            results.append({"to_role": m.group(1).strip(), "content": m.group(2).strip()})
        return results

    async def process_output(
        self,
        session_id: str,
        agent,
        output: str,
        all_agents: list,
        ws,
    ) -> str:
        questions = self.parse_questions(output)
        if not questions:
            return output

        role_map = {a.role.lower(): a for a in all_agents}

        async with async_session() as db:
            for q in questions:
                target = role_map.get(q["to_role"].lower())

                if target and target.status == "done" and target.output_summary:
                    answer = target.output_summary
                else:
                    answer = "Agent not available, proceed with best judgment."

                msg = Message(
                    session_id=session_id,
                    from_agent_id=agent.id,
                    to_agent_id=target.id if target else None,
                    type="question",
                    content=q["content"],
                    resolved=bool(target and target.status == "done"),
                )
                db.add(msg)

                await ws.broadcast(
                    session_id,
                    ws.message_sent(agent.role, q["to_role"], "question", q["content"][:200]),
                )

                logger.debug(
                    f"Q from {agent.role} → {q['to_role']}: answered={bool(target and target.status == 'done')}"
                )

            await db.commit()

        return output


message_bus = MessageBus()
