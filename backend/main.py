import os
import re
import json
import uuid
import asyncio
import logging
import requests
import httpx
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentos_backend")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db

# Models for Request Bodies
class SessionCreate(BaseModel):
    description: str

class ModelOverride(BaseModel):
    model: str

# FastAPI Application
app = FastAPI(title="AgentOS Backend", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from websocket_manager import manager

from routes.decisions import router as decisions_router
from routes.tasks import router as tasks_router
from routes.analytics import router as analytics_router

app.include_router(decisions_router)
app.include_router(tasks_router)
app.include_router(analytics_router)

# get_db imported from database module

# Database tables initialization
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'draft',
        user_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # agents
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        role TEXT NOT NULL,
        display_name TEXT,
        model TEXT NOT NULL,
        model_override TEXT,
        system_prompt TEXT,
        task TEXT,
        layer INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        output TEXT,
        cubicle TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    )
    """)
    
    # messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        from_agent TEXT,
        to_agent TEXT,
        type TEXT,
        content TEXT,
        resolved BOOLEAN DEFAULT FALSE,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (from_agent) REFERENCES agents(id) ON DELETE CASCADE,
        FOREIGN KEY (to_agent) REFERENCES agents(id) ON DELETE CASCADE
    )
    """)
    
    # results
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        title TEXT,
        summary TEXT,
        synthesis TEXT,
        metrics TEXT, -- JSON array string
        recommendations TEXT, -- JSON array string
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    )
    """)
    
    # agent_registry
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_registry (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        capabilities TEXT NOT NULL, -- JSON list
        tools TEXT, -- JSON list
        model TEXT,
        cubicle TEXT,
        status TEXT DEFAULT 'IDLE',
        enabled INTEGER DEFAULT 1,
        tasks_completed INTEGER DEFAULT 0,
        tokens_used INTEGER DEFAULT 0,
        execution_time_sum INTEGER DEFAULT 0
    )
    """)
    
    # Pre-populate default office agents
    default_agents = [
        ("agent-s", "Sammo", "Search Specialist", '["research", "search", "lookup", "source", "external", "extract", "evidence", "find"]', '["retrieval", "source scan", "text extraction"]', 'gemini-1.5-flash', 'S'),
        ("agent-p", "Paro", "Creative Strategist", '["marketing", "strategy", "campaign", "brand", "business", "creative", "launch", "growth"]', '["brief synthesis", "positioning", "campaign map"]', 'gemini-1.5-flash', 'P'),
        ("agent-a", "Amo", "Analytics Engineer", '["code", "api", "automation", "debug", "technical", "logic", "build", "backend"]', '["code plan", "debugger", "automation"]', 'gemini-1.5-flash', 'A'),
        ("agent-r", "Repo", "Content Creator", '["write", "caption", "script", "copy", "story", "communication", "post", "email"]', '["copy draft", "tone pass", "storyline"]', 'gemini-1.5-flash', 'R'),
        ("agent-k", "Kmailo", "Data Analyst", '["data", "analysis", "pattern", "summary", "compare", "report", "metrics", "insight"]', '["metrics scan", "pattern model", "report builder"]', 'gemini-1.5-flash', 'K')
    ]
    for agent in default_agents:
        cursor.execute(
            "INSERT OR REPLACE INTO agent_registry (id, name, role, capabilities, tools, model, cubicle) VALUES (?, ?, ?, ?, ?, ?, ?)",
            agent
        )
        
    # Migrate agents table if missing cubicle column
    try:
        cursor.execute("ALTER TABLE agents ADD COLUMN cubicle TEXT;")
    except Exception:
        pass

    conn.commit()
    conn.close()

# Run database setup
init_db()

# --- Health Endpoint ---
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "agentos"
    }

