"""
Unit and Integration Tests for Braintrust Trace Review Studio.
Tests service queries, multi-turn reconstruction, evaluations parsing,
FastAPI REST routes, and feedback syncing.
"""

import unittest
from fastapi.testclient import TestClient
from src.review_studio.server import app
from src.review_studio.service import BraintrustService


class TestTraceReviewStudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = BraintrustService()
        cls.client = TestClient(app)

    def test_01_get_current_user(self):
        """Verify current Braintrust user details are correctly resolved."""
        user = self.service.get_current_user()
        self.assertIsInstance(user, dict)
        self.assertIn("name", user)
        self.assertIn("email", user)
        self.assertIn("project", user)
        self.assertEqual(user["project"], "meridian-pay-support")
        print(f"\n[Test] Authenticated user: {user['name']} ({user['email']})")

    def test_02_list_traces(self):
        """Verify traces can be fetched and filtered with assignment stats."""
        res = self.service.list_traces(assignee_filter="all", limit=10)
        self.assertIn("traces", res)
        self.assertIn("stats", res)
        self.assertGreater(len(res["traces"]), 0)

        stats = res["stats"]
        self.assertIn("assigned_to_me", stats)
        self.assertIn("unassigned", stats)
        self.assertIn("failing_evals", stats)
        print(f"[Test] Traces fetched: {len(res['traces'])}, Assigned to me: {stats['assigned_to_me']}, Unassigned: {stats['unassigned']}")

    def test_03_get_trace_details_and_turns(self):
        """Verify trace details, multi-turn steps, reasoning, and system evaluations."""
        # Get first trace
        traces_data = self.service.list_traces(assignee_filter="all", limit=5)
        self.assertGreater(len(traces_data["traces"]), 0)
        sample_id = traces_data["traces"][0]["id"]

        detail = self.service.get_trace_details(sample_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["id"], sample_id)
        self.assertIn("turns", detail)
        self.assertIn("system_evaluations", detail)
        self.assertIn("eval_cards", detail["system_evaluations"])
        self.assertGreater(len(detail["turns"]), 0)

        first_turn = detail["turns"][0]
        self.assertIn("user_message", first_turn)
        self.assertIn("reasoning", first_turn)
        self.assertIn("tools", first_turn)
        print(f"[Test] Trace {sample_id[:8]} has {len(detail['turns'])} turns and {len(detail['system_evaluations']['eval_cards'])} evaluation scorecards")

    def test_04_api_endpoints(self):
        """Verify FastAPI REST endpoints respond with valid JSON."""
        # 1. /api/me
        r = self.client.get("/api/me")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("name", data)

        # 2. /api/traces
        r = self.client.get("/api/traces?assignee=all&limit=5")
        self.assertEqual(r.status_code, 200)
        traces_res = r.json()
        self.assertIn("traces", traces_res)
        self.assertGreater(len(traces_res["traces"]), 0)

        first_id = traces_res["traces"][0]["id"]

        # 3. /api/traces/{trace_id}
        r = self.client.get(f"/api/traces/{first_id}")
        self.assertEqual(r.status_code, 200)
        detail_res = r.json()
        self.assertIn("turns", detail_res)
        self.assertIn("system_evaluations", detail_res)

        # 4. /api/stats
        r = self.client.get("/api/stats")
        self.assertEqual(r.status_code, 200)

        # 5. / (index.html)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Braintrust Trace Review Studio", r.text)
        print("[Test] All REST endpoints and static HTML verified successfully.")

    def test_05_create_eval_from_feedback(self):
        """Verify creating an evaluation case directly from a story and its feedback."""
        traces_res = self.service.list_traces(assignee_filter="all", limit=5)
        sample_id = traces_res["traces"][0]["id"]

        r = self.client.post(f"/api/traces/{sample_id}/create-eval")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("case", data)
        case = data["case"]
        self.assertTrue(case["id"].startswith("MP-FEEDBACK-"))
        self.assertIn("input", case)
        self.assertIn("expected", case)
        self.assertIn("metadata", case)
        print(f"[Test] Successfully created eval case {case['id']} from trace {sample_id[:8]}")

    def test_06_prompt_compare(self):
        """Verify prompt comparison, texts, changelog, and unified diff."""
        r = self.client.get("/api/prompts/compare")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("prompts", data)
        self.assertIn("v2_concise", data["prompts"])
        self.assertIn("v3_fixed", data["prompts"])
        self.assertIn("diff", data)
        self.assertIn("fix_highlight", data)
        print("[Test] Prompt comparison and diff retrieved successfully.")

    def test_07_pre_deployment_eval(self):
        """Verify testing candidate prompt vs fixed prompt against dataset with zero-tolerance safety assertions."""
        payload = {
            "prompt_candidate": "v2",
            "prompt_fixed": "v3",
        }
        r = self.client.post("/api/eval/pre-deployment-test", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("candidate", data)
        self.assertIn("fixed", data)
        self.assertIn("deployment_decision", data)
        self.assertEqual(data["deployment_decision"], "APPROVED")
        self.assertFalse(data["candidate"]["passed"])
        self.assertTrue(data["fixed"]["passed"])
        self.assertEqual(data["candidate"]["scores"]["no_unauthorized_action"], 0.0)
        self.assertEqual(data["fixed"]["scores"]["no_unauthorized_action"], 1.0)
        print(f"[Test] Pre-deployment evaluation passed: Candidate safety=0.0 -> Fixed safety=1.0. Decision: {data['deployment_decision']}")


if __name__ == "__main__":
    unittest.main()

