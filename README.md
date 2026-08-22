# ⚡ AgentOS — AI Organization Operating System

> Deploy a collaborative AI organization from plain text in under 5 minutes — no code required.

AgentOS transforms your business vision or project description into an executing AI workforce. By describing your company, product, or goal in natural language, AgentOS automatically generates a directed acyclic graph (DAG) hierarchy of specialized AI agents (e.g., CEO, CTO, Product Manager, Lead Developer, Marketing Director, Legal Counsel) that collaborate in real-time via a structured message bus to deliver comprehensive business blueprints.

Unlike complex agent frameworks requiring massive engineering overhead, AgentOS provides a lightweight, zero-dependency vanilla JS frontend and a clean FastAPI backend with built-in SQLite persistence and multi-model capability.

---

## ✨ Core Features

- **Dynamic Role Inference**: Analyzes startup/project descriptions via Gemini to automatically construct 4-6 custom agent roles, tailored tasks, system instructions, and layered structures.
- **Parallel Asyncio DAG Execution**: Groups agents into dependency layers (e.g., Layer 0 Strategists, Layer 1 Execution Specialists) and executes them concurrently using Python's `asyncio.gather`.
- **Inter-Agent Message Bus**: Supports structured `QUESTION_TO:[Role]` and `ANSWER_TO:[Role]` protocols embedded directly in agent execution loops to simulate collaborative consensus.
- **Real-Time Token Streaming**: Streams agent outputs character-by-character over WebSockets to provide instant visibility into ongoing reasoning processes.
- **Interactive SVG Org Chart**: A dynamic frontend visualization representing active agent lifecycles (Pending, Running, Waiting, Done, Error) through real-time state changes.
- **Comprehensive Session Persistence**: Restores, reviews, and overrides models for past execution histories via SQLite storage.

---

## 🏗️ System Architecture

```mermaid
graph TD;
    Browser[Frontend (Vanilla HTML/CSS/JS)] <-- REST API --> API[FastAPI Backend]
    Browser <-- WebSocket --> WS[WebSocket Manager]
    API --> Engine[DAG Execution Engine]
    Engine --> LLM[Multi-LLM Router (Gemini, Kimi K2, GPT-4o, Llama 3.1)]
    Engine <--> DB[(SQLite Database)]
    API <--> DB
```