# --- Gemini API Call helper ---
def call_gemini(prompt: str, system_instruction: str = None) -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    contents = [{"parts": [{"text": prompt}]}]
    payload = {"contents": contents}
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
        
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        if res.status_code == 200:
            res_json = res.json()
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            logger.error(f"Gemini API returned status code {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"Gemini API request failed: {e}")
    return None

async def call_gemini_async(prompt: str, system_instruction: str = None) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return ""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, headers=headers, timeout=30.0)
            if res.status_code == 200:
                data = res.json()
                return data['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            logger.error(f"Gemini API async call failed: {e}")
    return ""

async def call_gemini_stream(prompt: str, system_instruction: str = None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:streamGenerateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("POST", url, json=payload, headers=headers, timeout=30.0) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        line_cleaned = line.strip().lstrip("[").rstrip("]").rstrip(",")
                        if not line_cleaned:
                            continue
                        try:
                            data = json.loads(line_cleaned)
                            text = data['candidates'][0]['content']['parts'][0]['text']
                            yield text
                        except Exception:
                            # Try simple regex extraction if json parsing of a line chunk fails
                            match = re.search(r'"text"\s*:\s*"([^"]+)"', line_cleaned)
                            if match:
                                try:
                                    yield match.group(1).encode().decode('unicode-escape')
                                except Exception:
                                    yield match.group(1)
        except Exception as e:
            logger.error(f"Gemini streaming request failed: {e}")

async def call_mock_stream(role: str, task: str, description: str):
    output = get_mock_output(role, task, description)
    words = output.split(" ")
    chunk_size = 3
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])
        if i > 0:
            chunk = " " + chunk
        yield chunk
        await asyncio.sleep(0.04)

class ModelRouter:
    @staticmethod
    async def generate_stream(role: str, task: str, description: str, system_prompt: str, model: str):
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            prompt = f"""
            You are an AI agent part of a multi-agent planning organization. 
            Overall project description: "{description}"
            Your specific role: "{role}"
            Your specific task: "{task}"
            
            Write a concise, extremely detailed professional output (about 300-400 words) satisfying your task in markdown format.
            Use headers, lists, and bold text. Start directly with your analysis.
            If you need to ask another role a question, embed it exactly in this syntax:
            QUESTION_TO:[TargetRole]Your query details here...END_QUESTION
            """
            async for chunk in call_gemini_stream(prompt, system_instruction=system_prompt):
                yield chunk
        else:
            async for chunk in call_mock_stream(role, task, description):
                yield chunk

