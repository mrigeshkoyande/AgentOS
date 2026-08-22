import unittest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to sys.path so we can import modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app, get_db

class TestDecisionIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        
        # Create a mock session first so that decision session references are valid
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO sessions (id, description, status) VALUES ('test_sess_1', 'Test Session', 'draft')")
        conn.commit()
        conn.close()

    def test_complete_decision_lifecycle(self):
        # 1. Create decision
        payload = {
            "session_id": "test_sess_1",
            "title": "Test Upgrade Choice",
            "description": "Decide on architectural upgrade path",
            "strategy": "consensus",
            "consensus_threshold": 0.8,
            "max_rounds": 3,
            "compromise_allowed": True,
            "approval_required": True
        }
        res = self.client.post("/api/decisions", json=payload)
        self.assertEqual(res.status_code, 201)
        dec_id = res.json()["id"]
        self.assertTrue(dec_id.startswith("dec_"))

        # 2. Add stakeholder (approver)
        stk_payload = {
            "name": "CTO Agent",
            "role": "approver",
            "type": "agent",
            "weight": 1.5,
            "approval_required": True
        }
        res = self.client.post(f"/api/decisions/{dec_id}/stakeholders", json=stk_payload)
        self.assertEqual(res.status_code, 201)
        stk_id = res.json()["id"]
        self.assertTrue(stk_id.startswith("stk_"))

        # 3. Add preference
        pref_payload = {
            "stakeholder_id": stk_id,
            "criterion": "cost",
            "value": "low",
            "weight": 1.2,
            "priority": "high",
            "description": "Cost must be kept under budget"
        }
        res = self.client.post(f"/api/decisions/{dec_id}/preferences", json=pref_payload)
        self.assertEqual(res.status_code, 201)
        pref_id = res.json()["id"]
        self.assertTrue(pref_id.startswith("pref_"))

        # 4. Add constraint
        const_payload = {
            "stakeholder_id": stk_id,
            "criterion": "duration",
            "operator": "<=",
            "value": "30 days",
            "severity": "hard"
        }
        res = self.client.post(f"/api/decisions/{dec_id}/constraints", json=const_payload)
        self.assertEqual(res.status_code, 201)
        const_id = res.json()["id"]
        self.assertTrue(const_id.startswith("const_"))

        # 5. Add options
        opt_payload = {
            "name": "Option 1: PostgreSQL migration",
            "description": "Migrate SQLite database to PostgreSQL"
        }
        res = self.client.post(f"/api/decisions/{dec_id}/options", json=opt_payload)
        self.assertEqual(res.status_code, 201)
        opt_id = res.json()["id"]
        self.assertTrue(opt_id.startswith("opt_"))

        # 6. Retrieve complete decision state
        res = self.client.get(f"/api/decisions/{dec_id}")
        self.assertEqual(res.status_code, 200)
        dec_data = res.json()
        self.assertEqual(dec_data["title"], "Test Upgrade Choice")
        self.assertEqual(len(dec_data["stakeholders"]), 1)
        self.assertEqual(len(dec_data["options"]), 1)

        # 7. Start decision (transitions to RUNNING -> NEGOTIATING -> AWAITING_APPROVAL)
        res = self.client.post(f"/api/decisions/{dec_id}/start")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")

        # 8. Check status
        res = self.client.get(f"/api/decisions/{dec_id}/status")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "AWAITING_APPROVAL")

        # 9. Verify invalid transitions fail
        res = self.client.patch(f"/api/decisions/{dec_id}", json={"status": "COMPLETED"})
        self.assertEqual(res.status_code, 400) # Invalid state transition (AWAITING_APPROVAL -> COMPLETED directly is invalid)

        # 10. Simulate what-if scenario
        sim_payload = {
            "preferences": [{
                "stakeholder_id": stk_id,
                "criterion": "cost",
                "value": "high",
                "weight": 2.0
            }],
            "options": [{
                "name": "Option 2: Cloud SQL Spanner",
                "description": "High performance option"
            }]
        }
        res = self.client.post(f"/api/decisions/{dec_id}/simulate", json=sim_payload)
        self.assertEqual(res.status_code, 200)
        sim_data = res.json()
        self.assertEqual(sim_data["outcome"]["selected_option"], "Option 2: Cloud SQL Spanner")

        # 11. Approve decision
        approve_payload = {
            "stakeholder_id": stk_id,
            "action": "approve",
            "reason": "Meets criteria perfectly"
        }
        res = self.client.post(f"/api/decisions/{dec_id}/approve", json=approve_payload)
        self.assertEqual(res.status_code, 200)

        # Verify outcome
        res = self.client.get(f"/api/decisions/{dec_id}/result")
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(res.json())

        # 12. Check historical decisions list
        res = self.client.get("/api/decisions/history")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.json()) > 0)

if __name__ == "__main__":
    unittest.main()
