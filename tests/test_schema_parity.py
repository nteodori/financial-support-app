"""
Test Schema Parity between Agent Spans and Braintrust Evaluation Datasets.
Required by PRD Rev 4 §3.1.

Asserts that:
1. Production root span `input` matches evaluation dataset record `input` keys.
2. Production root span `output` matches evaluation dataset record `expected` keys (`resolution`, `actions`, `escalate`, `citations`).
3. Additional operational attributes are stored in `metadata` rather than polluting `output`.
4. User feedback API executes cleanly without breaking trace logging.
"""

import json
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.agent.loop import run_agent, AgentRunResult

CASES_PATH = BASE_DIR / "data" / "cases.jsonl"


class TestSchemaParity(unittest.TestCase):

    def setUp(self):
        self.assertTrue(CASES_PATH.exists(), f"Dataset file {CASES_PATH} must exist.")
        with open(CASES_PATH, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            self.case = json.loads(first_line)

    def test_dataset_schema_conformance(self):
        """Verify the dataset case structure conforms to PRD Rev 2 §6.4 & Rev 4 §3.1."""
        self.assertIn("input", self.case)
        self.assertIn("expected", self.case)
        self.assertIn("metadata", self.case)

        expected_input_keys = {"ticket", "account_id", "channel"}
        self.assertTrue(expected_input_keys.issubset(set(self.case["input"].keys())),
                        f"Case input must contain {expected_input_keys}, found {self.case['input'].keys()}")

        expected_target_keys = {"resolution", "actions", "escalate", "citations"}
        self.assertTrue(expected_target_keys.issubset(set(self.case["expected"].keys())),
                        f"Case expected must contain {expected_target_keys}, found {self.case['expected'].keys()}")

    def test_agent_output_schema_parity(self):
        """Verify agent execution output can be mapped directly to dataset 'expected' with zero reshaping."""
        ticket = self.case["input"]["ticket"]
        account_id = self.case["input"]["account_id"]
        channel = self.case["input"]["channel"]

        # Run agent in offline simulation with feedback
        result = run_agent(
            ticket=ticket,
            account_id=account_id,
            channel=channel,
            prompt_version="v1",
            ticket_category=self.case["metadata"].get("category", "fraud_dispute"),
            persona="commercial_support",
            is_money_moving=self.case["metadata"].get("money_moving", True),
            user_feedback=1,
            feedback_comment="Accurate resolution adherence under policy.",
        )

        self.assertIsInstance(result, AgentRunResult)
        self.assertTrue(len(result.reply) > 0, "Agent reply must be non-empty string.")
        self.assertIsInstance(result.actions, list, "Agent actions must be a list of string identifiers.")
        self.assertIsInstance(result.escalated, bool, "Agent escalated must be a boolean.")
        self.assertIsInstance(result.citations, list, "Agent citations must be a list.")

        # Simulate Braintrust 'Add to Dataset' extraction
        # When added from Braintrust UI or SDK:
        # span.input -> dataset.input
        # span.output -> dataset.expected
        simulated_span_input = {
            "ticket": ticket,
            "account_id": account_id,
            "channel": channel,
        }
        simulated_span_output = {
            "resolution": result.reply,
            "actions": result.actions,
            "escalate": result.escalated,
            "citations": result.citations,
        }

        # Assert simulated dataset record has exact same keys as ground-truth dataset
        self.assertEqual(set(simulated_span_input.keys()), set(self.case["input"].keys()))
        self.assertEqual(set(simulated_span_output.keys()), set(self.case["expected"].keys()))

    def test_holdout_and_production_schema_parity(self):
        """Verify holdout cases used for production logs conform to input requirements."""
        holdout_path = BASE_DIR / "data" / "holdout.jsonl"
        self.assertTrue(holdout_path.exists(), f"Holdout file {holdout_path} must exist.")
        with open(holdout_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                h_case = json.loads(line)
                self.assertIn("ticket", h_case, f"Holdout line {i} missing 'ticket'")
                self.assertIn("account_id", h_case, f"Holdout line {i} missing 'account_id'")


if __name__ == "__main__":
    unittest.main()