# --- dynamic role generator ---
def generate_agents_for_description(description: str) -> List[Dict]:
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        prompt = f"""
        Given the following startup/project description:
        "{description}"
        
        Generate exactly 5 specialized AI agent roles needed to execute this project.
        Assign each agent a unique cubicle value ('S', 'P', 'A', 'R', or 'K') and group them into dependency layers:
        - Layer 0: High-level independent strategists (e.g. CEO, CTO, CFO). Set layer to 0.
        - Layer 1: Specialized executioners who depend on Layer 0 strategist outputs (e.g. Lead Developer, Product Manager, Marketing Specialist). Set layer to 1.
        
        Return ONLY a JSON array of exactly 5 objects with the following format:
        [
          {{
            "role": "CEO",
            "display_name": "Sarah Jenkins - Chief Executive Officer",
            "model": "kimi-k2",
            "layer": 0,
            "cubicle": "S",
            "task": "Create the overall strategic business model, identify product market fit, and define execution phases.",
            "system_prompt": "You are the CEO. Your goal is to guide the team strategically..."
          }}
        ]
        Do not add markdown formatting or backticks around the JSON. Return only the JSON.
        """
        response_text = call_gemini(prompt)
        if response_text:
            try:
                cleaned = re.sub(r"^```json\s*|```$", "", response_text.strip(), flags=re.MULTILINE)
                agents = json.loads(cleaned)
                if isinstance(agents, list) and len(agents) > 0:
                    cubicles = ["S", "P", "A", "R", "K"]
                    for idx, a in enumerate(agents):
                        if "cubicle" not in a:
                            a["cubicle"] = cubicles[idx % len(cubicles)]
                        if "layer" not in a:
                            a["layer"] = 0 if idx < 3 else 1
                    logger.info("Successfully generated dynamic agents via Gemini")
                    return agents
            except Exception as e:
                logger.error(f"Failed to parse Gemini generated roles JSON: {e}")
                
    # Fallback dynamic builder
    desc_lower = description.lower()
    logger.info("Using standard fallback dynamic agent builder")
    
    agents = [
        {
            "role": "CEO",
            "display_name": "Sarah Jenkins - Chief Executive Officer",
            "model": "kimi-k2",
            "layer": 0,
            "cubicle": "S",
            "task": "Create the overall strategic business model, identify product market fit, and define execution phases.",
            "system_prompt": "You are the CEO of AgentOS. Your goal is to design the strategy, coordinate sub-agents, and synthesize findings."
        },
        {
            "role": "CTO",
            "display_name": "Alex Chen - Chief Technology Officer",
            "model": "kimi-k2",
            "layer": 0,
            "cubicle": "P",
            "task": "Design the system architecture, select the technology stack, and identify technical scaling challenges.",
            "system_prompt": "You are the CTO. Your goal is to evaluate tech stack, engineering challenges, architecture diagrams, and security protocols."
        },
        {
            "role": "CFO",
            "display_name": "Marcus Vance - Chief Financial Officer",
            "model": "gpt-4o",
            "layer": 0,
            "cubicle": "A",
            "task": "Develop the financial model, estimate MVP development budget, and define the pricing strategy.",
            "system_prompt": "You are the CFO. Your goal is to draft budget breakdowns, pricing plans (freemium/premium), and revenue metrics."
        }
    ]
    
    if any(keyword in desc_lower for keyword in ["marketing", "sales", "brand", "agency"]):
        agents.extend([
            {
                "role": "Marketing Specialist",
                "display_name": "Julian Ross - Marketing Director",
                "model": "gemini-1.5-pro",
                "layer": 1,
                "cubicle": "R",
                "task": "Design the launch strategy, select digital marketing channels, and estimate client acquisition costs.",
                "system_prompt": "You are the Marketing Specialist. Your goal is to create advertising channels, landing page hooks, and growth tactics."
            },
            {
                "role": "Creative Director",
                "display_name": "Chloe Mercer - Creative Director",
                "model": "gemini-1.5-pro",
                "layer": 1,
                "cubicle": "K",
                "task": "Define the brand identity, logo concepts, and content theme parameters for the campaign.",
                "system_prompt": "You are the Creative Director. Design aesthetic values, UI layouts, colors, and key messaging."
            }
        ])
    elif any(keyword in desc_lower for keyword in ["legal", "compliance", "regulation", "health", "fintech"]):
        agents.extend([
            {
                "role": "Legal & Compliance",
                "display_name": "Elena Rostova - Legal Counsel",
                "model": "gpt-4o",
                "layer": 1,
                "cubicle": "R",
                "task": "Identify compliance standards (HIPAA, GDPR, etc.), outline security guidelines, and draft key policy highlights.",
                "system_prompt": "You are the Legal & Compliance Specialist. Advise on regulations, licensing, liability, and safety requirements."
            },
            {
                "role": "Product Manager",
                "display_name": "Liam Vance - Product Manager",
                "model": "gemini-1.5-pro",
                "layer": 1,
                "cubicle": "K",
                "task": "Draft detailed user stories, itemize core features for the MVP, and build a product roadmap.",
                "system_prompt": "You are the Product Manager. Your goal is to outline spec documents, prioritization matrices, and sprint milestones."
            }
        ])
    else:
        agents.extend([
            {
                "role": "Product Manager",
                "display_name": "Elena Rostova - Product Manager",
                "model": "gemini-1.5-pro",
                "layer": 1,
                "cubicle": "R",
                "task": "Define user personas, core MVP feature specification list, and write a release timeline.",
                "system_prompt": "You are the Product Manager. Create feature prioritization lists, client user flows, and release milestones."
            },
            {
                "role": "Lead Developer",
                "display_name": "David Kim - Lead Developer",
                "model": "llama-3.1-70b",
                "layer": 1,
                "cubicle": "K",
                "task": "Draft developer instructions, configure DB schema guidelines, and provide git folder structure specs.",
                "system_prompt": "You are the Lead Developer. Provide file structures, sample SQL schemas, API call guidelines, and code snippets."
            }
        ])
        
    return agents

