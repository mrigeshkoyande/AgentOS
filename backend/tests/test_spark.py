import unittest
import sys
import os
import json
import asyncio
from fastapi.testclient import TestClient

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app, get_db
from repositories.decision_repository import DecisionRepository
from services.decision.constraint_engine import ConstraintEngine
from services.decision.consensus_engine import ConsensusEngine
from services.negotiation.negotiation_engine import NegotiationEngine

class TestSparkWorkspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        
        # Populate session first
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO sessions (id, description, status) VALUES ('spark_sess_1', 'SPARK Virtual Office Session', 'draft')")
        conn.commit()
        conn.close()
        
        cls.repo = DecisionRepository()

    def test_agent_registry_endpoint(self):
        res = self.client.get("/api/agents")
        self.assertEqual(res.status_code, 200)
        agents = res.json()
        self.assertTrue(len(agents) >= 3)
        agent_ids = [a["id"] for a in agents]
        self.assertIn("agent-m", agent_ids)
        self.assertIn("agent-a", agent_ids)
        self.assertIn("agent-s", agent_ids)

    def test_task_submission_and_state_machine_flow(self):
        # Submit task
        payload = {
            "session_id": "spark_sess_1",
            "prompt": "Generate a marketing campaign brief and strategic branding plan."
        }
        res = self.client.post("/api/tasks", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("task_id", data)
        self.assertEqual(data["status"], "RECEIVED")
        
        task_id = data["task_id"]
        
        # Let's wait slightly or retrieve details
        res_details = self.client.get(f"/api/tasks/{task_id}")
        self.assertEqual(res_details.status_code, 200)
        t_data = res_details.json()
        self.assertEqual(t_data["prompt"], payload["prompt"])
        
        # Cancel task
        res_cancel = self.client.post(f"/api/tasks/{task_id}/cancel")
        self.assertEqual(res_cancel.status_code, 200)
        self.assertEqual(res_cancel.json()["status"], "success")
        
        res_details2 = self.client.get(f"/api/tasks/{task_id}")
        self.assertEqual(res_details2.json()["status"], "CANCELLED")

    def test_deterministic_constraint_engine(self):
        # Finance Constraint: cost <= 80000 (severity = hard)
        constraints = [
            {
                "criterion": "cost",
                "operator": "<=",
                "value": "80000",
                "severity": "hard"
            }
        ]
        
        # Option A: cost = 75000 (feasible)
        opt_a_attrs = {"cost": 75000}
        # Option B: cost = 90000 (infeasible)
        opt_b_attrs = {"cost": 90000}
        
        engine = ConstraintEngine()
        is_valid_a, violations_a = engine.validate_proposal(constraints, opt_a_attrs)
        is_valid_b, violations_b = engine.validate_proposal(constraints, opt_b_attrs)
        
        self.assertTrue(is_valid_a)
        self.assertFalse(is_valid_b)
        self.assertTrue(any("Hard constraint violation" in v for v in violations_b))

    def test_consensus_satisfaction_score(self):
        # Setup temporary decision structure
        decision = {
            "title": "Hosting Provider",
            "consensus_threshold": 0.7,
            "stakeholders": [
                {"id": "stk_finance", "name": "Finance", "role": "approver", "weight": 1.0},
                {"id": "stk_cto", "name": "CTO", "role": "driver", "weight": 1.5}
            ],
            "preferences": [
                {"stakeholder_id": "stk_finance", "criterion": "cost", "value": "low", "weight": 2.0},
                {"stakeholder_id": "stk_cto", "criterion": "performance", "value": "high", "weight": 3.0}
            ],
            "constraints": [
                {"stakeholder_id": "stk_finance", "criterion": "cost", "operator": "<=", "value": "80000", "severity": "hard"}
            ]
        }
        
        engine = ConsensusEngine()
        
        # Option A attributes (Feasible, low cost, mid performance)
        opt_a = {"cost": 75000, "performance": 7}
        res_a = engine.evaluate_proposal(decision, opt_a)
        self.assertTrue(res_a["is_feasible"])
        self.assertTrue(res_a["consensus_score"] > 0.0)
        
        # Option B attributes (Infeasible, violates hard constraint)
        opt_b = {"cost": 90000, "performance": 10}
        res_b = engine.evaluate_proposal(decision, opt_b)
        self.assertFalse(res_b["is_feasible"])
        self.assertEqual(res_b["consensus_score"], 0.0)

    def test_complete_negotiation_workflow(self):
        # 1. Create Decision
        dec_payload = {
            "session_id": "spark_sess_1",
            "title": "Cloud System Upgrade Strategy",
            "description": "Choose best cloud server architecture.",
            "strategy": "consensus",
            "consensus_threshold": 0.7,
            "max_rounds": 3,
            "compromise_allowed": True,
            "approval_required": True
        }
        res = self.client.post("/api/decisions", json=dec_payload)
        self.assertEqual(res.status_code, 201)
        dec_id = res.json()["id"]
        
        # 2. Add Stakeholder
        stk_res = self.client.post(f"/api/decisions/{dec_id}/stakeholders", json={
            "name": "Finance Department",
            "role": "approver",
            "type": "agent",
            "weight": 1.0,
            "approval_required": True
        })
        self.assertEqual(stk_res.status_code, 201)
        stk_id = stk_res.json()["id"]
        
        # 3. Add Preference
        pref_res = self.client.post(f"/api/decisions/{dec_id}/preferences", json={
            "stakeholder_id": stk_id,
            "criterion": "cost",
            "value": "low",
            "weight": 1.5,
            "priority": "high",
            "description": "Minimize recurring server fees"
        })
        self.assertEqual(pref_res.status_code, 201)
        
        # 4. Add Constraint (Hard constraint)
        const_res = self.client.post(f"/api/decisions/{dec_id}/constraints", json={
            "stakeholder_id": stk_id,
            "criterion": "cost",
            "operator": "<=",
            "value": "80000",
            "severity": "hard"
        })
        self.assertEqual(const_res.status_code, 201)
        
        # 5. Add Options (Option 1: cost ₹75000, Option 2: cost ₹90000)
        self.client.post(f"/api/decisions/{dec_id}/options", json={
            "name": "AWS Fargate Serverless Cluster",
            "description": "Cost is ₹75,000 monthly, performance tier is 8."
        })
        self.client.post(f"/api/decisions/{dec_id}/options", json={
            "name": "Dedicated Kubernetes Host",
            "description": "Cost is ₹90,000 monthly, high performance tier."
        })
        
        # 6. Execute Negotiation synchronously using NegotiationEngine directly
        engine = NegotiationEngine()
        outcome = asyncio.run(engine.execute_negotiation(dec_id))
        self.assertIn(outcome["status"], ["AWAITING_APPROVAL", "COMPLETED"])
        
        # Option 1 (AWS Fargate) should be selected as Option 2 violates the cost limit of 80000
        self.assertEqual(outcome["selected_option"], "AWS Fargate Serverless Cluster")

    def test_simulation_what_if_scenario(self):
        # Create decision
        dec_payload = {
            "session_id": "spark_sess_1",
            "title": "Cloud Simulation Decision",
            "strategy": "consensus",
            "consensus_threshold": 0.8,
            "max_rounds": 3,
            "compromise_allowed": True,
            "approval_required": True
        }
        res = self.client.post("/api/decisions", json=dec_payload)
        dec_id = res.json()["id"]
        
        stk_id = self.client.post(f"/api/decisions/{dec_id}/stakeholders", json={
            "name": "Finance",
            "role": "approver",
            "weight": 1.0
        }).json()["id"]
        
        self.client.post(f"/api/decisions/{dec_id}/options", json={"name": "Option A - Cost is 75000"})
        self.client.post(f"/api/decisions/{dec_id}/options", json={"name": "Option B - Cost is 90000"})
        
        # Run simulation with override constraints (make budget 100k, so both are feasible)
        sim_payload = {
            "preferences": [{"stakeholder_id": stk_id, "criterion": "cost", "value": "low"}],
            "constraints": [{"stakeholder_id": stk_id, "criterion": "cost", "operator": "<=", "value": "100000", "severity": "hard"}],
            "options": [{"name": "Option B - Cost is 90000"}]
        }
        res_sim = self.client.post(f"/api/decisions/{dec_id}/simulate", json=sim_payload)
        self.assertEqual(res_sim.status_code, 200)
        sim_data = res_sim.json()
        self.assertEqual(sim_data["outcome"]["selected_option"], "Option B - Cost is 90000")

if __name__ == "__main__":
    unittest.main()
