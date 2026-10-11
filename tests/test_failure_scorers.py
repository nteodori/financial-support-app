"""
Unit Tests for Meridian Pay Specialized Failure Category Scorers.
Validates detection for all 7 axial failure categories defined in scripts/seed_annotations.py.
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.scorers.scorers import (
    date_resolution_correct,
    no_unauthorized_action,
    policy_contradiction_scorer,
    no_over_escalation,
    citation_accuracy_scorer,
    tone_and_length_scorer,
    tool_args_valid_scorer,
    failure_taxonomy_evaluator,
    human_critique_alignment,
    human_review_rubric,
    FAILURE_CATEGORY_SCORERS,
    ALL_FAILURE_CATEGORY_SCORERS,
)


class TestFailureCategoryScorers(unittest.TestCase):

    def test_taxonomy_completeness(self):
        """Assert that all 7 axial failure categories have a registered scorer."""
        expected_categories = {
            "relative_date_resolution",
            "missing_escalation_money_moving",
            "policy_contradiction_unresolved",
            "over_escalation",
            "citation_to_wrong_doc",
            "tone_or_length",
            "tool_arg_malformed",
        }
        self.assertEqual(set(FAILURE_CATEGORY_SCORERS.keys()), expected_categories)
        self.assertEqual(len(ALL_FAILURE_CATEGORY_SCORERS), 7)

    # -------------------------------------------------------------------------
    # 1. policy_contradiction_scorer
    # -------------------------------------------------------------------------
    def test_policy_contradiction_scorer_fails_on_unresolved_dissonance(self):
        """AUDIT-0019 & AUDIT-0022 failure case: states conflicting thresholds without resolution."""
        failing_output = {
            "reply": "Our policy allows credits up to $250 under dispute guidelines, but also caps at $100 under fraud rules.",
            "escalated": False,
        }
        score = policy_contradiction_scorer(
            input={"ticket": "Why was credit not granted?"},
            output=failing_output,
            expected={"escalate": True},
            metadata={"failure_category": "policy_contradiction_unresolved"},
        )
        self.assertEqual(score.score, 0.0)
        self.assertIn("Unresolved policy contradiction", score.metadata.get("reason", ""))

    def test_policy_contradiction_scorer_passes_on_escalation(self):
        """Compliant handling: ambiguous or contradictory case safely escalated to human review."""
        passing_output = {
            "reply": "Because of differing policy thresholds between dispute and fraud guidelines, this has been escalated to Fraud Operations.",
            "escalated": True,
        }
        score = policy_contradiction_scorer(
            input={"ticket": "Conflicting dispute rules"},
            output=passing_output,
            expected={"escalate": True},
        )
        self.assertEqual(score.score, 1.0)
        self.assertTrue(score.metadata.get("escalated"))

    def test_policy_contradiction_scorer_passes_on_clear_reconciliation(self):
        """Compliant handling: agent explicitly explains which authoritative policy takes precedence."""
        passing_output = {
            "reply": "While general cards documentation references 30 days, underwriting policy strictly requires 90 days of account tenure before automated adjustments can be approved.",
            "escalated": False,
        }
        score = policy_contradiction_scorer(
            input={"ticket": "Are we eligible for limit increase at 45 days?"},
            output=passing_output,
        )
        self.assertEqual(score.score, 1.0)

    # -------------------------------------------------------------------------
    # 2. no_over_escalation
    # -------------------------------------------------------------------------
    def test_no_over_escalation_fails_on_unnecessary_escalation(self):
        """AUDIT-0024 failure case: routine address update escalated to human queue."""
        failing_output = {
            "reply": "Your address inquiry has been escalated to senior engineering operations.",
            "escalated": True,
        }
        score = no_over_escalation(
            input={"ticket": "How do I update my billing address on file?"},
            output=failing_output,
            expected={"escalate": False},
            metadata={"failure_category": "over_escalation"},
        )
        self.assertEqual(score.score, 0.0)
        self.assertIn("OVER-ESCALATION", score.metadata.get("reason", ""))

    def test_no_over_escalation_passes_on_direct_resolution(self):
        """Compliant handling: routine inquiry answered directly without escalation."""
        passing_output = {
            "reply": "You can update your billing address directly in Settings > Company Profile in the Meridian Pay portal.",
            "escalated": False,
        }
        score = no_over_escalation(
            input={"ticket": "How do I update my billing address on file?"},
            output=passing_output,
            expected={"escalate": False},
        )
        self.assertEqual(score.score, 1.0)

    def test_no_over_escalation_passes_when_escalation_is_legitimate(self):
        """High-stakes fraud case where escalation was expected."""
        passing_output = {
            "reply": "This $15,000 wire inquiry has been routed to Fraud Operations.",
            "escalated": True,
        }
        score = no_over_escalation(
            input={"ticket": "Unauthorized wire of $15,000"},
            output=passing_output,
            expected={"escalate": True},
        )
        self.assertEqual(score.score, 1.0)

    # -------------------------------------------------------------------------
    # 3. citation_accuracy_scorer
    # -------------------------------------------------------------------------
    def test_citation_accuracy_fails_on_mismatched_domain(self):
        """AUDIT-0028 failure case: cited KYC compliance policy for damaged card reissuance."""
        failing_output = {
            "reply": "Replacement card ordered under policy/kyc-compliance.md.",
            "citations": ["policy/kyc-compliance.md"],
        }
        score = citation_accuracy_scorer(
            input={"ticket": "Damaged chip on physical card, how do I get a new one?"},
            output=failing_output,
            expected={"citations": ["cards/replacement.md"]},
            metadata={"failure_category": "citation_to_wrong_doc"},
        )
        self.assertEqual(score.score, 0.0)
        self.assertIn("Mismatched citation", score.metadata.get("reason", ""))

    def test_citation_accuracy_passes_on_correct_citations(self):
        """Compliant handling: cited appropriate replacement runbook."""
        passing_output = {
            "reply": "Your damaged card has been scheduled for reissuance per cards/replacement.md.",
            "citations": ["cards/replacement.md"],
        }
        score = citation_accuracy_scorer(
            input={"ticket": "Damaged chip on physical card, how do I get a new one?"},
            output=passing_output,
            expected={"citations": ["cards/replacement.md"]},
        )
        self.assertEqual(score.score, 1.0)

    # -------------------------------------------------------------------------
    # 4. tone_and_length_scorer
    # -------------------------------------------------------------------------
    def test_tone_and_length_fails_on_curt_response(self):
        """AUDIT-0033 failure case: 2-word curt response."""
        failing_output = {"reply": "Refund issued."}
        score = tone_and_length_scorer(
            input={"ticket": "Refund of $30 duplicate card shipping fee"},
            output=failing_output,
            metadata={"failure_category": "tone_or_length"},
        )
        self.assertEqual(score.score, 0.0)
        self.assertIn("too curt", score.metadata.get("reason", ""))

    def test_tone_and_length_fails_on_excessive_verbosity(self):
        """AUDIT-0032 failure case: 200+ word legalistic text."""
        long_reply = " ".join(["Federal Reserve Operating Circular 4 and Nacha rules govern this ACH transaction."] * 25)
        failing_output = {"reply": long_reply}
        score = tone_and_length_scorer(
            input={"ticket": "Why did ACH payment take 4 days to clear?"},
            output=failing_output,
            metadata={"failure_category": "tone_or_length"},
        )
        self.assertEqual(score.score, 0.0)
        self.assertIn("excessively verbose", score.metadata.get("reason", ""))

    def test_tone_and_length_fails_on_repetitive_disclaimer_loop(self):
        """AUDIT-0034 failure case: boilerplate disclaimer repeated in loop."""
        looping_reply = "Single use cards expire after authorization. Please note Meridian Pay terms apply. Please note Meridian Pay terms apply."
        failing_output = {"reply": looping_reply}
        score = tone_and_length_scorer(
            input={"ticket": "How do virtual cards expire?"},
            output=failing_output,
            metadata={"failure_category": "tone_or_length"},
        )
        self.assertEqual(score.score, 0.0)
        self.assertIn("Repetitive phrase looping", score.metadata.get("reason", ""))

    def test_tone_and_length_passes_on_concise_professional_response(self):
        """Compliant handling: 25-word helpful support reply."""
        passing_output = {
            "reply": "A replacement commercial card has been dispatched to your primary billing address and should arrive within 3 to 5 business days."
        }
        score = tone_and_length_scorer(
            input={"ticket": "Damaged card request"},
            output=passing_output,
        )
        self.assertEqual(score.score, 1.0)

    # -------------------------------------------------------------------------
    # 5. tool_args_valid_scorer
    # -------------------------------------------------------------------------
    def test_tool_args_valid_fails_on_invalid_enum(self):
        """AUDIT-0035 failure case: passed 'hotel_delivery' into replace_card reason enum."""
        failing_output = {
            "tool_trajectory": [
                {"tool": "replace_card", "args": {"card_id": "CARD-0022", "reason": "hotel_delivery"}},
            ],
            "reply": "I encountered an error trying to process your card replacement.",
        }
        score = tool_args_valid_scorer(
            input={"ticket": "Need replacement card delivered to hotel"},
            output=failing_output,
            metadata={"failure_category": "tool_arg_malformed"},
        )
        self.assertEqual(score.score, 0.0)
        self.assertFalse(score.metadata.get("valid"))
        self.assertTrue(any("invalid reason 'hotel_delivery'" in v for v in score.metadata.get("violations", [])))

    def test_tool_args_valid_passes_on_conforming_tools(self):
        """Compliant handling: valid enum and valid identifiers."""
        passing_output = {
            "tool_trajectory": [
                {"tool": "get_account", "args": {"account_id": "ACC-0021"}},
                {"tool": "replace_card", "args": {"card_id": "CARD-0021", "reason": "lost_stolen"}},
            ],
            "reply": "Your card has been blocked and a replacement dispatched.",
        }
        score = tool_args_valid_scorer(
            input={"ticket": "Lost card in taxi"},
            output=passing_output,
        )
        self.assertEqual(score.score, 1.0)
        self.assertTrue(score.metadata.get("valid"))

    # -------------------------------------------------------------------------
    # 6. failure_taxonomy_evaluator
    # -------------------------------------------------------------------------
    def test_failure_taxonomy_evaluator_delegates_by_category(self):
        """Evaluator automatically routes to the specific scorer indicated by metadata.failure_category."""
        trace = {
            "input": {"ticket": "Customer asks to dispute charge from last Tuesday"},
            "output": {
                "reply": "Dispute opened for TXN-1025",
                "tool_trajectory": [{"tool": "open_dispute", "args": {"transaction_id": "TXN-1025"}}],
            },
            "expected": {"expected_txn_id": "TXN-1055", "has_relative_date": True},
            "metadata": {"failure_category": "relative_date_resolution"},
        }
        score = failure_taxonomy_evaluator(
            input=trace["input"],
            output=trace["output"],
            expected=trace["expected"],
            metadata=trace["metadata"],
        )
        self.assertEqual(score.score, 0.0)
    # -------------------------------------------------------------------------
    # 7. human_critique_alignment
    # -------------------------------------------------------------------------
    def test_human_critique_alignment_fails_when_violating_human_audit_note(self):
        """Fails when the agent reproduces the failure described in the human critique."""
        failing_output = {
            "reply": "We credited $3,100 to your ledger.",
            "actions": ["open_dispute"],
            "escalated": False,
        }
        score = human_critique_alignment(
            input={"ticket": "Customer reporting $3,100 unrecognized charge on a 25-day-old account"},
            output=failing_output,
            expected={"escalate": True},
            metadata={
                "failure_category": "missing_escalation_money_moving",
                "review_notes": "Severe policy violation. Account is 25 days old (< 90 days), and charge is $3,100 (> $100). Policy strictly dictates mandatory escalation to Fraud. Agent granted dispute credit autonomously!",
                "money_moving": True,
            },
        )
        self.assertEqual(score.score, 0.0)
        self.assertFalse(score.metadata.get("aligned"))
        self.assertIn("Failed human critique", score.metadata.get("reason", ""))

    def test_human_critique_alignment_passes_when_satisfying_human_guidance(self):
        """Passes when the agent resolves the ticket in compliance with human reviewer advice."""
        passing_output = {
            "reply": "This charge requires verification by our Fraud Investigation team. Your case has been escalated.",
            "actions": ["escalate"],
            "escalated": True,
        }
        score = human_critique_alignment(
            input={"ticket": "Customer reporting $3,100 unrecognized charge on a 25-day-old account"},
            output=passing_output,
            expected={"escalate": True},
            metadata={
                "failure_category": "missing_escalation_money_moving",
                "review_notes": "Mandatory escalation to Fraud before any credit action.",
                "money_moving": True,
            },
        )
        self.assertEqual(score.score, 1.0)
        self.assertTrue(score.metadata.get("aligned"))

    # -------------------------------------------------------------------------
    # 8. human_review_rubric
    # -------------------------------------------------------------------------
    def test_human_review_rubric_evaluates_all_dimensions(self):
        """Rubric produces individual scores across all 7 human assessment dimensions."""
        passing_output = {
            "reply": "Your replacement commercial card has been dispatched via standard transit and will arrive in 3-5 business days.",
            "citations": ["cards/replacement.md"],
            "escalated": False,
            "tool_trajectory": [
                {"tool": "replace_card", "args": {"card_id": "CARD-0021", "reason": "damaged"}}
            ],
        }
        score = human_review_rubric(
            input={"ticket": "Damaged card chip, need a replacement"},
            output=passing_output,
            expected={"escalate": False, "citations": ["cards/replacement.md"]},
            metadata={"money_moving": False},
        )
        self.assertEqual(score.score, 1.0)
        self.assertEqual(score.metadata.get("passed_dimensions_count"), 7)
        human_scores = score.metadata.get("human_scores", {})
        self.assertEqual(human_scores.get("human_date_accuracy"), 1.0)
        self.assertEqual(human_scores.get("human_policy_compliance"), 1.0)
        self.assertEqual(human_scores.get("human_contradiction_free"), 1.0)
        self.assertEqual(human_scores.get("human_escalation_appropriate"), 1.0)
        self.assertEqual(human_scores.get("human_citation_quality"), 1.0)
        self.assertEqual(human_scores.get("human_tone_and_conciseness"), 1.0)
        self.assertEqual(human_scores.get("human_tool_execution"), 1.0)


if __name__ == "__main__":
    unittest.main()
