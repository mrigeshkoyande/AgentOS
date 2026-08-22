from typing import Any, Dict, List
from .models import Stakeholder

def analyze_dissent(
    selected_option_id: str,
    consensus_results: Dict[str, Any],
    stakeholders: List[Stakeholder],
    threshold: float = 0.70
) -> Dict[str, Any]:
    """
    Identifies which stakeholders are least satisfied with the selected option
    and explains which criteria caused the dissatisfaction.
    
    Returns:
        Dict: {
            "dissenting_stakeholders": List[str],  # names or IDs of dissenting stakeholders
            "explanations": Dict[str, str]  # stakeholder_id -> textual explanation
        }
    """
    options_data = consensus_results.get("options", {})
    selected_eval = options_data.get(selected_option_id)

    if not selected_eval:
        return {
            "dissenting_stakeholders": [],
            "explanations": {}
        }

    dissenting_stakeholders = []
    explanations = {}

    stakeholder_scores = selected_eval.get("stakeholder_scores", {})
    individual_scores = selected_eval.get("individual_scores", {})

    for sh in stakeholders:
        sh_score = stakeholder_scores.get(sh.id, 0.0)
        
        # Check if stakeholder is dissenting (score below threshold)
        if sh_score < threshold:
            dissenting_stakeholders.append(sh.name)
            
            # Find the dissatisfied criteria (score < threshold)
            dissatisfied_criteria = []
            sh_indiv = individual_scores.get(sh.id, {})
            
            for pref in sh.preferences:
                crit = pref.criterion
                score = sh_indiv.get(crit, 0.0)
                if score < threshold:
                    dissatisfied_criteria.append(
                        f"'{crit}' (satisfaction: {round(score * 100, 1)}%)"
                    )
            
            if dissatisfied_criteria:
                explanation = f"Dissatisfied due to low satisfaction in: {', '.join(dissatisfied_criteria)}."
            else:
                explanation = f"Overall satisfaction is low ({round(sh_score * 100, 1)}%) across all preferences."
                
            explanations[sh.name] = explanation

    return {
        "dissenting_stakeholders": dissenting_stakeholders,
        "explanations": explanations
    }
