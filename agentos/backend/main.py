import asyncio
import logging

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import create_tables
from .api.sessions import router as sessions_router
from .api.agents import router as agents_router
from .ws_manager import ws_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AgentOS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await create_tables()
    logger.info("AgentOS API started — tables created")


app.include_router(sessions_router)
app.include_router(agents_router)


@app.websocket("/ws/sessions/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(websocket, session_id)

    ping_task = asyncio.create_task(_ping_loop(websocket))

    try:
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        ping_task.cancel()
        ws_manager.disconnect(websocket, session_id)


async def _ping_loop(websocket: WebSocket):
    try:
        while True:
            await asyncio.sleep(25)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break
    except asyncio.CancelledError:
        pass


@app.get("/health")
async def health():
    return {"status": "ok", "nim_configured": bool(settings.nvidia_nim_key)}


@app.get("/")
async def root():
    return {"message": "AgentOS API running", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
