import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import os

try:
    from websocket_manager import manager
except ImportError:
    try:
        from backend.websocket_manager import manager
    except ImportError:
        manager = None

try:
    from main import call_gemini
except ImportError:
    try:
        from backend.main import call_gemini
    except ImportError:
        call_gemini = None

from repositories.decision_repository import DecisionRepository
from services.orchestration.task_classifier import TaskClassifier
from services.orchestration.agent_router import AgentRouter

logger = logging.getLogger("dispatch_service")

# Coordinator Waypoints for office cubicles (0-100% coordinates matching frontend isometric layout)
CUBICLE_COORDINATES = {
    "S": [[27, 92], [30, 86], [65.2, 86], [65.2, 74], [65.2, 62], [39.0, 52], [39.0, 36]],
    "P": [[38, 92], [42, 86], [65.2, 86], [65.2, 74], [65.2, 62], [55.0, 52], [55.0, 36]],
    "A": [[50, 92], [54, 86], [65.2, 86], [65.2, 74], [65.2, 62], [68.5, 52], [68.5, 36]],
    "R": [[62, 92], [63, 86], [65.2, 86], [65.2, 74], [65.2, 62], [81.8, 52], [81.8, 36]],
    "K": [[73, 92], [72, 86], [65.2, 86], [65.2, 74], [65.2, 62], [93.8, 52], [93.8, 36]],
    "M": [[38, 92], [42, 86], [65.2, 86], [65.2, 74], [65.2, 62], [55.0, 52], [55.0, 36]]
}

# Static/simulated agent specialist mock responses if Gemini API is missing
MOCK_RESPONSES = {
    "agent-m": """### Marketing Strategy & Creative Campaign
*   **Target Audience Analysis**: Focus on early-adopter professionals and tech-savvy enterprise managers seeking process automation.
*   **Branding & Core Position**: SPARK is positioned as "The Living AI Virtual Workspace" offering frictionless workflow orchestration.
*   **Launch Action Items**:
    1. Product Hunt launch targeting Top 3 Product of the Day.
    2. Interactive Twitter/X video threads showing the live walking visualizers.
    3. Multi-channel developer news blast using sponsorship programs.""",
    
    "agent-p": """### Creative Strategy & Growth Positioning
*   **Market Positioning**: SPARK transforms discrete asynchronous agent workflows into a unified, tactile office experience.
*   **Strategic Growth Vectors**:
    1. Interactive showcase landing pages with live token savings calculators.
    2. Partner co-marketing campaigns with productivity tooling ecosystems.
    3. Phased enterprise pilots focusing on collaborative multi-agent orchestration.""",
    
    "agent-a": """### Data Analytics Pipeline & Automation Architecture
*   **System Event Schema**: All real-time movement state transitions mapped to an SQLite event bus.
*   **Database Metrics Layout**: Tracks completed vs aborted tasks with automated query indexing for token reduction computations.
*   **Automated Action Items**:
    1. Build clean Cron-based health checking jobs.
    2. Configure automatic database query tuning metrics.
    3. Expose REST endpoints with strict schemas for dashboard rendering.""",
    
    "agent-r": """### Content Development & Launch Communications
*   **Narrative Framework**: Crafting an engaging story around AI agent collaboration and context optimization.
*   **Publication Schedule**:
    1. Teaser copy highlighting zero-waste token processing.
    2. Video demonstration script showcasing real-time routing.
    3. Technical announcement blog post outlining the consensus engine.""",
    
    "agent-s": """### Semantic Retrieval & Search Optimization Plan
*   **Web Scraping Strategy**: Utilizes robust headless scraping components with rate-limiting backoffs.
*   **GraphRAG Neighborhood Expansion**: Crawls 2-hop structural dependency maps inside Neo4j node clusters.
*   **Search Engine Optimization (SEO)**:
    1. Configure server-side static indexable meta-headers.
    2. Build semantic search lookup index over code assets.
    3. Verify site indexing maps are compliant with schema standards.""",
    
    "agent-k": """### Data Metrics & Pattern Analysis Report
*   **Efficiency Metrics**: Analyzed telemetry across agent routing requests showing ~75-80% context reduction.
*   **Key Findings**:
    1. Single-agent targeted dispatch minimizes token bloat.
    2. Latency profile maintains sub-400ms routing turnaround.
    3. High-confidence capability matching improves task resolution velocity."""
}