# --- Mock Response generator for simulation ---
def get_mock_output(role: str, task: str, description: str, context: str = "") -> str:
    desc_clean = description.replace("Build a complete business plan and organization for: ", "").strip()
    
    if "ceo" in role.lower():
        return f"""### Executive Strategic Report: {desc_clean}
**Prepared by Sarah Jenkins, CEO**

#### 1. Strategic Vision
Our project focuses on addressing a critical gap in the market: {desc_clean}. Our strategic vision is to simplify user interactions, streamline execution, and create a sustainable, scalable business model.

#### 2. Target Market and Customer Profiles
- **Primary Audience:** Professionals and early-adopters seeking efficiency improvements.
- **Secondary Audience:** Enterprise teams needing custom integrations and collaborative frameworks.

#### 3. Core Business Model & Revenue Streams
1. **SaaS Subscription Model:** Flat-rate billing of $29/user/month for mid-market, $99/user/month for Enterprise.
2. **Usage-Based Pricing:** Tiered pricing for high-volume transactions.
3. **Professional Services:** High-margin training and custom onboarding workshops.

#### 4. Phased Implementation Roadmap
- **Phase 1 (Month 1-3):** MVP Launch and Closed Beta testing with 50 select design partners.
- **Phase 2 (Month 4-6):** Product stabilization, performance enhancements, and initial marketing push.
- **Phase 3 (Month 7+):** Multi-channel scaling, tool integrations, and automation layers.
"""
    elif "cto" in role.lower():
        return f"""### Technical Architecture Design: {desc_clean}
**Prepared by Alex Chen, CTO**

#### 1. Recommended Technology Stack
- **Frontend:** HTML5, TailwindCSS, React.js, and WebSockets for real-time state synchronization.
- **Backend:** FastAPI (Python 3.12+) using asynchronous event loops and Uvicorn.
- **Database:** PostgreSQL for persistent records, Redis for caching session states.
- **Deployment:** Docker containers, hosted on AWS Elastic Container Service (ECS) with RDS.

#### 2. High-Level System Architecture
- Client UI communicates with API Gateway via HTTPS (REST RESTful APIs) and WebSockets.
- Background tasks are delegated to Celery worker pools using RabbitMQ.

#### 3. Scaling & Security Implementation
- **HIPAA/GDPR Compliance:** Encryption of sensitive parameters at rest (AES-256) and in transit (TLS 1.3).
- **Concurrency:** Non-blocking asynchronous handlers to prevent connection bottle-necks.
"""
    elif "cfo" in role.lower():
        return f"""### Financial & Cost Projections: {desc_clean}
**Prepared by Marcus Vance, CFO**

#### 1. Financial Projection Highlights
- **Estimated Launch Budget:** $50,000 for Q1 (infrastructure and setup).
- **Customer Acquisition Cost (CAC):** Target $15 per customer through organic content and inbound funnels.
- **Lifetime Value (LTV):** Estimated at $348 (average retention of 12 months at $29/month).

#### 2. Cost Analysis & Pricing Tiers
- **Infrastructure Cost:** $150/month base (AWS Fargate, RDS, Route53, and domain hosting).
- **Subscription Tiers:**
  - *Starter:* $19/month (up to 3 projects, basic integrations).
  - *Professional:* $49/month (unlimited projects, advanced modules).
  - *Enterprise:* Custom pricing (Dedicated host, Single Sign-On, SLA guarantees).
"""
    elif "product manager" in role.lower() or "pm" in role.lower():
        return f"""### Product Specification Document: {desc_clean}
**Prepared by Elena Rostova, PM**

#### 1. Core Feature Specification for MVP
1. **Interactive Prompt Composer:** Clean user interface with character limits and smart suggestion chips.
2. **Real-time Live Feed:** Immediate updates showing sub-agent activity and inter-agent dialogues.
3. **Structured Export:** Multi-format download (JSON, Markdown) for instant saving of results.
4. **Session Loader:** Ability to load and resume past executions with a session ID token.
"""
    elif "developer" in role.lower() or "dev" in role.lower():
        return f"""### Codebase Blueprint & Implementation Details: {desc_clean}
**Prepared by David Kim, Lead Developer**

#### 1. Git Repository Folder Structure
```
workspace/
├── frontend/
│   ├── css/
│   │   └── main.css
│   ├── js/
│   │   ├── api.js
│   │   └── orgChart.js
│   └── index.html
└── backend/
    ├── main.py
    └── requirements.txt
```

#### 2. SQLite Database DDL Schema
```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'draft'
);
```
"""
    elif "marketing" in role.lower() or "mktg" in role.lower():
        return f"""### Marketing Strategy and Campaign Plan: {desc_clean}
**Prepared by Julian Ross, Marketing Director**

#### 1. Launch Marketing Strategy
- **Product Hunt Campaign:** Goal is to reach Top 5 Product of the Day.
- **Social Launch:** Short video threads on X/Twitter and LinkedIn showcasing the live token stream.
- **Content Marketing:** In-depth blog posts analyzing "How AgentOS automates startup launches in 5 minutes".
"""
    elif "legal" in role.lower() or "compliance" in role.lower():
        return f"""### Legal & Regulatory Review: {desc_clean}
**Prepared by Elena Rostova, Legal Counsel**

#### 1. Regulatory Guidelines
- **GDPR (Europe):** Data deletion protocols (Right to be Forgotten) and cookie consent banners.
- **HIPAA (USA - if Healthcare):** Business Associate Agreements (BAA) with server hosts and database encryption.
- **Terms of Service (ToS):** Disclaimers regarding AI limitations and generated content accuracy.
"""
    else:
        return f"""### Operational Report: {role}
**Prepared for: {desc_clean}**

#### 1. Domain Analysis & Tasks
We have carefully analyzed the context of `{desc_clean}` and implemented steps to satisfy the assigned task: `{task}`.

#### 2. Key Accomplishments
- Created structured criteria for operational reviews.
- Outlined execution obstacles and resolved data conflicts.
"""

