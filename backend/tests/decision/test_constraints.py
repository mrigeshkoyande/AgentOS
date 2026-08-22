import unittest
from backend.services.decision.models import Option, Constraint, Stakeholder, Preference
from backend.services.decision.constraint_engine import validate_constraint, validate_option_constraints
from backend.services.decision.consensus_engine import calculate_consensus

class TestConstraints(unittest.TestCase):
    def setUp(self):
        # AWS option has cost = 90000, performance = 9.5
        self.option_aws = Option(
            id="opt_aws",
            name="AWS",
            attributes={
                "cost": 90000,
                "performance": 9.5
            }
        )

    def test_validate_hard_constraint_success(self):
        constraint = Constraint(criterion="cost", operator="<=", value=100000, type="HARD")
        res = validate_constraint(self.option_aws, constraint)
        self.assertTrue(res["constraint_satisfied"])
        self.assertEqual(res["option_status"], "feasible")

    def test_validate_hard_constraint_violation(self):
        constraint = Constraint(criterion="cost", operator="<=", value=80000, type="HARD")
        res = validate_constraint(self.option_aws, constraint)
        self.assertFalse(res["constraint_satisfied"])
        self.assertEqual(res["option_status"], "infeasible")

    def test_validate_soft_constraint_violation_with_penalty(self):
        constraint = Constraint(criterion="cost", operator="<=", value=80000, type="SOFT", penalty=0.15)
        res = validate_constraint(self.option_aws, constraint)
        self.assertFalse(res["constraint_satisfied"])
        # Soft constraint violation leaves option status as feasible!
        self.assertEqual(res["option_status"], "feasible")

    def test_option_multiple_constraints(self):
        c1 = Constraint(criterion="cost", operator="<=", value=100000, type="HARD")
        c2 = Constraint(criterion="performance", operator=">=", value=9.0, type="HARD")
        c3 = Constraint(criterion="cost", operator="<=", value=80000, type="SOFT", penalty=0.2) # violated

        status, satisfied, violated, penalty = validate_option_constraints(self.option_aws, [c1, c2, c3])
        self.assertEqual(status, "feasible")
        self.assertEqual(len(satisfied), 2)
        self.assertEqual(len(violated), 1)
        self.assertEqual(penalty, 0.2)

    def test_hard_constraint_override_preference(self):
        # Critical test: a high preference score must NEVER override a hard constraint violation.
        # Even if the CTO gives AWS 10/10 for performance, if budget is strictly <= 80k, it must be infeasible.
        cto = Stakeholder(
            id="cto",
            name="CTO",
            weight=10.0,
            preferences=[
                Preference(criterion="performance", value=9.0, weight=10.0, strategy="higher_is_better")
            ]
        )
        
        # Hard constraint budget <= 80k, option cost = 90k
        budget_constraint = Constraint(criterion="cost", operator="<=", value=80000, type="HARD")
        
        consensus_res = calculate_consensus([self.option_aws], [cto], [budget_constraint])
        aws_res = consensus_res["options"]["opt_aws"]
        
        # Satisfaction is computed, but overall status is INFEASIBLE and consensus score is 0.0
        self.assertEqual(aws_res["status"], "infeasible")
        self.assertEqual(aws_res["consensus_score"], 0.0)

if __name__ == '__main__':
    unittest.main()
