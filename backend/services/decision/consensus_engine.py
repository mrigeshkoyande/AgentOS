import math
from typing import Any, Dict, List
from .models import Option, Stakeholder, Constraint
from .preference_engine import calculate_weighted_satisfaction
from .constraint_engine import validate_option_constraints

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
