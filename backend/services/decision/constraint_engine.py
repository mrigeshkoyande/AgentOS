import logging
import re
from typing import Any, Dict, List, Tuple
from .models import Option, Constraint

# --- Functions for standard decision routing (Person 4 / Remote main) ---

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
    operator = constraint.operator
    target_value = constraint.value
    
    # Extract attribute value from Option attributes dict
    attributes = option.attributes or {}
    option_value = attributes.get(criterion)
    
    if option_value is None:
        # If attribute is missing entirely, evaluate as violation
        status = "infeasible" if constraint.type.upper() == "HARD" else "feasible"
        return {
            "constraint_satisfied": False,
            "option_status": status,
            "error_message": f"Option is missing the required attribute: {criterion}"
        }

    satisfied = check_operator(option_value, operator, target_value)
    status = "feasible"
    if not satisfied and constraint.type.upper() == "HARD":
        status = "infeasible"
    
    return {
        "constraint_satisfied": satisfied,
        "option_status": status,
        "error_message": "" if satisfied else f"Constraint violated: {criterion} (value: {option_value}) {operator} {target_value}"
    }


def validate_option_constraints(option: Option, constraints: List[Constraint]) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], float]:
    """
    Validates all constraints for a single option.
    Returns a tuple of:
        - option_status: "feasible" or "infeasible"
        - satisfied_constraints: list of satisfied constraint summaries
        - violated_soft_constraints: list of violated soft constraint summaries with penalties
        - total_penalty: sum of penalties for violated soft constraints
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


# --- ConstraintEngine class for SPARK workspace & multi-agent negotiation ---

logger = logging.getLogger("constraint_engine")

class ConstraintEngine:
    @staticmethod
    def parse_numeric(val: Any) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        # Strip currency symbols and commas
        cleaned = str(val).replace("₹", "").replace("$", "").replace(",", "").strip()
        # Find first numeric group if it contains text like "80 days" or "80000 rupees"
        match = re.search(r"[-+]?\d*\.\d+|\d+", cleaned)
        if match:
            return float(match.group())
        raise ValueError(f"Could not parse numeric value from '{val}'")

    @staticmethod
    def evaluate_constraint(operator: str, constraint_val: str, proposal_val: Any) -> bool:
        # If proposal value is missing, fail hard constraints
        if proposal_val is None:
            return False

        operator = operator.strip()

        # Handle contains and must_include first
        if operator in ["contains", "must_include"]:
            return str(constraint_val).lower() in str(proposal_val).lower()

        # Try numeric comparison
        try:
            c_num = ConstraintEngine.parse_numeric(constraint_val)
            p_num = ConstraintEngine.parse_numeric(proposal_val)

            if operator in ["=", "=="]:
                return p_num == c_num
            elif operator == "!=":
                return p_num != c_num
            elif operator == ">":
                return p_num > c_num
            elif operator == ">=":
                return p_num >= c_num
            elif operator == "<":
                return p_num < c_num
            elif operator == "<=":
                return p_num <= c_num
        except Exception:
            # Fallback to string comparison if not numeric
            c_str = str(constraint_val).lower().strip()
            p_str = str(proposal_val).lower().strip()

            if operator in ["=", "=="]:
                return p_str == c_str
            elif operator == "!=":
                return p_str != c_str
            elif operator == ">":
                return p_str > c_str
            elif operator == ">=":
                return p_str >= c_str
            elif operator == "<":
                return p_str < c_str
            elif operator == "<=":
                return p_str <= c_str

        return False

    def validate_proposal(self, constraints: List[dict], proposal_attributes: dict) -> Tuple[bool, List[str]]:
        """
        Validates a proposal's attributes against all constraints.
        Returns (is_valid, list_of_violation_messages).
        """
        violations = []
        is_valid = True

        for c in constraints:
            criterion = c["criterion"]
            operator = c["operator"]
            value = c["value"]
            severity = c.get("severity", "soft").lower()

            # Find matching attribute in proposal (case-insensitive key match)
            p_val = None
            for pk, pv in proposal_attributes.items():
                if pk.lower().strip() == criterion.lower().strip():
                    p_val = pv
                    break

            satisfied = ConstraintEngine.evaluate_constraint(operator, value, p_val)

            if not satisfied and severity == "hard":
                is_valid = False
                violations.append(
                    f"Hard constraint violation: {criterion} (value: {p_val}) "
                    f"failed operator '{operator}' against constraint value '{value}'"
                )
            elif not satisfied:
                violations.append(
                    f"Soft constraint violation: {criterion} (value: {p_val}) "
                    f"failed operator '{operator}' against constraint value '{value}'"
                )

        return is_valid, violations
