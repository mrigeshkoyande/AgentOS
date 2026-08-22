import logging
from typing import Dict, Any, List

logger = logging.getLogger("decision_agent_factory")

class DecisionAgentFactory:
    @staticmethod
    def generate_stakeholder_prompt(decision: dict, stakeholder: dict, 
                                    preferences: List[dict], constraints: List[dict]) -> str:
        """
        Generates a custom structured system prompt for a stakeholder agent.
        """
        title = decision["title"]
        desc = decision.get("description", "")
        options = [o["name"] for o in decision.get("options", [])]
        
        stk_name = stakeholder["name"]
        stk_role = stakeholder["role"]
        stk_weight = stakeholder.get("weight", 1.0)
        
        # Filter preferences and constraints for this stakeholder
        stk_prefs = [p for p in preferences if p["stakeholder_id"] == stakeholder["id"]]
        stk_consts = [c for c in constraints if c["stakeholder_id"] == stakeholder["id"]]
        
        prefs_str = "\n".join([
            f"- Preferred {p['criterion']}: '{p['value']}' (priority weight: {p.get('weight', 1.0)})" 
            for p in stk_prefs
        ])
        
        consts_str = "\n".join([
            f"- {c['criterion']} must be {c['operator']} '{c['value']}' ({c.get('severity', 'soft')} constraint)" 
            for c in stk_consts
        ])
        
        prompt = f"""
        You are the {stk_name} Agent representing the {stk_name} perspective in the organizational decision: "{title}".
        Decision Description: "{desc}"
        Available Options to negotiate: {options}
        
        Your stakeholder role: {stk_role} (weight: {stk_weight})
        
        Your Preferences (negotiable but important):
        {prefs_str or "- None"}
        
        Your Constraints:
        {consts_str or "- None"}
        
        Operational Rules:
        1. You must defend your assigned stakeholder perspective in all negotiation rounds.
        2. You can score proposed options between 0.0 (unacceptable) and 1.0 (perfectly satisfied).
        3. You may negotiate compromises and accept values close to your preferences if compromise is allowed.
        4. You must reject any proposal that violates your HARD constraints. Hard constraints are non-negotiable.
        5. Provide a short, structured rationale (under 100 words) justifying your score.
        """
        return prompt.strip()

    @staticmethod
    def generate_negotiator_prompt(decision: dict, stakeholders: List[dict], 
                                   options: List[dict]) -> str:
        """
        Generates a system prompt for the central Negotiator Agent.
        """
        title = decision["title"]
        desc = decision.get("description", "")
        opts_str = "\n".join([f"- Name: {o['name']}, Description: {o.get('description', '')}" for o in options])
        stk_str = "\n".join([f"- Name: {s['name']}, Role: {s['role']}, Weight: {s.get('weight', 1.0)}" for s in stakeholders])
        
        prompt = f"""
        You are the central Negotiator Agent for the decision: "{title}".
        Decision Context: "{desc}"
        
        Available Options:
        {opts_str}
        
        Stakeholders Involved:
        {stk_str}
        
        Your Responsibilities:
        1. Review the scores, rationales, and preferences of all stakeholders.
        2. Identify specific disagreements and conflict points (e.g. Cost vs Performance).
        3. Formulate balanced proposals or counter-proposals that maximize consensus satisfaction.
        4. Recommend compromises to stakeholders (e.g. suggesting option permutations or reserved tiers).
        5. Track negotiation rounds. Your goal is to reach consensus above {decision.get('consensus_threshold', 0.7)} within {decision.get('max_rounds', 5)} rounds.
        6. If no consensus is possible, formulate a clear escalation log explaining why the options are infeasible.
        
        Output format: Always write a structured proposal including selected option name, attributes (like cost, time, scope), and reasoning.
        """
        return prompt.strip()
