import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("constraint_engine")

class ConstraintEngine:
    @staticmethod
    def parse_numeric(val: Any) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        # Strip currency symbols and commas
        cleaned = str(val).replace("₹", "").replace("$", "").replace(",", "").strip()
        # Find first numeric group if it contains text like "80 days" or "80000 rupees"
        import re
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
        from typing import Tuple
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
