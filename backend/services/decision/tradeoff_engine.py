from typing import Any, Dict, List, Set
from .models import Option, Stakeholder

def get_criterion_strategy(stakeholders: List[Stakeholder]) -> Dict[str, str]:
    """
    Infers the evaluation strategy for each criterion from stakeholder preferences.
    Defaults to 'higher_is_better' if not specified.
    """
    strategies = {}
    cost_keywords = {"cost", "price", "budget", "latency", "expense"}
    
    for sh in stakeholders:
        for pref in sh.preferences:
            crit = pref.criterion
            if pref.strategy:
                strategies[crit] = pref.strategy.lower()
            elif crit.lower() in cost_keywords:
                strategies[crit] = "lower_is_better"
            else:
                strategies[crit] = "higher_is_better"
                
    return strategies


def get_stakeholders_for_criteria(stakeholders: List[Stakeholder], criteria: Set[str]) -> List[str]:
    """Finds all stakeholders who care about the given set of criteria."""
    affected = set()
    for sh in stakeholders:
        for pref in sh.preferences:
            if pref.criterion in criteria and pref.weight > 0:
                affected.add(sh.name)
    return sorted(list(affected))


def calculate_tradeoffs(
    selected_option: Option,
    alternative_options: List[Option],
    stakeholders: List[Stakeholder]
) -> List[Dict[str, Any]]:
    """
    Generates structured trade-offs comparing the selected option with other options.
    
    Returns a list of trade-off dicts:
    {
        "advantage": str,
        "disadvantage": str,
        "affected_stakeholders": List[str]
    }
    """
    tradeoffs = []
    strategies = get_criterion_strategy(stakeholders)

    for alt in alternative_options:
        if alt.id == selected_option.id:
            continue

        advantages = []
        disadvantages = []
        affected_criteria = set()

        # Compare attributes
        all_criteria = set(selected_option.attributes.keys()) | set(alt.attributes.keys())

        for crit in all_criteria:
            sel_val = selected_option.attributes.get(crit)
            alt_val = alt.attributes.get(crit)

            if sel_val is None or alt_val is None:
                continue

            if isinstance(sel_val, (int, float)) and isinstance(alt_val, (int, float)):
                if abs(sel_val - alt_val) < 1e-9:
                    continue

                strategy = strategies.get(crit, "higher_is_better")
                is_sel_better = False

                if strategy == "higher_is_better":
                    is_sel_better = sel_val > alt_val
                elif strategy == "lower_is_better":
                    is_sel_better = sel_val < alt_val

                # Format labels nicely
                crit_label = crit.replace("_", " ").title()
                if is_sel_better:
                    advantages.append(f"Better {crit_label} ({sel_val} vs {alt_val})")
                else:
                    disadvantages.append(f"Worse {crit_label} ({sel_val} vs {alt_val})")
                
                affected_criteria.add(crit)

        # Pair advantages and disadvantages to represent a trade-off
        if advantages and disadvantages:
            affected_shs = get_stakeholders_for_criteria(stakeholders, affected_criteria)
            # Create a trade-off summary for this alternative
            tradeoffs.append({
                "advantage": ", ".join(advantages) + f" compared to {alt.name}",
                "disadvantage": ", ".join(disadvantages) + f" compared to {alt.name}",
                "affected_stakeholders": affected_shs
            })

    return tradeoffs