# --- REST API Endpoints ---

# List Sessions
@app.get("/api/sessions")
def list_sessions():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sessions

@app.post("/api/sessions")
def create_session(payload: SessionCreate):
    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    conn = get_db()
    try:
        cursor = conn.cursor()
        
        # Insert session
        cursor.execute(
            "INSERT INTO sessions (id, description, status) VALUES (?, ?, ?)",
            (session_id, payload.description, "draft")
        )
        
        # Generate agents
        agents_data = generate_agents_for_description(payload.description)
        agents_list = []
        
        cubicles = ['S', 'P', 'A', 'R', 'K']
        for idx, a in enumerate(agents_data):
            agent_id = f"agent_{uuid.uuid4().hex[:10]}"
            cubicle = a.get("cubicle", cubicles[idx % len(cubicles)])
            cursor.execute(
                """INSERT INTO agents 
                   (id, session_id, role, display_name, model, system_prompt, task, layer, status, cubicle) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    agent_id,
                    session_id,
                    a["role"],
                    a.get("display_name", a["role"]),
                    a["model"],
                    a.get("system_prompt", ""),
                    a.get("task", ""),
                    a.get("layer", 0),
                    "pending",
                    cubicle
                )
            )
            agents_list.append({
                "agent_id": agent_id,
                "role": a["role"],
                "display_name": a.get("display_name", a["role"]),
                "model": a["model"],
                "layer": a.get("layer", 0),
                "status": "pending",
                "task": a.get("task", ""),
                "cubicle": cubicle
            })
            
        conn.commit()
        return {
            "session_id": session_id,
            "status": "draft",
            "agents": agents_list
        }
    finally:
        conn.close()


# Get Session Details
@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    session_row = cursor.fetchone()
    if not session_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = dict(session_row)
    
    # Load agents
    cursor.execute("SELECT * FROM agents WHERE session_id = ?", (session_id,))
    agent_rows = cursor.fetchall()
    
    agents = []
    for row in agent_rows:
        a = dict(row)
        a["agent_id"] = a["id"]
        agents.append(a)
        
    session["agents"] = agents
    conn.close()
    return session

# Override Agent Model
@app.patch("/api/agents/{agent_id}/model")
def override_model(agent_id: str, payload: ModelOverride):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
    agent = cursor.fetchone()
    if not agent:
        cursor.execute("SELECT * FROM agents WHERE id LIKE ? OR role LIKE ?", (f"%{agent_id}%", f"%{agent_id}%"))
        agent = cursor.fetchone()
        
    if agent:
        real_id = agent["id"]
        cursor.execute(
            "UPDATE agents SET model = ?, model_override = ? WHERE id = ?",
            (payload.model, payload.model, real_id)
        )
    else:
        cursor.execute(
            "INSERT OR REPLACE INTO agents (id, session_id, role, model, model_override, system_prompt, status) "
            "VALUES (?, 'spark_default_session', ?, ?, ?, '', 'IDLE')",
            (agent_id, f"Specialist {agent_id.upper()}", payload.model, payload.model)
        )
    conn.commit()
    conn.close()
    return {"status": "success", "agent_id": agent_id, "model": payload.model}

# Get Results
@app.get("/api/sessions/{session_id}/results")
def get_results(session_id: str):
    conn = get_db()
    cursor = conn.cursor()
    
    # check session
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    session = cursor.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Check if results already computed
    cursor.execute("SELECT * FROM results WHERE session_id = ?", (session_id,))
    result_row = cursor.fetchone()
    
    if result_row:
        res = dict(result_row)
        res["metrics"] = json.loads(res["metrics"])
        res["recommendations"] = json.loads(res["recommendations"])
        
        # load agents output
        cursor.execute("SELECT * FROM agents WHERE session_id = ?", (session_id,))
        agents = []
        for r in cursor.fetchall():
            a = dict(r)
            a["agent_id"] = a["id"]
            agents.append(a)
        res["agents"] = agents
        
        conn.close()
        return res
        
    # If not computed, let's create dynamic results based on agent outputs
    cursor.execute("SELECT * FROM agents WHERE session_id = ?", (session_id,))
    agents_rows = cursor.fetchall()
    
    agents = []
    reports_context = ""
    for r in agents_rows:
        a = dict(r)
        a["agent_id"] = a["id"]
        agents.append(a)
        reports_context += f"### {a['role']} Blueprint Report:\n{a['output'] or 'No report generated.'}\n\n"
            
    summary_text = "Analysis is complete. All agents have collaborated to form the structural outline."
    synthesis_text = "Synthesis: The strategic foundation matches the technology stack and product milestones."
    
    # Call Gemini for dynamic final synthesis if API key is present
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key and reports_context:
        synthesis_prompt = f"""
        Act as a Chief of Staff. You have received the following reports from the AI Organization regarding the project description: "{session['description']}"
        
        {reports_context}
        
        Synthesize these findings into a single, cohesive, extremely detailed corporate execution plan.
        Use headers, bullet points, and clean markdown.
        """
        try:
            res_text = call_gemini(synthesis_prompt)
            if res_text:
                synthesis_text = res_text.strip()
                summary_text = synthesis_text[:300] + "..."
        except Exception as e:
            logger.error(f"Failed to generate real synthesis: {e}")
            
    # Build clean metrics
    metrics = [
        {"value": "$50k", "label": "Estimated Q1 Budget"},
        {"value": str(len(agents)), "label": "AI Agents Deployed"},
        {"value": "100%", "label": "Success Rate"}
    ]
    
    recommendations = [
        "Review HIPAA and GDPR compliance requirements immediately.",
        "Establish secure sandbox environments for beta API integrations.",
        "Adopt a phased roll-out plan beginning with key design partners."
    ]
    
    # Insert results
    result_id = f"res_{uuid.uuid4().hex[:10]}"
    cursor.execute(
        """INSERT INTO results (id, session_id, title, summary, synthesis, metrics, recommendations)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            result_id,
            session_id,
            f"AgentOS Blueprint - {session['description'][:40]}",
            summary_text,
            synthesis_text,
            json.dumps(metrics),
            json.dumps(recommendations)
        )
    )
    
    conn.commit()
    conn.close()
    
    return {
        "title": f"AgentOS Blueprint - {session['description'][:40]}",
        "session_id": session_id,
        "summary": summary_text,
        "synthesis": synthesis_text,
        "metrics": metrics,
        "recommendations": recommendations,
        "agents": agents
    }

