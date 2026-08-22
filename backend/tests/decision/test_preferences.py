import unittest
from backend.services.decision.models import Option, Preference, Stakeholder
from backend.services.decision.preference_engine import evaluate_preference, calculate_weighted_satisfaction

class TestPreferences(unittest.TestCase):
    def setUp(self):
        # Sample option for evaluation
        self.option_aws = Option(
            id="opt_aws",
            name="AWS Cloud hosting",
            attributes={
                "cost": 80000,
                "performance": 9.0,
                "scalability": 9.5,
                "provider": "Amazon Web Services",
                "features": ["autoscaling", "db_replication", "global_regions"]
            }
        )

    def test_evaluate_preference_exact(self):
        # Exact strategy
        pref1 = Preference(criterion="provider", value="Amazon Web Services", strategy="exact")
        pref2 = Preference(criterion="provider", value="Microsoft Azure", strategy="exact")
        self.assertEqual(evaluate_preference(self.option_aws, pref1), 1.0)
        self.assertEqual(evaluate_preference(self.option_aws, pref2), 0.0)

    def test_evaluate_preference_higher_is_better(self):
        # Target = 8.0, Option has 9.0 -> 1.0 (exceeds/meets target)
        pref_meet = Preference(criterion="performance", value=8.0, strategy="higher_is_better")
        self.assertEqual(evaluate_preference(self.option_aws, pref_meet), 1.0)

        # Target = 10.0, Option has 9.0 (no min_value) -> 9.0 / 10.0 = 0.9
        pref_below_ratio = Preference(criterion="performance", value=10.0, strategy="higher_is_better")
        self.assertAlmostEqual(evaluate_preference(self.option_aws, pref_below_ratio), 0.9)

        # Target = 10.0, Option has 9.0, min_value = 5.0 -> (9 - 5) / (10 - 5) = 4 / 5 = 0.8
        pref_below_interp = Preference(criterion="performance", value=10.0, strategy="higher_is_better", min_value=5.0)
        self.assertAlmostEqual(evaluate_preference(self.option_aws, pref_below_interp), 0.8)

    def test_evaluate_preference_lower_is_better(self):
        # Target = 90000, Option has 80000 -> 1.0 (cost is lower than target)
        pref_meet = Preference(criterion="cost", value=90000, strategy="lower_is_better")
        self.assertEqual(evaluate_preference(self.option_aws, pref_meet), 1.0)

        # Target = 60000, Option has 80000 (no max_value) -> 60000 / 80000 = 0.75
        pref_below_ratio = Preference(criterion="cost", value=60000, strategy="lower_is_better")
        self.assertAlmostEqual(evaluate_preference(self.option_aws, pref_below_ratio), 0.75)

        # Target = 50000, Option has 80000, max_value = 100000 -> 1 - (80000-50000)/(100000-50000) = 1 - 3/5 = 0.4
        pref_below_interp = Preference(criterion="cost", value=50000, strategy="lower_is_better", max_value=100000)
        self.assertAlmostEqual(evaluate_preference(self.option_aws, pref_below_interp), 0.4)

    def test_evaluate_preference_contains(self):
        # Substring/List containment check
        pref_list = Preference(criterion="features", value="autoscaling", strategy="contains")
        pref_list_fail = Preference(criterion="features", value="serverless", strategy="contains")
        pref_str = Preference(criterion="provider", value="Amazon", strategy="contains")
        
        self.assertEqual(evaluate_preference(self.option_aws, pref_list), 1.0)
        self.assertEqual(evaluate_preference(self.option_aws, pref_list_fail), 0.0)
        self.assertEqual(evaluate_preference(self.option_aws, pref_str), 1.0)

    def test_evaluate_preference_range(self):
        # Range checking
        pref_in = Preference(criterion="performance", value=8.0, strategy="range", min_value=7.0, max_value=9.5)
        pref_out = Preference(criterion="performance", value=8.0, strategy="range", min_value=9.2, max_value=9.8)
        
        self.assertEqual(evaluate_preference(self.option_aws, pref_in), 1.0)
        self.assertEqual(evaluate_preference(self.option_aws, pref_out), 0.0)

    def test_evaluate_preference_missing_attribute(self):
        # Attribute not present in Option
        pref = Preference(criterion="security_score", value=9.0, strategy="higher_is_better")
        self.assertEqual(evaluate_preference(self.option_aws, pref), 0.0)

    def test_calculate_weighted_satisfaction_equal_and_conflicting(self):
        # Stakeholder preferences setup
        cto = Stakeholder(
            id="cto",
            name="Chief Technology Officer",
            weight=10.0,
            preferences=[
                Preference(criterion="performance", value=10.0, weight=10.0, strategy="higher_is_better"), # 9/10 -> score 0.9
                Preference(criterion="scalability", value=10.0, weight=10.0, strategy="higher_is_better")  # 9.5/10 -> score 0.95
            ]
        )
        # CTO expected score = (0.9 * 10 + 0.95 * 10) / 20 = 0.925
        
        finance = Stakeholder(
            id="finance",
            name="Finance Lead",
            weight=5.0,
            preferences=[
                Preference(criterion="cost", value=50000, weight=10.0, strategy="lower_is_better", max_value=100000) # 1 - (80k-50k)/(50k) = 0.4
            ]
        )
        # Finance expected score = 0.4
        
        # Overall expected score = (0.925 * 10 + 0.4 * 5) / 15 = (9.25 + 2.0) / 15 = 11.25 / 15 = 0.75

        res = calculate_weighted_satisfaction(self.option_aws, [cto, finance])
        self.assertAlmostEqual(res["stakeholder_scores"]["cto"], 0.925)
        self.assertAlmostEqual(res["stakeholder_scores"]["finance"], 0.4)
        self.assertAlmostEqual(res["overall_score"], 0.75)

    def test_calculate_weighted_satisfaction_zero_weight_edge_cases(self):
        # Stakeholder weight = 0, preference weight = 0
        cto = Stakeholder(
            id="cto",
            name="CTO",
            weight=0.0,  # Stakeholder has weight 0
            preferences=[
                Preference(criterion="performance", value=10.0, weight=10.0, strategy="higher_is_better")  # score 0.9
            ]
        )
        finance = Stakeholder(
            id="finance",
            name="Finance",
            weight=5.0,
            preferences=[
                Preference(criterion="cost", value=80000, weight=0.0, strategy="lower_is_better"), # weight = 0
                Preference(criterion="scalability", value=10.0, weight=10.0, strategy="higher_is_better") # score 0.95, weight 10
            ]
        )
        # Finance expected score: cost is ignored because of weight 0, so score = 0.95 * 10 / 10 = 0.95
        # CTO expected score = 0.9, but stakeholder weight is 0.
        # Overall expected score = (0.95 * 5 + 0.9 * 0) / 5 = 0.95

        res = calculate_weighted_satisfaction(self.option_aws, [cto, finance])
        self.assertAlmostEqual(res["stakeholder_scores"]["cto"], 0.9)
        self.assertAlmostEqual(res["stakeholder_scores"]["finance"], 0.95)
        self.assertAlmostEqual(res["overall_score"], 0.95)

if __name__ == '__main__':
    unittest.main()
