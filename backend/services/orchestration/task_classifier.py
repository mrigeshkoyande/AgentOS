import os
import re
import json
import logging
from typing import Dict, List, Any, Optional

try:
    from main import call_gemini
except ImportError:
    try:
        from backend.main import call_gemini
    except ImportError:
        call_gemini = None

from repositories.decision_repository import DecisionRepository

logger = logging.getLogger("task_classifier")

class TaskClassifier:
    def __init__(self):
        self.repo = DecisionRepository()

    def classify_task(self, prompt: str) -> Dict[str, Any]:
        agents = self.repo.get_agent_registry()
        enabled_agents = [a for a in agents if a["enabled"]]
        
        # Build description of available agents for the classification prompt
        agent_descriptions = []
        for a in enabled_agents:
            agent_descriptions.append(
                f"- ID: {a['id']}, Role: {a['role']}, Capabilities: {a['capabilities']}"
            )
        agents_str = "\n".join(agent_descriptions)

        classification_prompt = f"""
        Analyze the following user task prompt:
        "{prompt}"

        Available specialist agents in the registry:
        {agents_str}

        Determine:
        1. "intent": A brief camelCase string representing the core request type.
        2. "required_capabilities": A list of capabilities needed to execute the task.
        3. "complexity": Task complexity rating: "low", "medium", or "high".
        4. "recommended_agent": The ID of the best suited agent from the registry who has the most matching capabilities.

        Return ONLY a JSON object with the following format:
        {{
            "intent": "marketingBriefGeneration",
            "required_capabilities": ["marketing", "creative", "synthesis"],
            "complexity": "medium",
            "recommended_agent": "agent-m"
        }}
        Do not add markdown formatting or backticks around the JSON. Return only raw JSON.
        """
        
        # Check for explicit agent mentions in the prompt first
        prompt_lower = prompt.lower()
        
        # 1. Direct agent mention matching
        if re.search(r"\b(agent[\s\-_]*s|@s|search\s*specialist|research\s*hub)\b", prompt_lower):
            return {
                "intent": "searchRetrieve",
                "required_capabilities": ["research", "search", "lookup", "source"],
                "complexity": "low",
                "recommended_agent": "agent-s" if "agent-s" in [a["id"] for a in enabled_agents] else enabled_agents[0]["id"]
            }
        elif re.search(r"\b(agent[\s\-_]*p|@p|creative\s*strategist|creative\s*studio|brand\s*strategist)\b", prompt_lower):
            target = "agent-p" if "agent-p" in [a["id"] for a in enabled_agents] else ("agent-m" if "agent-m" in [a["id"] for a in enabled_agents] else enabled_agents[0]["id"])
            return {
                "intent": "creativeStrategy",
                "required_capabilities": ["marketing", "strategy", "campaign", "creative"],
                "complexity": "medium",
                "recommended_agent": target
            }
        elif re.search(r"\b(agent[\s\-_]*a|@a|analytics\s*engineer|engineering\s*lab|automation\s*engineer)\b", prompt_lower):
            return {
                "intent": "analyticsAutomation",
                "required_capabilities": ["code", "api", "automation", "debug"],
                "complexity": "high",
                "recommended_agent": "agent-a" if "agent-a" in [a["id"] for a in enabled_agents] else enabled_agents[0]["id"]
            }
        elif re.search(r"\b(agent[\s\-_]*r|@r|content\s*creator|content\s*studio|copywriter|writer)\b", prompt_lower):
            return {
                "intent": "contentCreation",
                "required_capabilities": ["write", "caption", "script", "copy"],
                "complexity": "medium",
                "recommended_agent": "agent-r" if "agent-r" in [a["id"] for a in enabled_agents] else enabled_agents[0]["id"]
            }
        elif re.search(r"\b(agent[\s\-_]*k|@k|data\s*analyst|data\s*observatory|telemetry\s*analyst)\b", prompt_lower):
            return {
                "intent": "dataAnalysis",
                "required_capabilities": ["data", "analysis", "pattern", "metrics"],
                "complexity": "medium",
                "recommended_agent": "agent-k" if "agent-k" in [a["id"] for a in enabled_agents] else enabled_agents[0]["id"]
            }
        elif re.search(r"\b(agent[\s\-_]*m|@m)\b", prompt_lower):
            target = "agent-p" if "agent-p" in [a["id"] for a in enabled_agents] else ("agent-m" if "agent-m" in [a["id"] for a in enabled_agents] else enabled_agents[0]["id"])
            return {
                "intent": "marketingStrategy",
                "required_capabilities": ["marketing", "strategy", "creative"],
                "complexity": "medium",
                "recommended_agent": target
            }

        # 2. Dynamic Gemini Classification
        if call_gemini:
            try:
                response = call_gemini(classification_prompt)
                if response:
                    cleaned = re.sub(r"^```json\s*|```$", "", response.strip(), flags=re.MULTILINE)
                    res = json.loads(cleaned)
                    # Verify recommended agent exists
                    agent_ids = [a["id"] for a in enabled_agents]
                    if res.get("recommended_agent") in agent_ids:
                        logger.info(f"Dynamic task classification succeeded: {res}")
                        return res
            except Exception as e:
                logger.error(f"Gemini task classification failed: {e}. Falling back to keyword classification.")

        # 3. Comprehensive Semantic Keyword Fallbacks
        available_ids = [a["id"] for a in enabled_agents]
        p_agent = "agent-p" if "agent-p" in available_ids else ("agent-m" if "agent-m" in available_ids else available_ids[0])

        if any(w in prompt_lower for w in ["write", "script", "copy", "caption", "post", "blog", "story", "email", "article", "draft"]):
            fallback = {
                "intent": "contentCreation",
                "required_capabilities": ["write", "caption", "script", "copy"],
                "complexity": "medium",
                "recommended_agent": "agent-r" if "agent-r" in available_ids else p_agent
            }
        elif any(w in prompt_lower for w in ["data", "metrics", "pattern", "compare", "report", "insights", "telemetry", "tokens", "growth metrics"]):
            fallback = {
                "intent": "dataAnalysis",
                "required_capabilities": ["data", "analysis", "pattern", "metrics", "summary"],
                "complexity": "medium",
                "recommended_agent": "agent-k" if "agent-k" in available_ids else ("agent-a" if "agent-a" in available_ids else available_ids[0])
            }
        elif any(w in prompt_lower for w in ["code", "api", "automate", "automation", "debug", "technical", "logic", "build", "backend", "script"]):
            fallback = {
                "intent": "analyticsAutomation",
                "required_capabilities": ["code", "api", "automation", "debug"],
                "complexity": "high",
                "recommended_agent": "agent-a" if "agent-a" in available_ids else available_ids[0]
            }
        elif any(w in prompt_lower for w in ["search", "scrap", "lookup", "source", "research", "extract", "evidence", "find", "external"]):
            fallback = {
                "intent": "searchRetrieve",
                "required_capabilities": ["research", "search", "lookup", "source"],
                "complexity": "low",
                "recommended_agent": "agent-s" if "agent-s" in available_ids else available_ids[0]
            }
        elif any(w in prompt_lower for w in ["marketing", "creative", "strategy", "campaign", "brand", "branding", "launch", "positioning", "brief"]):
            fallback = {
                "intent": "creativeStrategy",
                "required_capabilities": ["marketing", "strategy", "campaign", "creative"],
                "complexity": "medium",
                "recommended_agent": p_agent
            }
        else:
            fallback = {
                "intent": "generalTask",
                "required_capabilities": ["synthesis"],
                "complexity": "medium",
                "recommended_agent": available_ids[0] if available_ids else "agent-s"
            }

        logger.info(f"Fallback task classification used: {fallback}")
        return fallback
