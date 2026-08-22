from typing import Any, Dict, List, Optional
from .models import Option, Preference, Stakeholder

def evaluate_preference(option: Option, preference: Preference) -> float:
    """
    Evaluates the satisfaction score of a preference against an option's attributes.
    Returns a float between 0.0 (completely unsatisfied) and 1.0 (completely satisfied).
    """
    criterion = preference.criterion
    if criterion not in option.attributes:
        return 0.0

    val = option.attributes[criterion]
    target = preference.value
    strategy = preference.strategy.lower() if preference.strategy else "exact"

    # Handle weight = 0 edge case separately? The satisfaction score itself is evaluated,
    # the weighting happens in the stakeholder aggregation.
    
    # If option value is None, it is unsatisfied
    if val is None:
        return 0.0

    if strategy == "exact":
        # Handle simple types and float comparisons
        if isinstance(val, (int, float)) and isinstance(target, (int, float)):
            return 1.0 if abs(val - target) < 1e-9 else 0.0
        return 1.0 if str(val) == str(target) else 0.0

    elif strategy == "higher_is_better":
        if not isinstance(val, (int, float)) or not isinstance(target, (int, float)):
            return 1.0 if val == target else 0.0
        if val >= target:
            return 1.0
        
        # If min_value is provided, interpolate between min_value and target
        if preference.min_value is not None:
            min_val = preference.min_value
            if target > min_val:
                satisfaction = (val - min_val) / (target - min_val)
                return max(0.0, min(1.0, satisfaction))
            
        # Fallback to ratio
        if target > 0:
            satisfaction = val / target
            return max(0.0, min(1.0, satisfaction))
        return 0.0

    elif strategy == "lower_is_better":
        if not isinstance(val, (int, float)) or not isinstance(target, (int, float)):
            return 1.0 if val == target else 0.0
        if val <= target:
            return 1.0
        
        # If max_value is provided, interpolate between target and max_value
        if preference.max_value is not None:
            max_val = preference.max_value
            if max_val > target:
                satisfaction = 1.0 - (val - target) / (max_val - target)
                return max(0.0, min(1.0, satisfaction))
            
        # Fallback to inverse ratio
        if val > 0:
            satisfaction = target / val
            return max(0.0, min(1.0, satisfaction))
        return 0.0

    elif strategy == "contains":
        pref_val_str = str(target).lower()
        if isinstance(val, list):
            return 1.0 if any(str(item).lower() == pref_val_str for item in val) else 0.0
        return 1.0 if pref_val_str in str(val).lower() else 0.0

    elif strategy == "range":
        min_val = preference.min_value if preference.min_value is not None else target
        max_val = preference.max_value if preference.max_value is not None else target
        if isinstance(val, (int, float)) and isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
            return 1.0 if min_val <= val <= max_val else 0.0
        return 0.0

    # Default fallback
    return 1.0 if val == target else 0.0


def calculate_weighted_satisfaction(option: Option, stakeholders: List[Stakeholder]) -> Dict[str, Any]:
    """
    Calculates the satisfaction scores for each stakeholder and aggregates them
    using stakeholder weights.
    
    Returns:
        Dict: {
            "overall_score": float,
            "stakeholder_scores": Dict[str, float],
            "individual_scores": Dict[str, Dict[str, float]]
        }
    """
    stakeholder_scores = {}
    individual_scores = {}
    
    overall_weighted_sum = 0.0
    total_stakeholder_weight = 0.0

    for sh in stakeholders:
        sh_individual = {}
        pref_weighted_sum = 0.0
        total_pref_weight = 0.0

        for pref in sh.preferences:
            score = evaluate_preference(option, pref)
            sh_individual[pref.criterion] = score
            
            # Weighted sums
            pref_weighted_sum += score * pref.weight
            total_pref_weight += pref.weight

        # Handle stakeholder score
        if total_pref_weight > 0:
            sh_score = pref_weighted_sum / total_pref_weight
        else:
            # If a stakeholder has no preferences or all weights are 0, default to 0.0
            sh_score = 0.0

        stakeholder_scores[sh.id] = sh_score
        individual_scores[sh.id] = sh_individual

        overall_weighted_sum += sh_score * sh.weight
        total_stakeholder_weight += sh.weight

    # Aggregate overall score
    if total_stakeholder_weight > 0:
        overall_score = overall_weighted_sum / total_stakeholder_weight
    else:
        overall_score = 0.0

    return {
        "overall_score": round(overall_score, 4),
        "stakeholder_scores": {k: round(v, 4) for k, v in stakeholder_scores.items()},
        "individual_scores": {
            sh_id: {crit: round(score, 4) for crit, score in crits.items()}
            for sh_id, crits in individual_scores.items()
        }
    }
