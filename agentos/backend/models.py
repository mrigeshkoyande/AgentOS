from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index
)
from .database import Base


def _sess_id():
    return "sess_" + uuid4().hex[:8]


def _agt_id():
    return "agt_" + uuid4().hex[:8]


def _msg_id():
    return "msg_" + uuid4().hex[:8]


def _res_id():
    return "res_" + uuid4().hex[:8]


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_sess_id)
    description = Column(Text, nullable=False)
    title = Column(String, nullable=True)
    status = Column(String, default="draft")
    total_agents = Column(Integer, default=0)
    completed_agents = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=_agt_id)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    emoji = Column(String, default="🤖")
    model = Column(String, default="kimi-k2")
    model_override = Column(String, nullable=True)
    system_prompt = Column(Text, nullable=True)
    task = Column(Text, nullable=True)
    dependencies = Column(Text, default="[]")
    layer = Column(Integer, default=0)
    status = Column(String, default="pending")
    output = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=_msg_id)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    from_agent_id = Column(String, nullable=True)
    to_agent_id = Column(String, nullable=True)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Result(Base):
    __tablename__ = "results"

    id = Column(String, primary_key=True, default=_res_id)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    format = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


Index("ix_agents_session_id", Agent.session_id)
Index("ix_agents_status", Agent.status)
Index("ix_messages_session_id", Message.session_id)
