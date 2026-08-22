import unittest
from backend.services.decision.models import Option, Constraint, Stakeholder, Preference
from backend.services.decision.conflict_detector import detect_conflicts

class TestConflicts(unittest.TestCase):
    def test_incompatible_hard_constraints(self):
        # Budget <= 50k and Budget >= 60k is incompatible
        c1 = Constraint(criterion="budget", operator="<=", value=50000, type="HARD")
        c2 = Constraint(criterion="budget", operator=">=", value=60000, type="HARD")
        
        conflicts = detect_conflicts([], [c1, c2], [])
        self.assertTrue(any(c["severity"] == "CRITICAL" and "Mutually exclusive" in c["description"] for c in conflicts))

    def test_opposing_preference_strategies(self):
        # CTO prefers higher cost (e.g. for premium features/support), Finance prefers lower cost
        cto = Stakeholder(
            id="cto",
            name="CTO",
            preferences=[
                Preference(criterion="cost", value=100000, weight=5.0, strategy="higher_is_better")
            ]
        )
        finance = Stakeholder(
            id="finance",
            name="Finance",
            preferences=[
                Preference(criterion="cost", value=50000, weight=10.0, strategy="lower_is_better")
            ]
        )
        
        conflicts = detect_conflicts([cto, finance], [], [])
        self.assertTrue(any(c["severity"] == "HIGH" and "Opposing satisfaction directions" in c["description"] for c in conflicts))

    def test_budget_performance_priority_conflict(self):
        # Finance places high priority on cost, CTO places high priority on performance
        finance = Stakeholder(
            id="finance",
            name="Finance",
            preferences=[
                Preference(criterion="cost", value=50000, weight=8.0, strategy="lower_is_better")
            ]
        )
        cto = Stakeholder(
            id="cto",
            name="CTO",
            preferences=[
                Preference(criterion="performance", value=10.0, weight=9.0, strategy="higher_is_better")
            ]
        )
        
        conflicts = detect_conflicts([finance, cto], [], [])
        self.assertTrue(any(c["severity"] == "HIGH" and "prioritizes" in c["description"] for c in conflicts))

    def test_no_feasible_option_escalation(self):
        # Option A: cost = 90k
        # Option B: cost = 85k
        # Hard constraint: budget <= 50k
        opt_a = Option(id="opt_a", name="A", attributes={"cost": 90000})
        opt_b = Option(id="opt_b", name="B", attributes={"cost": 85000})
        
        c = Constraint(criterion="cost", operator="<=", value=50000, type="HARD")
        
        cto = Stakeholder(id="cto", name="CTO", preferences=[])
        
        conflicts = detect_conflicts([cto], [c], [opt_a, opt_b])
        self.assertTrue(any(
            c["severity"] == "CRITICAL" and "No feasible option satisfies all hard constraints" in c["description"]
            for c in conflicts
        ))

if __name__ == '__main__':
    unittest.main()
