import json
import logging
from datetime import datetime, timezone

from fastapi import WebSocket

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WebSocketManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, session_id: str):
        await ws.accept()
        self.active.setdefault(session_id, []).append(ws)

    def disconnect(self, ws: WebSocket, session_id: str):
        conns = self.active.get(session_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, session_id: str, event: dict):
        event.setdefault("timestamp", _now())
        dead = []
        for ws in self.active.get(session_id, []):
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, session_id)

    # ── Event builders ──────────────────────────────────────────────────────

    def agent_created(self, agent) -> dict:
        return {
            "type": "agent_created",
            "agent_id": agent.id,
            "role": agent.role,
            "display_name": agent.display_name,
            "emoji": agent.emoji,
            "layer": agent.layer,
            "status": agent.status,
            "timestamp": _now(),
        }

    def agent_started(self, agent_id: str, role: str) -> dict:
        return {
            "type": "agent_started",
            "agent_id": agent_id,
            "role": role,
            "timestamp": _now(),
        }

    def agent_token(self, agent_id: str, token: str) -> dict:
        return {"type": "agent_token", "agent_id": agent_id, "token": token, "timestamp": _now()}

    def agent_done(self, agent_id: str, role: str, summary: str, tokens: int) -> dict:
        return {
            "type": "agent_done",
            "agent_id": agent_id,
            "role": role,
            "summary": summary,
            "tokens": tokens,
            "timestamp": _now(),
        }

    def agent_error(self, agent_id: str, role: str, error: str) -> dict:
        return {
            "type": "agent_error",
            "agent_id": agent_id,
            "role": role,
            "error": error,
            "timestamp": _now(),
        }

    def message_sent(self, from_role: str, to_role: str, msg_type: str, content: str) -> dict:
        return {
            "type": "message_sent",
            "from_role": from_role,
            "to_role": to_role,
            "msg_type": msg_type,
            "content": content,
            "timestamp": _now(),
        }

    def layer_started(self, layer_num: int, roles: list[str]) -> dict:
        return {
            "type": "layer_started",
            "layer": layer_num,
            "roles": roles,
            "timestamp": _now(),
        }

    def layer_done(self, layer_num: int) -> dict:
        return {"type": "layer_done", "layer": layer_num, "timestamp": _now()}

    def session_done(self, session_id: str, elapsed: float) -> dict:
        return {
            "type": "session_done",
            "session_id": session_id,
            "elapsed": round(elapsed, 1),
            "timestamp": _now(),
        }


ws_manager = WebSocketManager()