class DispatchService:
    def __init__(self):
        self.repo = DecisionRepository()
        self.classifier = TaskClassifier()
        self.router = AgentRouter()

    async def broadcast_state(self, task_id: str, session_id: str, state: str, payload: dict):
        event_type = f"task_{state.lower()}"
        if state == "IDLE":
            event_type = "agent_idle"
        elif state == "DISPATCHED":
            event_type = "agent_dispatch_started"
        elif state in ["WALKING", "ARRIVING", "WORKING", "STREAMING", "COMPLETED", "RETURNING"]:
            event_type = f"agent_{state.lower()}"
            
        full_event = {
            "type": event_type,
            "session_id": session_id,
            "task_id": task_id,
            "decision_id": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }
        
        # Log to db
        self.repo.add_task_event(task_id, event_type, payload)
        
        # Broadcast via WebSockets
        if manager:
            try:
                await manager.broadcast(session_id, full_event)
                logger.info(f"Broadcasted event '{event_type}' for task {task_id}")
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
        else:
            logger.warning("WebSocket manager not available, skipped broadcast.")

    async def run_task_execution(self, task_id: str):
        task = self.repo.get_task(task_id)
        if not task:
            logger.error(f"Task with ID {task_id} not found.")
            return

        session_id = task["session_id"]
        prompt = task["prompt"]
        start_time = time.time()

        try:
            # 1. EVALUATING
            self.repo.update_task(task_id, {"status": "EVALUATING"})
            await self.broadcast_state(task_id, session_id, "EVALUATING", {"status": "EVALUATING"})
            await asyncio.sleep(1)

            # 2. ROUTING
            self.repo.update_task(task_id, {"status": "ROUTING"})
            await self.broadcast_state(task_id, session_id, "ROUTING", {"status": "ROUTING"})
            
            classification = self.classifier.classify_task(prompt)
            route = self.router.route_task(prompt, classification)
            
            selected_agent_id = route["selected_agent"]
            match_score = route["match_score"]
            reason = route["reason"]
            skipped_agents = route["skipped_agents"]
            
            self.repo.update_task(task_id, {
                "status": "SELECTED",
                "selected_agent_id": selected_agent_id,
                "match_score": match_score,
                "reason": reason,
                "skipped_agents": skipped_agents
            })
            
            agent = self.repo.get_agent(selected_agent_id)
            cubicle = (agent.get("cubicle") if agent else None) or selected_agent_id.replace("agent-", "").upper()
            if cubicle not in CUBICLE_COORDINATES:
                cubicle = "S"
            
            # 3. SELECTED
            await self.broadcast_state(task_id, session_id, "SELECTED", {
                "selected_agent": selected_agent_id,
                "match_score": match_score,
                "reason": reason,
                "skipped_agents": skipped_agents
            })
            await asyncio.sleep(1.5)

            # Update agent status to BUSY
            self.repo.update_agent_status(selected_agent_id, "BUSY")

            # 4. DISPATCHED
            self.repo.update_task(task_id, {"status": "DISPATCHED"})
            await self.broadcast_state(task_id, session_id, "DISPATCHED", {
                "agent_id": selected_agent_id,
                "cubicle": cubicle
            })
            await asyncio.sleep(1)

            # 5. WALKING (to cubicle)
            waypoints = CUBICLE_COORDINATES.get(cubicle, CUBICLE_COORDINATES["S"])
            self.repo.update_task(task_id, {"status": "WALKING"})
            await self.broadcast_state(task_id, session_id, "WALKING", {
                "agent_id": selected_agent_id,
                "movement": {
                    "from": "holding-bay",
                    "to": f"cubicle-{cubicle}",
                    "waypoints": waypoints
                }
            })
            # Simulate walking duration
            await asyncio.sleep(2)

            # 6. ARRIVING
            self.repo.update_task(task_id, {"status": "ARRIVING"})
            await self.broadcast_state(task_id, session_id, "ARRIVING", {
                "agent_id": selected_agent_id,
                "cubicle": cubicle
            })
            await asyncio.sleep(1)

            # 7. WORKING
            self.repo.update_task(task_id, {"status": "WORKING"})
            await self.broadcast_state(task_id, session_id, "WORKING", {
                "agent_id": selected_agent_id
            })
            await asyncio.sleep(1)

            # 8. STREAMING & LLM Execution
            self.repo.update_task(task_id, {"status": "STREAMING"})
            await self.broadcast_state(task_id, session_id, "STREAMING", {
                "agent_id": selected_agent_id
            })

            # Formulate system prompt & call Gemini if available
            sys_prompt = f"You are {agent['name']}, acting in the role: {agent['role']}. Capabilities: {agent['capabilities']}."
            api_key = os.environ.get("GEMINI_API_KEY")
            result_text = ""
            
            prompt_tokens = 240
            completion_tokens = 0

            if api_key and call_gemini:
                try:
                    # Request analysis output
                    llm_prompt = f"satisfy this user task prompt: {prompt}"
                    response = call_gemini(llm_prompt, system_instruction=sys_prompt)
                    if response:
                        result_text = response.strip()
                except Exception as e:
                    logger.error(f"Gemini agent execution failed: {e}")

            if not result_text:
                result_text = MOCK_RESPONSES.get(selected_agent_id, MOCK_RESPONSES["agent-m"])

            # Stream response back word-by-word to simulate typewriter token streaming
            words = result_text.split(" ")
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i+chunk_size])
                if i > 0:
                    chunk = " " + chunk
                
                # Stream delta
                await self.broadcast_state(task_id, session_id, "STREAMING", {
                    "agent_id": selected_agent_id,
                    "delta": chunk
                })
                completion_tokens += len(chunk.split()) * 2 # Simulated token calculations
                await asyncio.sleep(0.08)

            total_tokens = prompt_tokens + completion_tokens
            # Optimization savings: Traditional context activations activate 3 agents (M, A, S), so total * 3
            traditional_tokens = total_tokens * 3
            savings_tokens = traditional_tokens - total_tokens
            reduction_percentage = round((savings_tokens / traditional_tokens) * 100, 1)

            # Record token usage
            self.repo.add_token_usage(
                task_id=task_id,
                decision_id=None,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                savings_tokens=savings_tokens
            )

            # Update agent statistics in registry
            exec_time_ms = int((time.time() - start_time) * 1000)
            self.repo.update_agent_stats(selected_agent_id, total_tokens, exec_time_ms)

            # 9. COMPLETED
            self.repo.update_task(task_id, {
                "status": "COMPLETED",
                "result": result_text,
                "execution_time_ms": exec_time_ms,
                "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            })
            await self.broadcast_state(task_id, session_id, "COMPLETED", {
                "task_id": task_id,
                "agent_id": selected_agent_id,
                "execution_time_ms": exec_time_ms,
                "tokens_used": total_tokens,
                "tokens_saved": savings_tokens,
                "reduction_percentage": reduction_percentage,
                "result": result_text
            })
            await asyncio.sleep(1)

            # 10. RETURNING (waypoints reversed)
            self.repo.update_task(task_id, {"status": "RETURNING"})
            return_waypoints = list(reversed(waypoints))
            await self.broadcast_state(task_id, session_id, "RETURNING", {
                "agent_id": selected_agent_id,
                "movement": {
                    "from": f"cubicle-{cubicle}",
                    "to": "holding-bay",
                    "waypoints": return_waypoints
                }
            })
            await asyncio.sleep(2)

            # Restore Agent Status to IDLE
            self.repo.update_agent_status(selected_agent_id, "IDLE")

            # 11. IDLE
            await self.broadcast_state(task_id, session_id, "IDLE", {
                "agent_id": selected_agent_id,
                "status": "IDLE"
            })

        except Exception as e:
            logger.error(f"Task dispatch error in state machine: {e}")
            self.repo.update_task(task_id, {"status": "ERROR"})
            if selected_agent_id:
                self.repo.update_agent_status(selected_agent_id, "IDLE")
            await self.broadcast_state(task_id, session_id, "ERROR", {
                "agent_id": selected_agent_id,
                "error_code": "EXECUTION_FAILURE",
                "message": str(e),
                "retryable": True
            })
