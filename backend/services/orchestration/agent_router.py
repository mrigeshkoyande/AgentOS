import logging
from typing import Dict, List, Any, Tuple
from repositories.decision_repository import DecisionRepository

logger = logging.getLogger("agent_router")

class AgentRouter:
    def __init__(self):
        self.repo = DecisionRepository()

    def route_task(self, task_prompt: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        recommended_id = classification["recommended_agent"]
        req_caps = set(classification["required_capabilities"])
        
        agents = self.repo.get_agent_registry()
        enabled_agents = [a for a in agents if a["enabled"]]
        
        selected_agent = None
        skipped_agents = []
        
        # Find the selected agent details
        for a in enabled_agents:
            if a["id"] == recommended_id:
                selected_agent = a
                break
                
        # If the recommended agent is disabled or missing, fallback to the one with the highest capability match
        if not selected_agent and enabled_agents:
            highest_score = -1
            best_agent = enabled_agents[0]
            for a in enabled_agents:
                caps = set(a["capabilities"])
                common = caps.intersection(req_caps)
                score = len(common) / max(len(req_caps), 1)
                if score > highest_score:
                    highest_score = score
                    best_agent = a
            selected_agent = best_agent
            recommended_id = selected_agent["id"]

        # Calculate routing details and skipped agents list
        for a in enabled_agents:
            if a["id"] == recommended_id:
                continue
                
            # Determine reason for skipping
            caps = set(a["capabilities"])
            common = caps.intersection(req_caps)
            
            if not common:
                reason = f"No matching capabilities for required tasks: {list(req_caps)}"
            else:
                missing = req_caps - caps
                reason = f"Lacks specialized capabilities: {list(missing)}"
                
            skipped_agents.append({
                "id": a["id"],
                "name": a["name"],
                "reason": reason
            })
            
        # Calculate match score based on capability intersection
        if selected_agent:
            caps = set(selected_agent["capabilities"])
            common = caps.intersection(req_caps)
            # base score of 0.85 + proportion of matching capabilities up to 0.13
            match_score = round(0.85 + (len(common) / max(len(req_caps), 1)) * 0.13, 2)
            reason_str = f"{selected_agent['name']} matches core task intent and has specialized capabilities for {list(common)}."
        else:
            match_score = 0.0
            reason_str = "No suitable agents found in the registry."

        return {
            "selected_agent": recommended_id,
            "match_score": match_score,
            "reason": reason_str,
            "skipped_agents": skipped_agents
        }
