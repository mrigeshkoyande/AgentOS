from typing import List, Dict, Any
from .models import Option, Stakeholder, Constraint, Preference
from .preference_engine import evaluate_preference, calculate_weighted_satisfaction
from .constraint_engine import validate_constraint, validate_option_constraints
from .conflict_detector import detect_conflicts
from .consensus_engine import calculate_consensus
from .ranking_engine import rank_options
from .tradeoff_engine import calculate_tradeoffs
from .dissent_engine import analyze_dissent
from .sensitivity_engine import run_sensitivity_analysis

def evaluate_preferences(options: List[Option], stakeholders: List[Stakeholder]) -> Dict[str, Any]:
    """
    Evaluates satisfaction scores for all options across all stakeholders.
    Exposes a clean interface for Person 4 / frontend.
    """
    return {
        opt.id: calculate_weighted_satisfaction(opt, stakeholders)
        for opt in options
    }

def validate_constraints(options: List[Option], constraints: List[Constraint]) -> Dict[str, Any]:
    """
    Validates all constraints across a list of options.
    Exposes a clean interface for Person 4 / frontend.
    """
    results = {}
    for opt in options:
        status, satisfied, violated, penalty = validate_option_constraints(opt, constraints)
        results[opt.id] = {
            "status": status,
            "satisfied_constraints": satisfied,
            "violated_soft_constraints": violated,
            "total_penalty": penalty
        }
    return results
