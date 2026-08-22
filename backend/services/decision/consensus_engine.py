import math
import logging
from typing import Any, Dict, List, Tuple
from .models import Option, Stakeholder, Constraint
from .preference_engine import calculate_weighted_satisfaction
from .constraint_engine import validate_option_constraints
from services.decision.constraint_engine import ConstraintEngine

# --- Functions for standard decision routing (Person 4 / Remote main) ---

def calculate_consensus(
    options: List[Option],
    stakeholders: List[Stakeholder],
    constraints: List[Constraint]
) -> Dict[str, Any]:
    """
    Computes consensus details, including satisfaction scores, constraint statuses,
    and dispersion-penalized consensus scores for all options.
    
    Returns:
        Dict: {
            "options": Dict[str, Dict]  # option_id -> detailed evaluation dict
        }
    """
    results = {}

    for opt in options:
        # 1. Calculate stakeholder satisfaction (overall and individual)
        sat_result = calculate_weighted_satisfaction(opt, stakeholders)
        overall_score = sat_result["overall_score"]
        stakeholder_scores = sat_result["stakeholder_scores"]
        individual_scores = sat_result["individual_scores"]

        # 2. Validate constraints
        status, satisfied_c, violated_soft_c, total_penalty = validate_option_constraints(opt, constraints)

        # 3. Calculate final consensus score if feasible
        if status == "infeasible":
            consensus_score = 0.0
            penalized_score = 0.0
        else:
            # Apply soft constraint penalty
            penalized_score = max(0.0, overall_score - total_penalty)
            
            # Calculate standard deviation of stakeholder scores to penalize dispersion
            scores_list = list(stakeholder_scores.values())
            if len(scores_list) > 1:
                mean = sum(scores_list) / len(scores_list)
                variance = sum((x - mean) ** 2 for x in scores_list) / len(scores_list)
                std_dev = math.sqrt(variance)
            else:
                std_dev = 0.0
            
            # consensus_score = penalized_score * (1.0 - std_dev)
            consensus_score = max(0.0, min(1.0, penalized_score * (1.0 - std_dev)))

        results[opt.id] = {
            "option_id": opt.id,
            "option_name": opt.name,
            "status": status,  # feasible or infeasible
            "overall_score": round(overall_score, 4),
            "penalized_score": round(penalized_score, 4),
            "consensus_score": round(consensus_score, 4),
            "stakeholder_scores": {k: round(v, 4) for k, v in stakeholder_scores.items()},
            "individual_scores": individual_scores,
            "satisfied_constraints": satisfied_c,
            "violated_soft_constraints": violated_soft_c,
            "total_penalty": round(total_penalty, 4)
        }

    return {"options": results}


# --- ConsensusEngine class for SPARK workspace & multi-agent negotiation ---

logger = logging.getLogger("consensus_engine")

class ConsensusEngine:
    def __init__(self):
        self.constraint_engine = ConstraintEngine()

    @staticmethod
    def calculate_preference_satisfaction(pref_val: str, proposal_val: Any) -> float:
        if proposal_val is None:
            return 0.0

        p_str = str(proposal_val).lower().strip()
        pref_str = str(pref_val).lower().strip()

        if p_str == pref_str:
            return 1.0

        # Handle semantic keywords like "low", "medium", "high"
        try:
            p_num = ConstraintEngine.parse_numeric(proposal_val)
            if pref_str == "low" and p_num < 80000:
                return 1.0
            elif pref_str == "medium" and 80000 <= p_num <= 150000:
                return 1.0
            elif pref_str == "high" and p_num > 150000:
                return 1.0
        except Exception:
            pass

        # Partial matching (sub-strings)
        if pref_str in p_str or p_str in pref_str:
            return 0.5

        return 0.0

    def evaluate_proposal(self, decision: dict, proposal_attributes: dict) -> dict:
        """
        Evaluate a single proposal against all stakeholders, constraints, and preferences.
        """
        stakeholders = decision.get("stakeholders", [])
        preferences = decision.get("preferences", [])
        constraints = decision.get("constraints", [])

        # 1. Deterministic Hard Constraint Validation
        is_feasible, violations = self.constraint_engine.validate_proposal(constraints, proposal_attributes)
        
        # Hard constraints violation makes the proposal completely infeasible
        if not is_feasible:
            return {
                "is_feasible": False,
                "consensus_score": 0.0,
                "stakeholder_scores": {s["id"]: 0.0 for s in stakeholders},
                "violations": violations,
                "satisfied_constraints": []
            }

        # 2. Preference Satisfaction per Stakeholder
        stakeholder_scores = {}
        total_stakeholder_weight = 0.0
        weighted_score_sum = 0.0

        for s in stakeholders:
            stk_id = s["id"]
            stk_weight = s.get("weight", 1.0)
            
            # Find preferences for this stakeholder
            stk_prefs = [p for p in preferences if p["stakeholder_id"] == stk_id]
            
            if not stk_prefs:
                # Default satisfaction if no preferences defined
                stk_score = 1.0
            else:
                total_pref_weight = 0.0
                pref_score_sum = 0.0
                
                for p in stk_prefs:
                    criterion = p["criterion"]
                    pref_val = p["value"]
                    p_weight = p.get("weight", 1.0)
                    
                    # Find attribute in proposal
                    p_val = None
                    for pk, pv in proposal_attributes.items():
                        if pk.lower().strip() == criterion.lower().strip():
                            p_val = pv
                            break
                            
                    satisfaction = ConsensusEngine.calculate_preference_satisfaction(pref_val, p_val)
                    pref_score_sum += satisfaction * p_weight
                    total_pref_weight += p_weight
                    
                stk_score = pref_score_sum / max(total_pref_weight, 1.0)

            # Reduce score slightly if there are soft constraint violations for this stakeholder
            stk_constraints = [c for c in constraints if c["stakeholder_id"] == stk_id and c.get("severity") == "soft"]
            for c in stk_constraints:
                criterion = c["criterion"]
                operator = c["operator"]
                val = c["value"]
                
                # Check soft constraint
                p_val = None
                for pk, pv in proposal_attributes.items():
                    if pk.lower().strip() == criterion.lower().strip():
                        p_val = pv
                        break
                satisfied = ConstraintEngine.evaluate_constraint(operator, val, p_val)
                if not satisfied:
                    stk_score *= 0.8 # 20% penalty for violating a soft constraint
            
            stk_score = round(max(0.0, min(1.0, stk_score)), 2)
            stakeholder_scores[stk_id] = stk_score
            
            # Sum up weighted overall consensus
            weighted_score_sum += stk_score * stk_weight
            total_stakeholder_weight += stk_weight

        overall_consensus = weighted_score_sum / max(total_stakeholder_weight, 1.0)
        overall_consensus = round(overall_consensus, 2)

        return {
            "is_feasible": True,
            "consensus_score": overall_consensus,
            "stakeholder_scores": stakeholder_scores,
            "violations": violations, # contains soft constraint violations
            "satisfied_constraints": [c["criterion"] for c in constraints]
        }
