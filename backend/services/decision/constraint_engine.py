from typing import Any, Dict, List, Tuple
from .models import Option, Constraint

def check_operator(val: Any, op: str, target: Any) -> bool:
    """
    Helper function to evaluate operators.
    Returns True if the operator condition is met, False otherwise.
    """
    op = op.strip().lower()
    try:
        if op in ("=", "=="):
            if isinstance(val, (int, float)) and isinstance(target, (int, float)):
                return abs(val - target) < 1e-9
            return str(val) == str(target)
        
        elif op == "!=":
            if isinstance(val, (int, float)) and isinstance(target, (int, float)):
                return abs(val - target) >= 1e-9
            return str(val) != str(target)
            
        elif op == ">":
            return float(val) > float(target)
            
        elif op == ">=":
            return float(val) >= float(target)
            
        elif op == "<":
            return float(val) < float(target)
            
        elif op == "<=":
            return float(val) <= float(target)
            
        elif op in ("contains", "must_include"):
            target_str = str(target).lower()
            if isinstance(val, list):
                return any(str(item).lower() == target_str for item in val)
            return target_str in str(val).lower()
            
    except (ValueError, TypeError):
        # Handle type mismatches or conversion failures by returning False
        return False
        
    return False


def validate_constraint(option: Option, constraint: Constraint) -> Dict[str, Any]:
    """
    Validates a single constraint against an option.
    Returns a status dict detailing satisfaction and feasibility.
    """
    criterion = constraint.criterion
    
    # If the attribute is missing, it fails the constraint
    if criterion not in option.attributes:
        satisfied = False
        error_msg = f"Missing attribute '{criterion}' on option."
    else:
        val = option.attributes[criterion]
        satisfied = check_operator(val, constraint.operator, constraint.value)
        error_msg = None if satisfied else f"Value '{val}' does not satisfy '{constraint.operator} {constraint.value}'."

    is_hard = constraint.type.upper() == "HARD"
    option_status = "feasible"
    
    if not satisfied and is_hard:
        option_status = "infeasible"

    return {
        "constraint_satisfied": satisfied,
        "option_status": option_status,
        "constraint": constraint,
        "error_message": error_msg
    }


def validate_option_constraints(option: Option, constraints: List[Constraint]) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], float]:
    """
    Validates all constraints for a single option.
    
    Returns:
        Tuple of:
            - option_status: "feasible" or "infeasible"
            - satisfied_constraints: list of details
            - violated_soft_constraints: list of details
            - total_penalty: float (sum of penalties from violated soft constraints)
    """
    option_status = "feasible"
    satisfied_constraints = []
    violated_soft_constraints = []
    total_penalty = 0.0

    for constraint in constraints:
        result = validate_constraint(option, constraint)
        
        if result["constraint_satisfied"]:
            satisfied_constraints.append({
                "criterion": constraint.criterion,
                "operator": constraint.operator,
                "value": constraint.value,
                "type": constraint.type
            })
        else:
            if constraint.type.upper() == "HARD":
                option_status = "infeasible"
            else:
                violated_soft_constraints.append({
                    "criterion": constraint.criterion,
                    "operator": constraint.operator,
                    "value": constraint.value,
                    "type": constraint.type,
                    "penalty": constraint.penalty,
                    "error_message": result["error_message"]
                })
                total_penalty += constraint.penalty

    return option_status, satisfied_constraints, violated_soft_constraints, total_penalty