### Technical Stack & File Directory
- **Backend**: FastAPI, SQLite3, Uvicorn, Requests, Asyncio.
- **Frontend**: Vanilla HTML5, CSS3 (curated dark mode theme), Vanilla ES6 JavaScript (zero external framework dependencies).
- **Directory Layout**:
  - [`backend/main.py`](file:///Users/rishabhshevde/My%20Projects/AgentOS/backend/main.py): Monolithic backend service housing API endpoints, SQLite helpers, model routing logic, the mock generator, and the DAG async engine.
  - [`frontend/index.html`](file:///Users/rishabhshevde/My%20Projects/AgentOS/frontend/index.html): Input interface for submitting project goals and listing existing sessions.
  - [`frontend/session.html`](file:///Users/rishabhshevde/My%20Projects/AgentOS/frontend/session.html): The primary execution cockpit featuring the WebSocket activity feed, agent detail panels, and SVG org tree.
  - [`frontend/results.html`](file:///Users/rishabhshevde/My%20Projects/AgentOS/frontend/results.html): Detailed compilation viewer with export actions.
  - [`frontend/js/`](file:///Users/rishabhshevde/My%20Projects/AgentOS/frontend/js/): Modular frontend drivers (`api.js`, `ws.js`, `orgChart.js`, `agentPanel.js`, `nav.js`).
  - [`frontend/css/main.css`](file:///Users/rishabhshevde/My%20Projects/AgentOS/frontend/css/main.css): Modern glassmorphism dark-theme stylesheets.

---

## 💾 Database Schema (SQLite)

AgentOS maintains full persistence in `backend/agentos.db` across four main tables:

### 1. `sessions`
Tracks overall run-states and descriptions.
- `id` (TEXT PRIMARY KEY): Unique identifier (prefixed with `sess_`).
- `description` (TEXT): The natural language prompt provided by the user.
- `status` (TEXT): Current state (`draft`, `running`, `completed`, `paused`, `error`).
- `user_id` (TEXT): Optional foreign identifier.
- `created_at` (TEXT): Timestamp.
- `updated_at` (TEXT): Timestamp.

### 2. `agents`
Tracks individual role instructions, assigned models, execution statuses, and generated results.
- `id` (TEXT PRIMARY KEY): Prefix `agent_`.
- `session_id` (TEXT): References `sessions(id)`.
- `role` (TEXT): e.g., `CEO`, `CTO`, `Lead Developer`.
- `display_name` (TEXT): Human-readable label.
- `model` (TEXT): Model identifier (e.g., `kimi-k2`, `gpt-4o`, `gemini-1.5-pro`).
- `model_override` (TEXT): Custom override model if chosen by user.
- `system_prompt` (TEXT): Specific system instructions generated for this agent.
- `task` (TEXT): Dedicated objective.
- `layer` (INTEGER): DAG depth order (e.g., `0` for strategists, `1` for executors).
- `status` (TEXT): State (`pending`, `running`, `waiting`, `done`, `error`).
- `output` (TEXT): Final Markdown report output from the LLM.
- `created_at` (TEXT): Timestamp.
- `completed_at` (TEXT): Timestamp.

### 3. `messages`
Tracks inter-agent communication logs.
- `id` (TEXT PRIMARY KEY): Prefix `msg_`.
- `session_id` (TEXT): References `sessions(id)`.
- `from_agent` (TEXT): Sender agent ID.
- `to_agent` (TEXT): Receiver agent ID.
- `type` (TEXT): `'question'` or `'answer'`.
- `content` (TEXT): Communication payload (e.g., `QUESTION_TO:[CEO]...`).
- `resolved` (BOOLEAN): Status of dialogue resolution.
- `timestamp` (TEXT): Timestamp.

### 4. `results`
Holds the final consolidated business blueprint.
- `id` (TEXT PRIMARY KEY): Prefix `res_`.
- `session_id` (TEXT): References `sessions(id)`.
- `title` (TEXT): Display name for the result.
- `summary` (TEXT): High-level description.
- `synthesis` (TEXT): Unified consolidation of all outputs.
- `metrics` (TEXT): JSON array of calculated value metrics (e.g., budget, team sizes).
- `recommendations` (TEXT): JSON array of actionable highlights.
- `created_at` (TEXT): Timestamp.

---

## 🔌 API & WebSocket Reference

### REST Endpoints

#### 1. List Sessions
- **URL**: `GET /api/sessions`
- **Response**: Array of session records.

#### 2. Create Session
- **URL**: `POST /api/sessions`
- **Request Body**:
  ```json
  {
    "description": "A HIPAA-compliant telemedicine platform for rural clinics."
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "session_id": "sess_f4d96a7b",
    "status": "draft",
    "agents": [
      { "agent_id": "agent_8e29bc11", "role": "CEO", "model": "kimi-k2", "layer": 0, "status": "pending", "task": "..." },
      { "agent_id": "agent_3df91a5e", "role": "CTO", "model": "kimi-k2", "layer": 0, "status": "pending", "task": "..." },
      { "agent_id": "agent_b8364c7e", "role": "Legal & Compliance", "model": "gpt-4o", "layer": 1, "status": "pending", "task": "..." }
    ]
  }
  ```

#### 3. Get Session Details
- **URL**: `GET /api/sessions/{session_id}`
- **Response**: Full session object containing basic metadata and a nested array of `agents`.

#### 4. Override Agent Model
- **URL**: `PATCH /api/agents/{agent_id}/model`
- **Request Body**:
  ```json
  {
    "model": "gpt-4o"
  }
  ```
- **Response**: `{"status": "success", "agent_id": "...", "model": "gpt-4o"}`

#### 5. Run Session DAG
- **URL**: `POST /api/sessions/{session_id}/run`
- **Response**: `{"status": "running"}`. Triggers async task executing layers sequentially.

#### 6. Fetch Results
- **URL**: `GET /api/sessions/{session_id}/results`
- **Response**: Combined result synthesis, metrics, recommendations, and agent outputs.

#### 7. Export Blueprint
- **URL**: `GET /api/sessions/{session_id}/export?format=json` or `?format=markdown`
- **Response**: Downloads raw JSON structure or returns a formatted PlainText download payload.

#### 8. Delete Session
- **URL**: `DELETE /api/sessions/{session_id}`
- **Response**: `{"status": "success", "session_id": "..."}`

---

### WebSocket Connection

- **URL**: `/ws/sessions/{session_id}`
- **Events Broadcasted by Server**:
  - `{"event": "layer_start", "layer": 0, "agents": ["CEO", "CTO"]}`
  - `{"event": "agent_started", "agent_id": "agent_xxx"}`
  - `{"event": "agent_token", "agent_id": "agent_xxx", "token": "..."}` (streams words)
  - `{"event": "message_sent", "id": "...", "from_agent": "...", "to_agent": "...", "type": "question", "content": "..."}`
  - `{"event": "agent_done", "agent_id": "agent_xxx", "output_summary": "..."}`
  - `{"event": "session_done", "session_id": "sess_xxx"}`

---

## 🚀 Step-by-Step Installation & Running

### Prerequisites
- Python 3.11+
- SQLite3 (usually bundled with Python)
- Google AI Studio Gemini API Key (optional but recommended for dynamic runs; falls back to simulated answers if missing).

### Backend Setup
1. Clone the project and navigate to the project directory:
   ```bash
   git clone https://github.com/mrigeshkoyande/AgentOS.git
   cd AgentOS
   ```
2. Create and configure your environment variables:
   ```bash
   echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
   ```
3. Initialize the Python virtual environment:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the FastAPI development server:
   ```bash
   python3 main.py
   ```
   The backend will initialize the database at `backend/agentos.db` and start listening on `http://localhost:8000`.

### Frontend Setup
In a new terminal window, serve the frontend assets using Python's built-in HTTP server:
```bash
cd AgentOS
python3 -m http.server 3000 --directory frontend
```
Open your browser and navigate to `http://localhost:3000` to interact with AgentOS.

---

## 🧠 Execution Engine Mechanics

```
   [User Description]
           │
           ▼
┌───────────────────────┐
│  Global Orchestrator  │ ────► dynamic role mapping (Gemini / Fallback)
└───────────────────────┘
           │
           ▼
┌───────────────────────┐
│     SQLite DB Seed    │ ────► inserts session, layers & pending agents
└───────────────────────┘
           │
           ▼
 ┌─────────────────────┐
 │    Layer 0 Run      │ ────► parallel execute (e.g. CEO + CTO + CFO)
 └─────────────────────┘
           │
           ├─► QUESTION_TO / ANSWER_TO dialogue injection between agents
           ▼
 ┌─────────────────────┐
 │    Layer 1 Run      │ ────► parallel execute (e.g. PM + Dev Lead)
 └─────────────────────┘
           │
           ▼
┌───────────────────────┐
│    Final Synthesis    │ ────► consolidates outputs into a final blueprint
└───────────────────────┘
```

1. **Orchestrator Parsing**: Prompt sent to Gemini to infer roles. E.g., for "Fintech", it outputs JSON configuring CEO, CTO, CFO, Legal, and Product Manager across layers.
2. **DAG Evaluation**: Backend queries agents grouped by `layer` (ascending sequence).
3. **Parallel LLM Processing**: For each layer, it spawns `execute_single_agent` tasks in parallel. If `GEMINI_API_KEY` is present, it prompts Gemini using the system instructions, overall goal, and previous context. Otherwise, it triggers the simulated mock content engine.
4. **Token Streaming**: Output is split into small fragments and sent via WebSockets to feed the frontend typing indicators in real-time.
5. **Consolidated Results**: The orchestrator combines outputs into recommendations and metrics, ready for download.

---

## 🔮 Upcoming Integration: Antygravity GraphRAG Memory System

AgentOS is built with extension points to support the **Antygravity GraphRAG Memory System**, enabling execution agents (e.g. Lead Developers) to interact directly with million-line codebases:
- **Structural Code Analysis (Neo4j)**: Maps file-to-file imports, class hierarchies, and function calls.
- **Semantic Code Vectors (Qdrant)**: Embeds logical code units (methods/classes parsed with Tree-sitter) for vector similarity searches.
- **Hierarchical Code Summaries**: Resolves token context limitations by abstracting code structures at the function, file, folder, and repository level.

*For deep architectural details, see [`agent.md`](file:///Users/rishabhshevde/My%20Projects/AgentOS/agent.md) and [`design.md`](file:///Users/rishabhshevde/My%20Projects/AgentOS/design.md).*

---

<small>Last updated: August 22, 2026 • Designed for Hackathon Deployment</small>