# Export Results
@app.get("/api/sessions/{session_id}/export")
def export_results(session_id: str, format: str = "json"):
    results_data = get_results(session_id)
    
    if format == "json":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=results_data,
            headers={"Content-Disposition": f"attachment; filename=agentos-{session_id}.json"}
        )
        
    # Markdown format
    md_content = f"""# {results_data['title']}

## Executive Summary
{results_data['summary']}

## Final Synthesis
{results_data['synthesis']}

## Metrics
"""
    for m in results_data['metrics']:
        md_content += f"- **{m['label']}:** {m['value']}\n"
        
    md_content += "\n## Agent Contributions\n"
    for a in results_data['agents']:
        md_content += f"\n### {a['display_name']} ({a['role']})\n"
        md_content += f"**Model Used:** {a['model']}\n\n"
        md_content += f"{a['output'] or 'No output generated.'}\n"
        md_content += "\n---\n"
        
    md_content += "\n## Recommendations\n"
    for r in results_data['recommendations']:
        md_content += f"- {r}\n"
        
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        md_content,
        headers={"Content-Disposition": f"attachment; filename=agentos-{session_id}.md"}
    )

# Delete Session
@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "session_id": session_id}

# Run Session DAG in Background
@app.post("/api/sessions/{session_id}/run")
async def run_session(session_id: str):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check session
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    session = cursor.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Prevent duplicate runs
    if session["status"] == "running":
        conn.close()
        raise HTTPException(status_code=409, detail="Session is already running")
        
    # Set running
    cursor.execute("UPDATE sessions SET status = 'running' WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    
    # Trigger background task
    asyncio.create_task(execute_dag(session_id, session["description"]))
    return {"status": "running"}

# --- DAG Async Execution Engine ---
async def execute_dag(session_id: str, description: str):
    logger.info(f"Starting DAG execution for session: {session_id}")
    await asyncio.sleep(1) # delay to allow websocket connections to settle
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agents WHERE session_id = ? ORDER BY layer ASC", (session_id,))
    agent_rows = cursor.fetchall()
    conn.close()
    
    if not agent_rows:
        logger.warning(f"No agents found for session {session_id}")
        return
        
    # Group agents by layers
    layers: Dict[int, List[Dict]] = {}
    for r in agent_rows:
        a = dict(r)
        a["agent_id"] = a["id"]
        layer_num = a.get("layer", 0)
        if layer_num not in layers:
            layers[layer_num] = []
        layers[layer_num].append(a)
        
    # Execute layer by layer
    for layer_idx in sorted(layers.keys()):
        layer_agents = layers[layer_idx]
        
        # Broadcast layer start
        await manager.broadcast(session_id, {
            "event": "layer_start",
            "layer": layer_idx,
            "agents": [a["role"] for a in layer_agents]
        })
        
        # Execute agents in parallel
        tasks = [execute_single_agent(session_id, agent, description) for agent in layer_agents]
        await asyncio.gather(*tasks)
        
    # Mark Session Complete
    conn = get_db()
    conn.execute("UPDATE sessions SET status = 'completed' WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    
    # Broadcast session completion
    await manager.broadcast(session_id, {
        "event": "session_done",
        "session_id": session_id
    })
    logger.info(f"DAG execution completed successfully for session: {session_id}")

# --- Execute Single Agent ---
async def execute_single_agent(session_id: str, agent: dict, description: str):
    agent_id = agent["agent_id"]
    role = agent["role"]
    task = agent["task"]
    sys_prompt = agent["system_prompt"]
    model = agent["model"]
    
    logger.info(f"Agent {role} started execution.")
    
    # Mark agent running
    conn = get_db()
    conn.execute("UPDATE agents SET status = 'running' WHERE id = ?", (agent_id,))
    conn.commit()
    conn.close()
    
    # Broadcast started
    await manager.broadcast(session_id, {
        "event": "agent_started",
        "agent_id": agent_id
    })
    
    # Retrieve messages/context for this agent
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM messages WHERE session_id = ? AND (from_agent = ? OR to_agent = ?)",
        (session_id, agent_id, agent_id)
    )
    context_msgs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    context_str = ""
    if context_msgs:
        context_str = "\n".join([f"{m['from_agent']} -> {m['to_agent']}: {m['content']}" for m in context_msgs])
        
    # Stream the output token by token
    agent_output = ""
    async for chunk in ModelRouter.generate_stream(role, task, description, sys_prompt, model):
        agent_output += chunk
        await manager.broadcast(session_id, {
            "event": "agent_token",
            "agent_id": agent_id,
            "token": chunk
        })
        
    # Intercept QUESTION_TO to resolve inter-agent dependencies
    agent_output = await check_and_route_messages(session_id, agent, agent_output, description)
        
    # Mark agent done
    conn = get_db()
    conn.execute(
        "UPDATE agents SET status = 'done', output = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (agent_output, agent_id)
    )
    conn.commit()
    conn.close()
    
    # Broadcast agent done
    await manager.broadcast(session_id, {
        "event": "agent_done",
        "agent_id": agent_id,
        "output_summary": agent_output[:120] + "..."
    })
    logger.info(f"Agent {role} execution done.")

# --- Inter-Agent Message Routing ---
async def check_and_route_messages(session_id: str, sender_agent: dict, text: str, description: str):
    match = re.search(r'QUESTION_TO:\[([^\]]+)\](.*?)END_QUESTION', text, re.DOTALL)
    if not match:
        return text
    
    target_role = match.group(1).strip()
    question_text = match.group(2).strip()
    
    # Find target agent in database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agents WHERE session_id = ? AND role = ?", (session_id, target_role))
    target_row = cursor.fetchone()
    conn.close()
    
    if not target_row:
        return text
    
    target_agent = dict(target_row)
    target_agent["agent_id"] = target_agent["id"]
    
    # Put sender into waiting
    conn = get_db()
    conn.execute("UPDATE agents SET status = 'waiting' WHERE id = ?", (sender_agent["agent_id"],))
    conn.commit()
    conn.close()
    
    # Broadcast message_sent question
    q_id = f"msg_{uuid.uuid4().hex[:10]}"
    q_content = f"QUESTION_TO:[{target_role}] {question_text}"
    
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (id, session_id, from_agent, to_agent, type, content) VALUES (?, ?, ?, ?, ?, ?)",
        (q_id, session_id, sender_agent["agent_id"], target_agent["agent_id"], "question", q_content)
    )
    conn.commit()
    conn.close()
    
    await manager.broadcast(session_id, {
        "event": "message_sent",
        "id": q_id,
        "session_id": session_id,
        "from_agent": sender_agent["agent_id"],
        "to_agent": target_agent["agent_id"],
        "type": "question",
        "content": q_content,
        "timestamp": datetime.now().isoformat()
    })
    
    # Generate answer from target agent by executing it
    conn = get_db()
    conn.execute("UPDATE agents SET status = 'running' WHERE id = ?", (target_agent["agent_id"],))
    conn.commit()
    conn.close()
    await manager.broadcast(session_id, {
        "event": "agent_started",
        "agent_id": target_agent["agent_id"]
    })
    
    answer_text = ""
    async for chunk in ModelRouter.generate_stream(target_role, f"Answer question: {question_text}", description, target_agent.get("system_prompt", ""), target_agent.get("model", "gemini-1.5-flash")):
        answer_text += chunk
        await manager.broadcast(session_id, {
            "event": "agent_token",
            "agent_id": target_agent["agent_id"],
            "token": chunk
        })
        
    # Mark target agent done
    conn = get_db()
    conn.execute("UPDATE agents SET status = 'done', output = ? WHERE id = ?", (answer_text, target_agent["agent_id"]))
    conn.commit()
    conn.close()
    await manager.broadcast(session_id, {
        "event": "agent_done",
        "agent_id": target_agent["agent_id"],
        "output_summary": answer_text[:120] + "..."
    })
    
    # Broadcast message_sent answer
    a_id = f"msg_{uuid.uuid4().hex[:10]}"
    
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (id, session_id, from_agent, to_agent, type, content) VALUES (?, ?, ?, ?, ?, ?)",
        (a_id, session_id, target_agent["agent_id"], sender_agent["agent_id"], "answer", answer_text)
    )
    conn.commit()
    conn.close()
    
    await manager.broadcast(session_id, {
        "event": "message_sent",
        "id": a_id,
        "session_id": session_id,
        "from_agent": target_agent["agent_id"],
        "to_agent": sender_agent["agent_id"],
        "type": "answer",
        "content": answer_text,
        "timestamp": datetime.now().isoformat()
    })
    
    # Resume sender agent
    conn = get_db()
    conn.execute("UPDATE agents SET status = 'running' WHERE id = ?", (sender_agent["agent_id"],))
    conn.commit()
    conn.close()
    
    return text + f"\n\n**Response received from {target_role}:**\n{answer_text}"

# --- WebSocket Event Route ---
@app.websocket("/ws/sessions/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"WS received data from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
    except Exception as e:
        logger.error(f"WS error: {e}")
        manager.disconnect(session_id, websocket)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run("main:app", host=host, port=port, reload=False)

