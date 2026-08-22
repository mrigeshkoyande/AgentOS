import math
from typing import Any, Dict, List
from .models import Option

def calculate_std_dev(scores: List[float]) -> float:
    """Helper to compute standard deviation of a list of floats."""
    if len(scores) <= 1:
        return 0.0
    mean = sum(scores) / len(scores)
    variance = sum((x - mean) ** 2 for x in scores) / len(scores)
    return math.sqrt(variance)


class RankingSortKey:
    """
    Custom sort key wrapper to rank options.
    Enables sorting in ascending order, where "better" options are "less than" others.
    """
    def __init__(self, opt_res: Dict[str, Any]):
        self.opt_res = opt_res
        self.consensus_score = opt_res["consensus_score"]
        self.std_dev = calculate_std_dev(list(opt_res["stakeholder_scores"].values()))
        self.soft_viol_count = len(opt_res["violated_soft_constraints"])
        self.name = opt_res["option_name"]
        self.id = opt_res["option_id"]

    def __lt__(self, other: "RankingSortKey") -> bool:
        # 1. Consensus score (higher is better)
        if abs(self.consensus_score - other.consensus_score) > 1e-9:
            return self.consensus_score > other.consensus_score
        
        # 2. Standard deviation of stakeholder satisfaction (lower is better)
        if abs(self.std_dev - other.std_dev) > 1e-9:
            return self.std_dev < other.std_dev
            
        # 3. Soft constraints violated count (lower is better)
        if self.soft_viol_count != other.soft_viol_count:
            return self.soft_viol_count < other.soft_viol_count
            
        # 4. Option name / ID (alphabetical ascending is better)
        if self.name != other.name:
            return self.name < other.name
        return self.id < other.id


def rank_options(options: List[Option], consensus_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ranks only feasible options from the consensus results.
    Applies the tie-breaker strategy.
    
    Returns:
        Dict: {
            "status": str,  # "SUCCESS" or "NO_FEASIBLE_OPTION"
            "ranking": List[Dict]  # Ordered list of ranked option details
        }
    """
    opt_details = consensus_results.get("options", {})
    feasible_options_details = [
        detail for detail in opt_details.values() if detail["status"] == "feasible"
    ]

    if not feasible_options_details:
        return {
            "status": "NO_FEASIBLE_OPTION",
            "ranking": []
        }

    # Sort using custom comparator key
    sorted_details = sorted(feasible_options_details, key=RankingSortKey)

    ranking = []
    for rank_idx, detail in enumerate(sorted_details, start=1):
        ranking.append({
            "rank": rank_idx,
            "option_id": detail["option_id"],
            "option_name": detail["option_name"],
            "consensus_score": detail["consensus_score"],
            "overall_score": detail["overall_score"],
            "status": detail["status"]
        })

    return {
        "status": "SUCCESS",
        "ranking": ranking
    }
