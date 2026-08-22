import unittest
from backend.services.decision.models import Option, Constraint, Stakeholder, Preference
from backend.services.decision.consensus_engine import calculate_consensus
from backend.services.decision.ranking_engine import rank_options
from backend.services.decision.dissent_engine import analyze_dissent
from backend.services.decision.tradeoff_engine import calculate_tradeoffs
from backend.services.decision.sensitivity_engine import run_sensitivity_analysis

class TestConsensus(unittest.TestCase):
    def setUp(self):
        # CTO prefers performance (higher is better, weight 10)
        # Finance prefers lower cost (lower is better, weight 10)
        self.stakeholders = [
            Stakeholder(
                id="cto",
                name="CTO",
                weight=1.0,
                preferences=[
                    Preference(criterion="performance", value=10.0, weight=10.0, strategy="higher_is_better")
                ]
            ),
            Stakeholder(
                id="finance",
                name="Finance",
                weight=1.0,
                preferences=[
                    Preference(criterion="cost", value=50000, weight=10.0, strategy="lower_is_better", max_value=100000)
                ]
            )
        ]
        
        # Hard constraint budget <= 100k
        # Soft constraint budget <= 80k (penalty 0.1)
        self.constraints = [
            Constraint(criterion="cost", operator="<=", value=100000, type="HARD"),
            Constraint(criterion="cost", operator="<=", value=80000, type="SOFT", penalty=0.1)
        ]

        # Options:
        # Option A: cost = 75k, performance = 7.0 -> feasible, satisfies soft constraint!
        # Option B: cost = 90k, performance = 10.0 -> feasible, violates soft constraint!
        # Option C: cost = 120k, performance = 10.0 -> infeasible!
        self.opt_a = Option(id="opt_a", name="Option A", attributes={"cost": 75000, "performance": 7.0})
        self.opt_b = Option(id="opt_b", name="Option B", attributes={"cost": 90000, "performance": 10.0})
        self.opt_c = Option(id="opt_c", name="Option C", attributes={"cost": 120000, "performance": 10.0})
        
        self.options = [self.opt_a, self.opt_b, self.opt_c]

    def test_consensus_calculation(self):
        consensus_res = calculate_consensus(self.options, self.stakeholders, self.constraints)
        opts = consensus_res["options"]
        
        # Option C must be infeasible
        self.assertEqual(opts["opt_c"]["status"], "infeasible")
        self.assertEqual(opts["opt_c"]["consensus_score"], 0.0)

        # Option A details:
        # CTO performance score: 7.0/10.0 = 0.7
        # Finance cost score: cost is 75k <= 80k soft, wait! Cost score is evaluated relative to target (50k) and max_value (100k):
        # 1 - (75000 - 50000) / (100000 - 50000) = 1 - 25000/50000 = 0.5
        # Overall score = (0.7 + 0.5) / 2 = 0.6
        # Penalty = 0.0 (satisfies cost <= 80000 soft constraint)
        # Penalized score = 0.6
        # Std dev of [0.7, 0.5] -> Mean = 0.6, Var = ((0.7-0.6)^2 + (0.5-0.6)^2)/2 = 0.01 -> std = 0.1
        # Consensus score = 0.6 * (1 - 0.1) = 0.6 * 0.9 = 0.54
        self.assertEqual(opts["opt_a"]["status"], "feasible")
        self.assertAlmostEqual(opts["opt_a"]["consensus_score"], 0.54, places=4)

        # Option B details:
        # CTO performance score: 10.0/10.0 = 1.0
        # Finance cost score: 1 - (90000 - 50000) / (100000 - 50000) = 1 - 40000/50000 = 0.2
        # Overall score = (1.0 + 0.2) / 2 = 0.6
        # Penalty = 0.1 (violates cost <= 80000 soft constraint)
        # Penalized score = 0.6 - 0.1 = 0.5
        # Std dev of [1.0, 0.2] -> Mean = 0.6, Var = ((1.0-0.6)^2 + (0.2-0.6)^2)/2 = (0.16 + 0.16)/2 = 0.16 -> std = 0.4
        # Consensus score = 0.5 * (1 - 0.4) = 0.5 * 0.6 = 0.3
        self.assertEqual(opts["opt_b"]["status"], "feasible")
        self.assertAlmostEqual(opts["opt_b"]["consensus_score"], 0.3, places=4)

    def test_ranking_and_tie_breaker(self):
        consensus_res = calculate_consensus(self.options, self.stakeholders, self.constraints)
        ranking_res = rank_options(self.options, consensus_res)
        
        self.assertEqual(ranking_res["status"], "SUCCESS")
        self.assertEqual(len(ranking_res["ranking"]), 2) # Only feasible ranked
        
        # Option A should be rank 1 (score 0.54 vs 0.3)
        self.assertEqual(ranking_res["ranking"][0]["option_id"], "opt_a")
        self.assertEqual(ranking_res["ranking"][0]["rank"], 1)
        self.assertEqual(ranking_res["ranking"][1]["option_id"], "opt_b")
        self.assertEqual(ranking_res["ranking"][1]["rank"], 2)

    def test_tie_breaker_logic(self):
        # Two options with identical consensus_score
        # Opt X: CTO satisfaction 0.6, Finance satisfaction 0.6 -> Mean = 0.6, std = 0.0 -> consensus = 0.6
        # Opt Y: CTO satisfaction 0.8, Finance satisfaction 0.4 -> Mean = 0.6, std = 0.2 -> consensus = 0.6 * 0.8 = 0.48
        # Let's adjust Opt Y attributes so consensus score evaluates exactly same as X (e.g. 0.6) but different std.
        # Wait, if we force the consensus score to be identical:
        # Let's say Opt X and Opt Y have identical consensus score = 0.6.
        # But Opt X has std = 0.0, Opt Y has std = 0.1.
        # The ranking engine should prioritize Opt X (lowest std dev).
        # Let's construct a consensus results object directly to test this tie-breaker cleanly.
        mock_consensus_results = {
            "options": {
                "opt_y": {
                    "option_id": "opt_y",
                    "option_name": "Option Y",
                    "status": "feasible",
                    "overall_score": 0.6,
                    "penalized_score": 0.6,
                    "consensus_score": 0.6,
                    "stakeholder_scores": {"cto": 0.8, "finance": 0.4},
                    "violated_soft_constraints": []
                },
                "opt_x": {
                    "option_id": "opt_x",
                    "option_name": "Option X",
                    "status": "feasible",
                    "overall_score": 0.6,
                    "penalized_score": 0.6,
                    "consensus_score": 0.6,
                    "stakeholder_scores": {"cto": 0.6, "finance": 0.6},
                    "violated_soft_constraints": []
                }
            }
        }
        options = [
            Option(id="opt_y", name="Option Y", attributes={}),
            Option(id="opt_x", name="Option X", attributes={})
        ]
        
        ranking_res = rank_options(options, mock_consensus_results)
        # Option X has lower std dev (0.0 < 0.2), so it must be ranked first!
        self.assertEqual(ranking_res["ranking"][0]["option_id"], "opt_x")

    def test_dissent_analysis(self):
        consensus_res = calculate_consensus(self.options, self.stakeholders, self.constraints)
        
        # Under Option B, Finance has score 0.2 (< 0.7 threshold)
        dissent_res = analyze_dissent("opt_b", consensus_res, self.stakeholders, threshold=0.7)
        self.assertIn("Finance", dissent_res["dissenting_stakeholders"])
        self.assertNotIn("CTO", dissent_res["dissenting_stakeholders"])
        
        # Explanation check
        self.assertIn("cost", dissent_res["explanations"]["Finance"])

    def test_tradeoff_calculation(self):
        # Compare Option A and Option B
        # Option A: cost 75k, performance 7.0
        # Option B: cost 90k, performance 10.0
        # Option A is lower cost, Option B is higher performance
        tradeoffs = calculate_tradeoffs(self.opt_a, [self.opt_b], self.stakeholders)
        self.assertEqual(len(tradeoffs), 1)
        self.assertIn("Better Cost", tradeoffs[0]["advantage"])
        self.assertIn("Worse Performance", tradeoffs[0]["disadvantage"])

    def test_sensitivity_analysis(self):
        # Vary CTO performance preference weight
        res = run_sensitivity_analysis(self.options, self.stakeholders, self.constraints, "cto", "performance", steps=3)
        self.assertEqual(res["stakeholder_id"], "cto")
        self.assertEqual(len(res["sensitivity_steps"]), 3)

if __name__ == '__main__':
    unittest.main()
