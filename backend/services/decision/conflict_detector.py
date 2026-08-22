from typing import Any, Dict, List
from .models import Stakeholder, Constraint, Option
from .constraint_engine import validate_constraint

def detect_conflicts(
    stakeholders: List[Stakeholder],
    constraints: List[Constraint],
    options: List[Option]
) -> List[Dict[str, Any]]:
    """
    Analyzes preferences, constraints, and options to identify conflicts.
    
    Returns a list of conflict dicts in the following format:
    {
        "criterion": str,
        "stakeholders": List[str],
        "severity": str,  # LOW, MEDIUM, HIGH, CRITICAL
        "description": str
    }
    """
    conflicts = []

    # 1. Check if there are options, but none of them are feasible
    if options:
        any_feasible = False
        for opt in options:
            feasible = True
            for const in constraints:
                if const.type.upper() == "HARD":
                    res = validate_constraint(opt, const)
                    if not res["constraint_satisfied"]:
                        feasible = False
                        break
            if feasible:
                any_feasible = True
                break
        
        if not any_feasible:
            conflicts.append({
                "criterion": "multiple",
                "stakeholders": [sh.id for sh in stakeholders],
                "severity": "CRITICAL",
                "description": "No feasible option satisfies all hard constraints. Human intervention required."
            })

    # 2. Check for logically incompatible hard constraints on the same criterion
    # E.g. cost <= 50000 and cost >= 60000
    hard_constraints = [c for c in constraints if c.type.upper() == "HARD"]
    criterion_constraints: Dict[str, List[Constraint]] = {}
    for hc in hard_constraints:
        criterion_constraints.setdefault(hc.criterion, []).append(hc)

    for crit, cs in criterion_constraints.items():
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                c1, c2 = cs[i], cs[j]
                incompatible = False
                
                # Pairwise compatibility check
                op1, op2 = c1.operator.strip().lower(), c2.operator.strip().lower()
                try:
                    val1, val2 = float(c1.value), float(c2.value)
                    
                    if op1 == "<=" and op2 == ">=" and val1 < val2:
                        incompatible = True
                    elif op1 == ">=" and op2 == "<=" and val2 < val1:
                        incompatible = True
                    elif op1 == "<" and op2 == ">" and val1 <= val2:
                        incompatible = True
                    elif op1 == ">" and op2 == "<" and val2 <= val1:
                        incompatible = True
                    elif op1 in ("=", "==") and op2 in ("=", "==") and abs(val1 - val2) >= 1e-9:
                        incompatible = True
                    elif op1 in ("=", "==") and op2 == "!=" and abs(val1 - val2) < 1e-9:
                        incompatible = True
                    elif op2 in ("=", "==") and op1 == "!=" and abs(val1 - val2) < 1e-9:
                        incompatible = True
                        
                except (ValueError, TypeError):
                    # For non-numeric values
                    val1_str, val2_str = str(c1.value), str(c2.value)
                    if op1 in ("=", "==") and op2 in ("=", "==") and val1_str != val2_str:
                        incompatible = True
                    elif op1 in ("=", "==") and op2 == "!=" and val1_str == val2_str:
                        incompatible = True
                    elif op2 in ("=", "==") and op1 == "!=" and val1_str == val2_str:
                        incompatible = True

                if incompatible:
                    conflicts.append({
                        "criterion": crit,
                        "stakeholders": [],
                        "severity": "CRITICAL",
                        "description": f"Mutually exclusive hard constraints detected on '{crit}': {c1.operator} {c1.value} and {c2.operator} {c2.value}."
                    })

    # 3. Check for opposing preferred values and preference differences
    # E.g. Stakeholder A prefers low cost, Stakeholder B prefers high cost or higher performance
    crit_preferences: Dict[str, List[tuple]] = {}  # crit -> [(stakeholder_id, preference)]
    for sh in stakeholders:
        for pref in sh.preferences:
            if pref.weight > 0:
                crit_preferences.setdefault(pref.criterion, []).append((sh.id, pref))

    for crit, prefs in crit_preferences.items():
        for i in range(len(prefs)):
            for j in range(i + 1, len(prefs)):
                sh1_id, p1 = prefs[i]
                sh2_id, p2 = prefs[j]
                if sh1_id == sh2_id:
                    continue

                # Check if strategies are opposing (higher_is_better vs lower_is_better)
                s1, s2 = p1.strategy.lower() if p1.strategy else "exact", p2.strategy.lower() if p2.strategy else "exact"
                
                if (s1 == "higher_is_better" and s2 == "lower_is_better") or \
                   (s1 == "lower_is_better" and s2 == "higher_is_better"):
                    conflicts.append({
                        "criterion": crit,
                        "stakeholders": sorted([sh1_id, sh2_id]),
                        "severity": "HIGH",
                        "description": f"Opposing satisfaction directions for '{crit}': {sh1_id} preferred strategy is {s1} while {sh2_id} is {s2}."
                    })
                    continue

                # Check if exact values are opposing
                try:
                    v1, v2 = float(p1.value), float(p2.value)
                    # If exact targets differ significantly
                    if s1 == "exact" and s2 == "exact" and abs(v1 - v2) > 1e-9:
                        conflicts.append({
                            "criterion": crit,
                            "stakeholders": sorted([sh1_id, sh2_id]),
                            "severity": "MEDIUM",
                            "description": f"Opposing preferred target values for '{crit}': {sh1_id} prefers {v1} while {sh2_id} prefers {v2}."
                        })
                except (ValueError, TypeError):
                    v1_str, v2_str = str(p1.value).lower(), str(p2.value).lower()
                    if s1 == "exact" and s2 == "exact" and v1_str != v2_str:
                        conflicts.append({
                            "criterion": crit,
                            "stakeholders": sorted([sh1_id, sh2_id]),
                            "severity": "MEDIUM",
                            "description": f"Opposing preferred target values for '{crit}': {sh1_id} prefers '{p1.value}' while {sh2_id} prefers '{p2.value}'."
                        })

    # 4. Check for Budget / Performance trade-offs and Stakeholder Priority Differences
    # Find stakeholders who heavily prioritize cost vs those who heavily prioritize performance/scalability
    cost_keywords = {"cost", "price", "budget", "expense"}
    perf_keywords = {"performance", "speed", "scalability", "throughput", "quality"}

    cost_prioritizers = []
    perf_prioritizers = []

    for sh in stakeholders:
        for pref in sh.preferences:
            crit_lower = pref.criterion.lower()
            if pref.weight >= 7.0:
                if any(k in crit_lower for k in cost_keywords):
                    cost_prioritizers.append((sh.id, pref.criterion, pref.weight))
                elif any(k in crit_lower for k in perf_keywords):
                    perf_prioritizers.append((sh.id, pref.criterion, pref.weight))

    for c_sh, c_crit, c_w in cost_prioritizers:
        for p_sh, p_crit, p_w in perf_prioritizers:
            if c_sh != p_sh:
                # Add a high-level trade-off / priority conflict
                conflicts.append({
                    "criterion": f"{c_crit}/{p_crit}",
                    "stakeholders": sorted([c_sh, p_sh]),
                    "severity": "HIGH",
                    "description": f"{c_sh} prioritizes low {c_crit} (weight {c_w}) while {p_sh} prioritizes high {p_crit} (weight {p_w})."
                })

    # Deduplicate conflicts with the same description or key features
    unique_conflicts = []
    seen_descriptions = set()
    for conflict in conflicts:
        desc = conflict["description"]
        if desc not in seen_descriptions:
            seen_descriptions.add(desc)
            unique_conflicts.append(conflict)

    return unique_conflicts
