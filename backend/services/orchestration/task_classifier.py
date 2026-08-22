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
        
        # Default fallback classification
        fallback = {
            "intent": "generalTask",
            "required_capabilities": ["synthesis"],
            "complexity": "medium",
            "recommended_agent": "agent-m"
        }
        
        # Let's map keywords if Gemini is not configured/available
        prompt_lower = prompt.lower()
        if "marketing" in prompt_lower or "creative" in prompt_lower or "brief" in prompt_lower or "branding" in prompt_lower:
            fallback = {
                "intent": "marketingBrief",
                "required_capabilities": ["marketing", "creative"],
                "complexity": "medium",
                "recommended_agent": "agent-m"
            }
        elif "analytics" in prompt_lower or "automate" in prompt_lower or "code" in prompt_lower or "script" in prompt_lower or "api" in prompt_lower:
            fallback = {
                "intent": "analyticsAutomation",
                "required_capabilities": ["analytics", "automation", "code"],
                "complexity": "high",
                "recommended_agent": "agent-a"
            }
        elif "search" in prompt_lower or "scrap" in prompt_lower or "lookup" in prompt_lower or "support" in prompt_lower:
            fallback = {
                "intent": "searchRetrieve",
                "required_capabilities": ["search", "retrieval"],
                "complexity": "low",
                "recommended_agent": "agent-s"
            }

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

        logger.info(f"Fallback task classification used: {fallback}")
        return fallback
