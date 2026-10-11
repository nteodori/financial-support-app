"""
Unit and Integration Tests for Meridian Pay Financial Support App Web Portal.
Tests portal endpoints, account views, live agent execution, KB runbooks, and routing.
"""

import unittest
from fastapi.testclient import TestClient
from src.review_studio.server import app


class TestFinancialSupportApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_portal_root_serves_html(self):
        """Verify GET / serves Meridian Pay portal HTML."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Meridian Pay", resp.text)
        self.assertIn("Corporate Card", resp.text)
        self.assertIn("chat-messages-container", resp.text)

    def test_02_studio_route_serves_html(self):
        """Verify GET /studio serves Trace Review Studio HTML."""
        resp = self.client.get("/studio")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Trace Review Studio", resp.text)

    def test_03_get_accounts_list(self):
        """Verify GET /api/app/accounts returns 30 commercial accounts."""
        resp = self.client.get("/api/app/accounts")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("accounts", data)
        self.assertGreaterEqual(len(data["accounts"]), 30)
        first = data["accounts"][0]
        self.assertEqual(first["account_id"], "ACC-0001")
        self.assertEqual(first["company_name"], "Acme Cloud Inc")

    def test_04_get_account_details(self):
        """Verify GET /api/app/accounts/ACC-0001 returns transactions and financial health."""
        resp = self.client.get("/api/app/accounts/ACC-0001")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["account_id"], "ACC-0001")
        self.assertIn("credit_limit", data)
        self.assertIn("current_balance", data)
        self.assertIn("transactions", data)
        self.assertGreater(len(data["transactions"]), 0)

    def test_05_get_kb_document(self):
        """Verify GET /api/app/kb/doc retrieves runbook documentation."""
        resp = self.client.get("/api/app/kb/doc", params={"path": "data/kb/policy/dispute-handling.md"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("content", data)
        self.assertIn("Dispute Handling", data["content"])

    def test_06_agent_live_execution(self):
        """Verify POST /api/app/agent/run executes support agent and returns trajectory."""
        payload = {
            "ticket": "My physical card was bent in my wallet and the chip fell out. We need a replacement card ASAP.",
            "account_id": "ACC-0001",
            "channel": "web_chat",
            "prompt_version": "v1"
        }
        resp = self.client.post("/api/app/agent/run", json=payload)
        self.assertEqual(resp.status_code, 200)
        result = resp.json()
        self.assertIn("reply", result)
        self.assertIn("tool_trajectory", result)
        self.assertIn("actions", result)
        self.assertIn("replace_card", result["actions"])
        self.assertGreater(len(result["tool_trajectory"]), 0)
        print(f"\n[Test] Agent executed successfully with reply: {result['reply'][:60]}...")
        print(f"[Test] Tools executed: {[s['tool'] for s in result['tool_trajectory']]}")


if __name__ == "__main__":
    unittest.main()
