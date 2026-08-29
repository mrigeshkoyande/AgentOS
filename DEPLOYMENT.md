# 🚀 AgentOS & SPARK — Production Deployment & Scaling Guide

This guide details how to build and run the containerized stack locally, and how to scale the architecture for production platforms like **Vercel** and container clouds.

---

## 📦 1. Local Containerized Stack (Docker Compose)

The repository is equipped with fully configured Dockerfiles and a `docker-compose.yml` to orchestrate both services.

### Prerequisite: Environment Variables
Create a `.env` file at the root of the repository:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Build & Run Commands
From the repository root, run:
```bash
# Build and launch all containers
docker-compose up --build -d

# View status of active services
docker-compose ps

# Monitor execution logs in real-time
docker-compose logs -f
```

### Container Layout & Network Proxies
- **`agentos_backend` (Port 8000)**: Serves the FastAPI REST endpoints and WebSocket channels (`/ws/sessions/`).
- **`agentos_frontend` (Port 80)**: Mounts an **Nginx** server serving the compiled React build and proxies API calls (`/api/`) and WebSockets (`/ws/`) to the backend container over the internal Docker bridge network.
- **SQLite Persistence**: Database state is mapped to `./backend/agentos.db` on the host system to survive container rebuilds.

---

## ⚡ 2. Scaling Architecture for Vercel (Production)

Deploying a multi-agent system with live streaming WebSockets and stateful persistence requires a **Decoupled Monorepo Architecture** to scale efficiently.

```
                              ┌───────────────────────────────────┐
                              │         Global Edge DNS           │
                              └─────────────────┬─────────────────┘
                                                │
                        ┌───────────────────────┴───────────────────────┐
                        ▼                                               ▼
     ┌─────────────────────────────────────┐         ┌─────────────────────────────────────┐
     │      Vercel (Static CDN Edge)       │         │      Container Host (Railway/AWS)    │
     │      - React / Vite SPA Assets      │         │      - FastAPI Async Server         │
     │      - Global Edge Scale (CDN)      │         │      - Persistent WebSocket Pipes   │
     └─────────────────────────────────────┘         └──────────────────┬──────────────────┘
                                                                        │
                                                                        ▼
                                                     ┌─────────────────────────────────────┐
                                                     │      Cloud DB (Postgres / Neon)     │
                                                     │      - Shared Persistent State      │
                                                     └─────────────────────────────────────┘
```

### Why we decouple the layers:
1. **Stateless Functions (Vercel)**: Vercel Serverless Functions have strict timeouts (10s–300s) and are ephemeral. Long-running Multi-Agent DAG runs that take minutes will get cut off mid-execution.
2. **WebSocket Support**: WebSockets require persistent TCP connections. Ephemeral serverless functions cannot keep connection state, causing immediate disconnects.
3. **Database Writes**: SQLite is a file-based database. Scaling to multiple serverless function instances will write to isolated disk environments, losing synchronization.

---

## 🛠️ Step-by-Step Production Setup

### Step 1: Deploy Frontend on Vercel
1. Link the repository root (or the `spark-prototype/` folder) to your **Vercel Console**.
2. Configure **Framework Preset**: `Vite`.
3. Set **Build Command**: `npm run build`
4. Set **Output Directory**: `dist/client`
5. Configure **Environment Variables**:
   - `VITE_API_BASE_URL`: Set this to your deployed Backend URL (e.g., `https://api.yourdomain.com`).
6. Vercel automatically deploys, configures `vercel.json` SPA routing rewrites, and scales the static assets globally on their CDN.

### Step 2: Deploy Backend on Container Hosts (Render, Railway, or AWS)
Deploy the FastAPI backend to a service supporting persistent Python containers (e.g. Render Web Services, Railway Docker Deploy, AWS ECS, or Fly.io).

1. Set the build context to `backend/` using `backend/Dockerfile`.
2. Configure environment variables:
   - `GEMINI_API_KEY`: Google Deepmind API key.
   - `DATABASE_URL`: Connection string for a cloud database.

### Step 3: Database Scale (PostgreSQL Migration)
To support multi-instance horizontal scaling, connect the backend to a hosted PostgreSQL instance (e.g. Neon, Supabase, or AWS RDS).

Modify `get_db` connection helper in `backend/main.py`:
```python
def get_db():
    database_url = os.environ.get("DATABASE_URL")
    if database_url and (database_url.startswith("postgres://") or database_url.startswith("postgresql://")):
        import psycopg2
        conn = psycopg2.connect(database_url)
        return conn
    else:
        # Fallback to local SQLite during development
        import sqlite3
        conn = sqlite3.connect("agentos.db")
        return conn
```
*(Add `psycopg2-binary` to your `requirements.txt` dependencies in the production build).*
