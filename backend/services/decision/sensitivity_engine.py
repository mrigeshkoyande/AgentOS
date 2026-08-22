import copy
from typing import Any, Dict, List, Optional
from .models import Option, Stakeholder, Constraint
from .consensus_engine import calculate_consensus
from .ranking_engine import rank_options

def run_sensitivity_analysis(
    options: List[Option],
    stakeholders: List[Stakeholder],
    constraints: List[Constraint],
    target_stakeholder_id: str,
    target_criterion: Optional[str] = None,
    min_weight: float = 0.0,
    max_weight: float = 10.0,
    steps: int = 11
) -> Dict[str, Any]:
    """
    Simulates changing the weight of a target criterion (or stakeholder weight if criterion is None)
    from min_weight to max_weight. Identifies crossover points where the selected option changes.
    
    Returns:
        Dict: sensitivity report showing selected option per weight step and crossover points.
    """
    # 1. Deep copy stakeholders to avoid modifying the original list
    stakeholders_copy = copy.deepcopy(stakeholders)
    
    # 2. Find target stakeholder
    target_sh = next((sh for sh in stakeholders_copy if sh.id == target_stakeholder_id), None)
    if not target_sh:
        return {
            "error": f"Stakeholder '{target_stakeholder_id}' not found."
        }

    # Generate the weight steps
    weight_steps = [min_weight + i * (max_weight - min_weight) / (steps - 1) for i in range(steps)]
    weight_steps = [round(w, 2) for w in weight_steps]

    sensitivity_steps = []
    
    # Find original weight for reporting
    original_weight = 1.0
    if target_criterion:
        target_pref = next((p for p in target_sh.preferences if p.criterion == target_criterion), None)
        if target_pref:
            original_weight = target_pref.weight
    else:
        original_weight = target_sh.weight

    # 3. Simulate weights
    for w in weight_steps:
        # Apply the weight
        if target_criterion:
            target_pref = next((p for p in target_sh.preferences if p.criterion == target_criterion), None)
            if target_pref:
                target_pref.weight = w
        else:
            target_sh.weight = w
            
        # Recompute consensus and ranking
        consensus_res = calculate_consensus(options, stakeholders_copy, constraints)
        rank_res = rank_options(options, consensus_res)
        
        selected_option = None
        selected_score = 0.0
        
        if rank_res["status"] == "SUCCESS" and rank_res["ranking"]:
            top = rank_res["ranking"][0]
            selected_option = top["option_name"]
            selected_score = top["consensus_score"]
        else:
            selected_option = "NO_FEASIBLE_OPTION"
            selected_score = 0.0

        sensitivity_steps.append({
            "weight": w,
            "selected_option": selected_option,
            "consensus_score": round(selected_score, 4)
        })

    # 4. Calculate Crossover Points
    crossover_points = []
    if sensitivity_steps:
        current_opt = sensitivity_steps[0]["selected_option"]
        start_w = sensitivity_steps[0]["weight"]
        
        for idx in range(1, len(sensitivity_steps)):
            step = sensitivity_steps[idx]
            if step["selected_option"] != current_opt:
                # We found a crossover!
                end_w = sensitivity_steps[idx - 1]["weight"]
                crossover_points.append({
                    "weight_range": [start_w, end_w],
                    "selected_option": current_opt
                })
                current_opt = step["selected_option"]
                start_w = step["weight"]
                
        # Append the final range
        crossover_points.append({
            "weight_range": [start_w, sensitivity_steps[-1]["weight"]],
            "selected_option": current_opt
        })

    return {
        "stakeholder_id": target_stakeholder_id,
        "stakeholder_name": target_sh.name,
        "target_criterion": target_criterion,
        "original_weight": original_weight,
        "sensitivity_steps": sensitivity_steps,
        "crossover_points": crossover_points
    }
