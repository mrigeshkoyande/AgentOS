import os
import re
import json
import uuid
import sqlite3
import asyncio
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentos_backend")

# Database File Path
DB_FILE = os.path.join(os.path.dirname(__file__), "agentos.db")

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
    allow_origins=["*"],  # Allows all origins
    allow_credentials=False,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WebSocket connected for session: {session_id}")

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected for session: {session_id}")

    async def broadcast(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending ws message: {e}")

manager = ConnectionManager()

# Helper to get DB connection
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

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
        resolved BOOLEAN DEFAULT 0,
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
    
    conn.commit()
    conn.close()

# Run database setup
init_db()

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

# --- dynamic role generator ---
def generate_agents_for_description(description: str) -> List[Dict]:
    # Try dynamic role generation with Gemini first
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        prompt = f"""
        Given the following startup/project description:
        "{description}"
        
        Generate a list of 4-6 AI agent roles needed to execute this project.
        Group them into dependency layers:
        - Layer 0: High-level independent strategists (e.g. CEO, CTO, CFO).
        - Layer 1: Specialized executioners who depend on Layer 0 strategist outputs (e.g. Lead Developer, Product Manager, Marketing Specialist).
        
        Return ONLY a JSON array of objects with the following format:
        [
          {{
            "role": "CEO",
            "display_name": "Sarah Jenkins - Chief Executive Officer",
            "model": "kimi-k2",
            "layer": 0,
            "task": "Create the overall strategic business model, identify product market fit, and define execution phases.",
            "system_prompt": "You are the CEO. Your goal is to guide the team strategically..."
          }}
        ]
        Do not add markdown formatting or backticks around the JSON. Return only the JSON.
        """
        response_text = call_gemini(prompt)
        if response_text:
            try:
                # Strip backticks if the model added them
                cleaned = re.sub(r"^```json\s*|```$", "", response_text.strip(), flags=re.MULTILINE)
                agents = json.loads(cleaned)
                if isinstance(agents, list) and len(agents) > 0:
                    logger.info("Successfully generated dynamic agents via Gemini")
                    return agents
            except Exception as e:
                logger.error(f"Failed to parse Gemini generated roles JSON: {e}")
                
    # Fallback/Mock dynamic builder
    desc_lower = description.lower()
    logger.info("Using standard fallback dynamic agent builder")
    
    # Base Strategists (Layer 0)
    agents = [
        {
            "role": "CEO",
            "display_name": "Sarah Jenkins - Chief Executive Officer",
            "model": "kimi-k2",
            "layer": 0,
            "task": "Create the overall strategic business model, identify product market fit, and define execution phases.",
            "system_prompt": "You are the CEO of AgentOS. Your goal is to design the strategy, coordinate sub-agents, and synthesize findings."
        },
        {
            "role": "CTO",
            "display_name": "Alex Chen - Chief Technology Officer",
            "model": "kimi-k2",
            "layer": 0,
            "task": "Design the system architecture, select the technology stack, and identify technical scaling challenges.",
            "system_prompt": "You are the CTO. Your goal is to evaluate tech stack, engineering challenges, architecture diagrams, and security protocols."
        },
        {
            "role": "CFO",
            "display_name": "Marcus Vance - Chief Financial Officer",
            "model": "gpt-4o",
            "layer": 0,
            "task": "Develop the financial model, estimate MVP development budget, and define the pricing strategy.",
            "system_prompt": "You are the CFO. Your goal is to draft budget breakdowns, pricing plans (freemium/premium), and revenue metrics."
        }
    ]
    
    # Layer 1 based on description content
    if any(keyword in desc_lower for keyword in ["marketing", "sales", "brand", "agency"]):
        agents.extend([
            {
                "role": "Marketing Specialist",
                "display_name": "Julian Ross - Marketing Director",
                "model": "gemini-1.5-pro",
                "layer": 1,
                "task": "Design the launch strategy, select digital marketing channels, and estimate client acquisition costs.",
                "system_prompt": "You are the Marketing Specialist. Your goal is to create advertising channels, landing page hooks, and growth tactics."
            },
            {
                "role": "Creative Director",
                "display_name": "Chloe Mercer - Creative Director",
                "model": "gemini-1.5-pro",
                "layer": 1,
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
                "task": "Identify compliance standards (HIPAA, GDPR, etc.), outline security guidelines, and draft key policy highlights.",
                "system_prompt": "You are the Legal & Compliance Specialist. Advise on regulations, licensing, liability, and safety requirements."
            },
            {
                "role": "Product Manager",
                "display_name": "Liam Vance - Product Manager",
                "model": "gemini-1.5-pro",
                "layer": 1,
                "task": "Draft detailed user stories, itemize core features for the MVP, and build a product roadmap.",
                "system_prompt": "You are the Product Manager. Your goal is to outline spec documents, prioritization matrices, and sprint milestones."
            }
        ])
    else:
        # Default Developer & Product Manager roles
        agents.extend([
            {
                "role": "Product Manager",
                "display_name": "Elena Rostova - Product Manager",
                "model": "gemini-1.5-pro",
                "layer": 1,
                "task": "Define user personas, core MVP feature specification list, and write a release timeline.",
                "system_prompt": "You are the Product Manager. Create feature prioritization lists, client user flows, and release milestones."
            },
            {
                "role": "Lead Developer",
                "display_name": "David Kim - Lead Developer",
                "model": "llama-3.1-70b",
                "layer": 1,
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
2. **Usage-Based Pricing:** Tiered pricing for high-volume transactions, ensuring aligned incentives.
3. **Professional Services:** High-margin training and custom onboarding workshops for enterprise accounts.

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
- Secure token-based OAuth2 authentication handles session isolation.

#### 3. Scaling & Security Implementation
- **HIPAA/GDPR Compliance:** Encryption of sensitive parameters at rest (AES-256) and in transit (TLS 1.3).
- **Concurrency:** Non-blocking asynchronous handlers to prevent connection bottle-necks.
- **Database Backups:** Automatic daily snapshots with multi-region redundancy.
"""
    elif "cfo" in role.lower():
        return f"""### Financial & Cost Projections: {desc_clean}
**Prepared by Marcus Vance, CFO**

#### 1. Financial Projection Highlights
- **Estimated Launch Budget:** $50,000 for Q1 (covering infrastructure, initial design, and legal setup).
- **Customer Acquisition Cost (CAC):** Target $15 per customer through organic content and inbound funnels.
- **Lifetime Value (LTV):** Estimated at $348 (average retention of 12 months at $29/month).

#### 2. Cost Analysis & Pricing Tiers
- **Infrastructure Cost:** $150/month base (AWS Fargate, RDS, Route53, and domain hosting).
- **Subscription Tiers:**
  - *Starter:* $19/month (up to 3 projects, basic integrations).
  - *Professional:* $49/month (unlimited projects, advanced modules).
  - *Enterprise:* Custom pricing (Dedicated host, Single Sign-On, SLA guarantees).

#### 3. Break-Even Analysis
Assuming a monthly burn rate of $5,000 (including server fees and marketing), the venture will achieve break-even status upon acquiring 103 active Professional tier subscribers.
"""
    elif "product manager" in role.lower() or "pm" in role.lower():
        return f"""### Product Specification Document: {desc_clean}
**Prepared by Elena Rostova, PM**

#### 1. Core Feature Specification for MVP
1. **Interactive Prompt Composer:** Clean user interface with character limits and smart suggestion chips.
2. **Real-time Live Feed:** Immediate updates showing sub-agent activity and inter-agent dialogues.
3. **Structured Export:** Multi-format download (JSON, Markdown) for instant saving of results.
4. **Session Loader:** Ability to load and resume past executions with a session ID token.

#### 2. User Persona Profiles
- **User A (The Busy Strategist):** Needs quick, actionable insights without typing complex commands.
- **User B (The Dev Lead):** Wants detailed structural guides, database schemas, and codebase blueprints.

#### 3. Release Roadmap
- **Milestone 1:** High-fidelity wireframe and static frontend components validation.
- **Milestone 2:** Event bus integration and WebSocket token stream testing.
- **Milestone 3 (Public launch):** Stable MVP release with download functionality.
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
│   │   ├── ws.js
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
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    role TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    output TEXT
);
```

#### 3. API Route Handler Example
```python
@app.get("/api/sessions/{{session_id}}")
async def get_session(session_id: str):
    conn = get_db()
    session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return dict(session)
```
"""
    elif "marketing" in role.lower() or "mktg" in role.lower():
        return f"""### Marketing Strategy and Campaign Plan: {desc_clean}
**Prepared by Julian Ross, Marketing Director**

#### 1. Launch Marketing Strategy
- **Product Hunt Campaign:** Goal is to reach Top 5 Product of the Day.
- **Social Launch:** Short video threads on X/Twitter and LinkedIn showcasing the live token stream.
- **Content Marketing:** In-depth blog posts analyzing "How AgentOS automates startup launches in 5 minutes".

#### 2. Key Advertising & Outbound Channels
1. **LinkedIn Organic & Paid:** Targeted towards Product Managers, Founders, and Technical leads.
2. **Founder Communities:** Pitching in Slack/Discord channels, Indie Hackers, and Hackernews.
3. **Developer Newsletters:** Sponsor newsletters like TL;DR and JavaScript Weekly.

#### 3. Expected Metrics
- **Sign-ups (Week 1):** Target 500 free sign-ups.
- **Conversion Rate:** Aim for 3-5% conversion from Free Trial to Starter/Professional.
- **Viral Coefficient:** Focus on encouraging share link utilization on results page.
"""
    elif "legal" in role.lower() or "compliance" in role.lower():
        return f"""### Legal & Regulatory Review: {desc_clean}
**Prepared by Elena Rostova, Legal Counsel**

#### 1. Regulatory Guidelines
Given the scope of "{desc_clean}", the product must align with key compliance guidelines:
- **GDPR (Europe):** Data deletion protocols (Right to be Forgotten) and cookie consent banners.
- **HIPAA (USA - if Healthcare):** Business Associate Agreements (BAA) with server hosts and database encryption.
- **Terms of Service (ToS):** Disclaimers regarding AI limitations and generated content accuracy.

#### 2. Licensing Requirements
- Software components utilize MIT or Apache 2.0 open-source licenses to avoid copyleft issues.
- Third-party API usage (like Gemini/OpenAI) must comply with their developer terms of service.

#### 3. Liability Mitigation
- Implement standard terms disclaiming liability for direct, indirect, or incidental damages.
- Clearly state that AgentOS outputs are recommendations and must be verified by certified professionals.
"""
    else:
        return f"""### Operational Report: {role}
**Prepared for: {desc_clean}**

#### 1. Domain Analysis & Tasks
We have carefully analyzed the context of `{desc_clean}` and implemented steps to satisfy the assigned task: `{task}`.

#### 2. Key Accomplishments
- Created structured criteria for operational reviews.
- Outlined execution obstacles and resolved data conflicts.
- Proposed key performance indicators (KPIs) to track ongoing progress.

#### 3. Collaboration Summary
{context or "Exchanged parameters with strategist agents to align priorities."}
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

# Create Session
@app.post("/api/sessions")
def create_session(payload: SessionCreate):
    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    conn = get_db()
    cursor = conn.cursor()
    
    # Insert session
    cursor.execute(
        "INSERT INTO sessions (id, description, status) VALUES (?, ?, ?)",
        (session_id, payload.description, "draft")
    )
    
    # Generate agents
    agents_data = generate_agents_for_description(payload.description)
    agents_list = []
    
    for a in agents_data:
        agent_id = f"agent_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            """INSERT INTO agents 
               (id, session_id, role, display_name, model, system_prompt, task, layer, status) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                agent_id,
                session_id,
                a["role"],
                a.get("display_name", a["role"]),
                a["model"],
                a.get("system_prompt", ""),
                a.get("task", ""),
                a.get("layer", 0),
                "pending"
            )
        )
        agents_list.append({
            "agent_id": agent_id,
            "role": a["role"],
            "display_name": a.get("display_name", a["role"]),
            "model": a["model"],
            "layer": a.get("layer", 0),
            "status": "pending",
            "task": a.get("task", "")
        })
        
    conn.commit()
    conn.close()
    
    return {
        "session_id": session_id,
        "status": "draft",
        "agents": agents_list
    }

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
        # map db name 'id' to api name 'agent_id'
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
        conn.close()
        raise HTTPException(status_code=404, detail="Agent not found")
        
    cursor.execute(
        "UPDATE agents SET model = ?, model_override = ? WHERE id = ?",
        (payload.model, payload.model, agent_id)
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
    ceo_output = ""
    for r in agents_rows:
        a = dict(r)
        a["agent_id"] = a["id"]
        agents.append(a)
        if a["role"] == "CEO":
            ceo_output = a["output"] or ""
            
    summary_text = "Analysis is complete. All agents have collaborated to form the structural outline."
    synthesis_text = "Synthesis: The strategic foundation matches the technology stack and product milestones."
    
    if ceo_output:
        # Extract from CEO output if possible
        summary_text = ceo_output[:250] + "..."
        synthesis_text = ceo_output
        
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
        # Return JSON direct download header
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
        
        # Insert Layer communications/message sequences
        if layer_idx == 0:
            # Let CTO ask CEO a question, and CEO answer
            ceo = next((a for a in layer_agents if a["role"] == "CEO"), None)
            cto = next((a for a in layer_agents if a["role"] == "CTO"), None)
            
            if ceo and cto:
                await asyncio.sleep(1)
                
                # Question
                q_id = f"msg_{uuid.uuid4().hex[:10]}"
                q_content = "QUESTION_TO:[CEO] What is our target timeline for MVP launch and expected validation milestones?"
                conn = get_db()
                conn.execute(
                    "INSERT INTO messages (id, session_id, from_agent, to_agent, type, content) VALUES (?, ?, ?, ?, ?, ?)",
                    (q_id, session_id, cto["agent_id"], ceo["agent_id"], "question", q_content)
                )
                conn.commit()
                conn.close()
                
                await manager.broadcast(session_id, {
                    "event": "message_sent",
                    "id": q_id,
                    "session_id": session_id,
                    "from_agent": cto["agent_id"],
                    "to_agent": ceo["agent_id"],
                    "type": "question",
                    "content": q_content,
                    "timestamp": datetime.now().isoformat()
                })
                
                await asyncio.sleep(2)
                
                # Answer
                a_id = f"msg_{uuid.uuid4().hex[:10]}"
                a_content = "ANSWER_TO:[CTO] We are targeting a Q3 launch. Milestone 1 is static prototype validation, Milestone 2 is WebSocket pipeline streaming integration, and Milestone 3 is full public beta."
                conn = get_db()
                conn.execute(
                    "INSERT INTO messages (id, session_id, from_agent, to_agent, type, content) VALUES (?, ?, ?, ?, ?, ?)",
                    (a_id, session_id, ceo["agent_id"], cto["agent_id"], "answer", a_content)
                )
                conn.commit()
                conn.close()
                
                await manager.broadcast(session_id, {
                    "event": "message_sent",
                    "id": a_id,
                    "session_id": session_id,
                    "from_agent": ceo["agent_id"],
                    "to_agent": cto["agent_id"],
                    "type": "answer",
                    "content": a_content,
                    "timestamp": datetime.now().isoformat()
                })
                await asyncio.sleep(1)
                
        elif layer_idx == 1:
            # Let PM ask CTO a question, and CTO answer
            pm = next((a for a in layer_agents if "product" in a["role"].lower() or "pm" in a["role"].lower()), None)
            
            # Find CTO from database since he was in Layer 0
            conn = get_db()
            cto_row = conn.execute("SELECT * FROM agents WHERE session_id = ? AND role = 'CTO'", (session_id,)).fetchone()
            conn.close()
            
            if pm and cto_row:
                cto_id = cto_row["id"]
                await asyncio.sleep(1)
                
                # Question
                q_id = f"msg_{uuid.uuid4().hex[:10]}"
                q_content = "QUESTION_TO:[CTO] What security standards and compliance frameworks should we build into our core communication pipelines?"
                conn = get_db()
                conn.execute(
                    "INSERT INTO messages (id, session_id, from_agent, to_agent, type, content) VALUES (?, ?, ?, ?, ?, ?)",
                    (q_id, session_id, pm["agent_id"], cto_id, "question", q_content)
                )
                conn.commit()
                conn.close()
                
                await manager.broadcast(session_id, {
                    "event": "message_sent",
                    "id": q_id,
                    "session_id": session_id,
                    "from_agent": pm["agent_id"],
                    "to_agent": cto_id,
                    "type": "question",
                    "content": q_content,
                    "timestamp": datetime.now().isoformat()
                })
                
                await asyncio.sleep(2)
                
                # Answer
                a_id = f"msg_{uuid.uuid4().hex[:10]}"
                a_content = "ANSWER_TO:[PM] We should implement AES-256 encryption at rest and TLS 1.3 in transit. For communication pipelines, secure WebSockets with JWT token authentication will satisfy our safety profiles."
                conn = get_db()
                conn.execute(
                    "INSERT INTO messages (id, session_id, from_agent, to_agent, type, content) VALUES (?, ?, ?, ?, ?, ?)",
                    (a_id, session_id, cto_id, pm["agent_id"], "answer", a_content)
                )
                conn.commit()
                conn.close()
                
                await manager.broadcast(session_id, {
                    "event": "message_sent",
                    "id": a_id,
                    "session_id": session_id,
                    "from_agent": cto_id,
                    "to_agent": pm["agent_id"],
                    "type": "answer",
                    "content": a_content,
                    "timestamp": datetime.now().isoformat()
                })
                await asyncio.sleep(1)
                
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
        
    # Determine output content (Real Gemini API call vs dynamic simulated text)
    api_key = os.environ.get("GEMINI_API_KEY")
    agent_output = ""
    
    if api_key:
        prompt = f"""
        You are part of an AI startup planning suite. 
        Overall project description: "{description}"
        Your specific role: "{role}"
        Your specific task: "{task}"
        
        Previous collaboration context:
        {context_str}
        
        Write a concise, extremely detailed professional output (about 300-400 words) satisfying your task in markdown format. 
        Start immediately with your analysis. Use headers, lists, and bold text. Do not output conversational preamble.
        """
        response_text = call_gemini(prompt, system_instruction=sys_prompt)
        if response_text:
            agent_output = response_text.strip()
            
    if not agent_output:
        # Generate simulation template output
        agent_output = get_mock_output(role, task, description, context_str)
        
    # Stream the output token by token (or chunk of words)
    # We split into words to stream rapidly
    words = agent_output.split(" ")
    chunk_size = 3
    
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])
        if i > 0:
            chunk = " " + chunk
        await manager.broadcast(session_id, {
            "event": "agent_token",
            "agent_id": agent_id,
            "token": chunk
        })
        # sleep slightly to simulate typing speed
        await asyncio.sleep(0.06)
        
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

# --- WebSocket Event Route ---
@app.websocket("/ws/sessions/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            # Just keep the WebSocket connection alive by reading message
            data = await websocket.receive_text()
            logger.info(f"WS received data from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
    except Exception as e:
        logger.error(f"WS error: {e}")
        manager.disconnect(session_id, websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
