"""
Unit tests for Braintrust multi-turn conversation thread logging.
Braintrust SDK Version: 0.39.0
"""

import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.seed_threads import (
    SCENARIOS,
    generate_extended_scenarios,
    log_conversation_thread,
)


class TestBraintrustThreadsLogging(unittest.TestCase):

    def test_scenarios_taxonomy_and_integrity(self):
        """Assert all base scenarios have valid topic, pattern, and multi-turn message definitions."""
        valid_topics = {
            "fraud_dispute",
            "duplicate_charge",
            "credit_limit_bump",
            "card_management",
            "wire_transfer_ops",
            "developer_api_webhook",
        }
        valid_patterns = {
            "multi_turn_resolution",
            "mandatory_escalation",
            "circular_friction",
            "policy_drift_under_pressure",
            "context_loss",
        }

        self.assertGreaterEqual(len(SCENARIOS), 6)

        for sc in SCENARIOS:
            self.assertIn(sc["topic"], valid_topics, f"Invalid topic: {sc['topic']}")
            self.assertIn(sc["pattern"], valid_patterns, f"Invalid pattern: {sc['pattern']}")
            self.assertGreaterEqual(len(sc["turns"]), 2, f"Scenario {sc['id']} has less than 2 turns.")
            self.assertIn("resolution_success", sc["scores"])
            self.assertIn("no_unauthorized_action", sc["scores"])

            for idx, turn in enumerate(sc["turns"], start=1):
                self.assertTrue(turn["user_message"], f"Turn {idx} in {sc['id']} missing user_message")
                self.assertTrue(turn["reply"], f"Turn {idx} in {sc['id']} missing reply")
                self.assertTrue(turn["reasoning"], f"Turn {idx} in {sc['id']} missing reasoning")

    def test_generate_extended_scenarios(self):
        """Assert dynamic scenario generation produces distinct thread IDs and accounts."""
        count = 15
        extended = generate_extended_scenarios(count)
        self.assertEqual(len(extended), count)

        thread_ids = [s["thread_id"] for s in extended]
        self.assertEqual(len(thread_ids), len(set(thread_ids)), "Thread IDs must be strictly unique.")

        for item in extended:
            self.assertTrue(item["thread_id"].startswith("TH-"))
            self.assertIn("customer_tier", item)
            self.assertIn("company_name", item)

    def test_log_conversation_thread_dry_run(self):
        """Assert thread logging logic works cleanly in dry-run mode."""
        extended = generate_extended_scenarios(3)
        for sc in extended:
            res = log_conversation_thread(
                logger=None,
                scenario=sc,
                base_timestamp=1700000000.0,
                dry_run=True,
            )
            self.assertIn("thread_id", res)
            self.assertIn("topic", res)
            self.assertIn("pattern", res)
            self.assertGreaterEqual(res["turn_count"], 2)


if __name__ == "__main__":
    unittest.main()
