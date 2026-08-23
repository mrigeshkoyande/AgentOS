import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

try:
    from websocket_manager import manager
except ImportError:
    try:
        from backend.websocket_manager import manager
    except ImportError:
        manager = None

try:
    from main import get_db
except ImportError:
    try:
        from backend.main import get_db
    except ImportError:
        get_db = None

from repositories.decision_repository import DecisionRepository
from services.decision.consensus_engine import ConsensusEngine
from services.negotiation.negotiation_engine import NegotiationEngine

logger = logging.getLogger("decision_service")

VALID_TRANSITIONS = {
    "DRAFT": ["SETUP"],
    "SETUP": ["READY"],
    "READY": ["RUNNING"],
    "RUNNING": ["NEGOTIATING", "FAILED"],
    "NEGOTIATING": ["AWAITING_APPROVAL", "FAILED"],
    "AWAITING_APPROVAL": ["APPROVED", "REJECTED", "CHANGES_REQUESTED"],
    "APPROVED": ["COMPLETED"],
    "CHANGES_REQUESTED": ["SETUP"],
    "COMPLETED": [],
    "REJECTED": [],
    "FAILED": []
}

class DecisionService:
    def __init__(self):
        self.repo = DecisionRepository()

    async def broadcast_event(self, session_id: str, decision_id: str, event_type: str, payload: dict):
        if manager is not None:
            try:
                await manager.broadcast(session_id, {
                    "type": event_type,
                    "session_id": session_id,
                    "decision_id": decision_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "payload": payload
                })
                logger.info(f"Broadcasted WS event '{event_type}' for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to broadcast WS event '{event_type}': {e}")
        else:
            logger.warning("WS Connection Manager not available, skipped broadcast")

    def create_decision(self, session_id: str, title: str, description: Optional[str] = None, 
                        strategy: str = "consensus", deadline: Optional[str] = None, 
                        consensus_threshold: float = 0.7, max_rounds: int = 5, 
                        compromise_allowed: bool = True, approval_required: bool = True) -> str:
        # Validate session exists
        if get_db is not None:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            session_exists = cursor.fetchone() is not None
            conn.close()
            if not session_exists:
                raise ValueError(f"Session with ID '{session_id}' does not exist")

        # Validate inputs
        if not title.strip():
            raise ValueError("Decision title is required")
        if not (0.0 <= consensus_threshold <= 1.0):
            raise ValueError("Consensus threshold must be between 0.0 and 1.0")
        if max_rounds < 1:
            raise ValueError("Max negotiation rounds must be at least 1")

        decision_id = self.repo.create_decision(
            session_id=session_id,
            title=title,
            description=description,
            strategy=strategy,
            deadline=deadline,
            consensus_threshold=consensus_threshold,
            max_rounds=max_rounds,
            compromise_allowed=compromise_allowed,
            approval_required=approval_required
        )
        return decision_id

    def validate_decision_for_execution(self, decision_id: str) -> Tuple[bool, List[str]]:
        dec = self.repo.get_decision(decision_id)
        if not dec:
            return False, ["Decision not found"]
        
        errors = []
        
        # At least one stakeholder
        if not dec.get("stakeholders"):
            errors.append("Decision must have at least one stakeholder")
            
        # Roles and weights check
        has_approver = False
        for stk in dec.get("stakeholders", []):
            if stk["role"] not in ["driver", "contributor", "approver", "informed"]:
                errors.append(f"Invalid stakeholder role '{stk['role']}' for stakeholder {stk['name']}")
            if stk["weight"] <= 0:
                errors.append(f"Stakeholder weight must be positive for stakeholder {stk['name']}")
            if stk["role"] == "approver":
                has_approver = True
                
        # If approval is required, there must be at least one approver
        if dec["approval_required"] and not has_approver:
            errors.append("Decision requires approval, but no approver is assigned")
            
        # Preferences check
        for pref in dec.get("preferences", []):
            if pref["weight"] <= 0:
                errors.append(f"Preference weight must be positive for preference criterion '{pref['criterion']}'")
            if pref["priority"] not in ["high", "medium", "low"]:
                errors.append(f"Invalid preference priority '{pref['priority']}'")
                
        # Constraints check
        valid_operators = ["==", "!=", ">", "<", ">=", "<="]
        for const in dec.get("constraints", []):
            if const["operator"] not in valid_operators:
                errors.append(f"Invalid operator '{const['operator']}' for constraint criterion '{const['criterion']}'")
            if const["severity"] not in ["hard", "soft"]:
                errors.append(f"Invalid severity '{const['severity']}' for constraint criterion '{const['criterion']}'")

        # Options check
        if not dec.get("options"):
            errors.append("Decision must have at least one decision option")

        return len(errors) == 0, errors

    async def update_status(self, decision_id: str, next_status: str, authorized_user: Optional[str] = None) -> bool:
        dec = self.repo.get_decision(decision_id)
        if not dec:
            raise ValueError("Decision not found")
        
        current_status = dec["status"]
        if next_status not in VALID_TRANSITIONS.get(current_status, []):
            raise ValueError(f"Invalid state transition from {current_status} to {next_status}")

        # Authorization Checks for approvals
        if next_status in ["APPROVED", "REJECTED", "CHANGES_REQUESTED"]:
            if dec["approval_required"]:
                # The authorized_user must be a stakeholder with role = 'approver'
                approvers = [s["id"] for s in dec["stakeholders"] if s["role"] == "approver"]
                if not authorized_user or authorized_user not in approvers:
                    raise PermissionError("Only an authorized approver can approve, reject, or request changes for this decision")

        # If transitioning to RUNNING/READY, validate decision configurations
        if next_status == "READY":
            valid, errors = self.validate_decision_for_execution(decision_id)
            if not valid:
                raise ValueError(f"Decision configuration is invalid: {', '.join(errors)}")

        updated = self.repo.update_decision(decision_id, {"status": next_status})
        if updated:
            # Broadcast specific event based on state
            event_map = {
                "SETUP": "decision_setup_updated",
                "READY": "decision_setup_updated",
                "RUNNING": "decision_started",
                "NEGOTIATING": "negotiation_round_started",
                "AWAITING_APPROVAL": "approval_required",
                "APPROVED": "decision_approved",
                "REJECTED": "decision_rejected",
                "CHANGES_REQUESTED": "decision_changes_requested",
                "COMPLETED": "decision_completed",
                "FAILED": "decision_failed"
            }
            event_type = event_map.get(next_status, "decision_setup_updated")
            await self.broadcast_event(dec["session_id"], decision_id, event_type, {"status": next_status})
        
        return updated

    async def simulate_decision(self, decision_id: str, overrides: dict) -> dict:
        dec = self.repo.get_decision(decision_id)
        if not dec:
            raise ValueError("Decision not found")

        # Create simulated version (copy in memory)
        sim = json.loads(json.dumps(dec))
        sim["id"] = f"{dec['id']}_sim"
        sim["status"] = "COMPLETED"
        
        # Apply overrides
        if overrides.get("preferences"):
            sim["preferences"] = []
            for p in overrides["preferences"]:
                sim["preferences"].append({
                    "id": f"pref_sim_{p['criterion']}",
                    "stakeholder_id": p["stakeholder_id"],
                    "criterion": p["criterion"],
                    "value": p["value"],
                    "weight": p.get("weight", 1.0),
                    "priority": p.get("priority", "medium"),
                    "description": p.get("description", "")
                })

        if overrides.get("constraints"):
            sim["constraints"] = []
            for c in overrides["constraints"]:
                sim["constraints"].append({
                    "id": f"const_sim_{c['criterion']}",
                    "stakeholder_id": c["stakeholder_id"],
                    "criterion": c["criterion"],
                    "operator": c["operator"],
                    "value": c["value"],
                    "severity": c.get("severity", "soft")
                })

        if overrides.get("options"):
            sim["options"] = []
            for o in overrides["options"]:
                sim["options"].append({
                    "id": f"opt_sim_{o['name']}",
                    "decision_id": sim["id"],
                    "name": o["name"],
                    "description": o.get("description", "")
                })

        # Run simulation logic dynamically using deterministic engines
        consensus_engine = ConsensusEngine()
        
        feasible_sims = []
        infeasible_sims = []
        
        for o in sim["options"]:
            o_attrs = NegotiationEngine.extract_attributes(o)
            eval_res = consensus_engine.evaluate_proposal(sim, o_attrs)
            if eval_res["is_feasible"]:
                feasible_sims.append((o, eval_res))
            else:
                infeasible_sims.append((o, eval_res))

        if feasible_sims:
            # Sort by consensus score descending
            feasible_sims.sort(key=lambda x: x[1]["consensus_score"], reverse=True)
            best_opt, best_eval = feasible_sims[0]
            selected_option = best_opt["name"]
            consensus_score = best_eval["consensus_score"]
            violations = best_eval["violations"]
            stk_scores = best_eval["stakeholder_scores"]
        else:
            selected_option = "None - Infeasible"
            consensus_score = 0.0
            violations = ["All options violate hard constraints in this simulation configuration."]
            stk_scores = {s["id"]: 0.0 for s in sim.get("stakeholders", [])}
        
        # Generate simulation round
        sim["negotiation_rounds"] = [{
            "id": "neg_sim_1",
            "decision_id": sim["id"],
            "round_number": 1,
            "status": "completed",
            "proposal": selected_option,
            "counter_proposal": None,
            "reason": "Simulation evaluation using constraint engine.",
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }]

        # Generate simulated outcome
        sim["outcome"] = {
            "id": "out_sim",
            "decision_id": sim["id"],
            "selected_option": selected_option,
            "consensus_score": consensus_score,
            "rationale": f"Simulation selecting {selected_option} with {consensus_score*100}% consensus. Violations: {violations}",
            "tradeoffs": "Tradeoff between cost efficiency and implementation duration.",
            "dissent": "Calculated stakeholder satisfaction scores: " + str(stk_scores),
            "next_actions": "1. Deploy simulation configuration.\n2. Finalize production specifications.",
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Generate simulated conflict if overrides trigger it
        if len(sim["preferences"]) > 1 and sim["preferences"][0]["criterion"] == sim["preferences"][1]["criterion"]:
            sim["conflicts"] = [{
                "id": "conf_sim",
                "decision_id": sim["id"],
                "criterion": sim["preferences"][0]["criterion"],
                "stakeholder_ids": [sim["preferences"][0]["stakeholder_id"], sim["preferences"][1]["stakeholder_id"]],
                "description": "Stakeholders have opposing preferences on the same criterion",
                "severity": "high",
                "status": "active",
                "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            }]
        else:
            sim["conflicts"] = []

        return sim
