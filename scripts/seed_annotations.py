"""
Seed 60 Production Traces with Open-Coded Review Notes and Axial Failure Taxonomy.
Braintrust SDK Version: 0.39.0

Implements Beat S2: Error Analysis & Failure Taxonomy (Hamel Husain & Shreya Shankar method).
- 60 production traces audited
- 35 failing traces across 7 categories
- 25 passing traces with positive reviewer commentary
- Visible in Braintrust Logs with metadata.failure_category, metadata.review_notes, tags, and human_review scores
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import braintrust as bt
from dotenv import load_dotenv

load_dotenv()

# The 60 annotated traces with handwritten open-coded notes in Nick Teodori's voice
ANNOTATED_TRACES: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1. relative_date_resolution (12 traces) - TOP FAILURE MODE
    # -------------------------------------------------------------------------
    {
        "id": "AUDIT-0001",
        "ticket": "Customer disputing the duplicate charge from last Tuesday for cloud storage ($45.20)",
        "account_id": "ACC-0026",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Customer explicitly stated 'last Tuesday' ($45.20). Agent queried list_transactions, saw multiple SaaS transactions, and grabbed the most recent one (TXN-1025 from yesterday) instead of TXN-1055 from 7 days ago. Off-by-one date failure because agent has no date-parsing helper.",
        "tools": [
            ("get_account", {"account_id": "ACC-0026"}, {"tier": "Growth", "age_days": 180}),
            ("list_transactions", {"account_id": "ACC-0026"}, [{"id": "TXN-1025", "date": "2026-08-25", "merchant": "STRIPE"}, {"id": "TXN-1055", "date": "2026-08-18", "merchant": "STRIPE"}]),
            ("open_dispute", {"transaction_id": "TXN-1025", "reason": "duplicate_charge"}, {"dispute_id": "DSP-901"}),
        ],
        "reply": "We have opened a dispute for transaction TXN-1025 for $45.20.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.85},
    },
    {
        "id": "AUDIT-0002",
        "ticket": "Customer asks to dispute the software charge from a couple weeks ago ($185.00) on account ACC-0002",
        "account_id": "ACC-0002",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Customer referenced 'a couple weeks ago' for $185.00. Agent pulled 15 transactions, ignored relative anchor time, and filed against TXN-1033 from 10 days ago instead of TXN-1002 from 14 days ago. Recurring date-sorting blindspot.",
        "tools": [
            ("get_account", {"account_id": "ACC-0002"}, {"tier": "Scale", "age_days": 140}),
            ("list_transactions", {"account_id": "ACC-0002"}, [{"id": "TXN-1033", "date": "2026-08-16"}, {"id": "TXN-1002", "date": "2026-08-12"}]),
            ("open_dispute", {"transaction_id": "TXN-1033", "reason": "unrecognized_software"}, {"dispute_id": "DSP-902"}),
        ],
        "reply": "Dispute opened for transaction TXN-1033 in the amount of $185.00.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.80},
    },
    {
        "id": "AUDIT-0003",
        "ticket": "Unrecognized Uber charge from earlier this week on commercial card CARD-0030",
        "account_id": "ACC-0030",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Customer said 'earlier this week'. Agent selected the first Uber ride in the list (TXN-1008 from 3 weeks ago) because list_transactions returned items sorted by amount rather than chronologically. Wrong charge disputed.",
        "tools": [
            ("get_account", {"account_id": "ACC-0030"}, {"tier": "Core"}),
            ("list_transactions", {"account_id": "ACC-0030"}, [{"id": "TXN-1008", "merchant": "UBER"}, {"id": "TXN-1056", "merchant": "UBER"}]),
            ("open_dispute", {"transaction_id": "TXN-1008", "reason": "unrecognized"}, {"dispute_id": "DSP-903"}),
        ],
        "reply": "A dispute has been initiated for your Uber transaction TXN-1008.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.82},
    },
    {
        "id": "AUDIT-0004",
        "ticket": "Dispute the gas station charge from three days ago ($15.00) that posted twice",
        "account_id": "ACC-0024",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Ticket specified 'three days ago'. Agent failed calendar math relative to transaction ISO dates and grabbed the gas charge from 18 days ago. Customer will have to contact support again.",
        "tools": [
            ("get_account", {"account_id": "ACC-0024"}, {"tier": "Core"}),
            ("list_transactions", {"account_id": "ACC-0024"}, [{"id": "TXN-1090"}, {"id": "TXN-1071"}]),
            ("open_dispute", {"transaction_id": "TXN-1090", "reason": "duplicate"}, {"dispute_id": "DSP-904"}),
        ],
        "reply": "We opened dispute DSP-904 for the gas station transaction TXN-1090.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.88},
    },
    {
        "id": "AUDIT-0005",
        "ticket": "Can we dispute that hotel charge from last weekend ($447.68)?",
        "account_id": "ACC-0028",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Customer referenced 'last weekend'. Agent picked TXN-1154 from yesterday instead of TXN-1015 from last Saturday. The model defaults to whatever sits at index 0 of the tool response.",
        "tools": [
            ("get_account", {"account_id": "ACC-0028"}, {"tier": "Scale"}),
            ("list_transactions", {"account_id": "ACC-0028"}, [{"id": "TXN-1154"}, {"id": "TXN-1015"}]),
            ("open_dispute", {"transaction_id": "TXN-1154", "reason": "hotel_dispute"}, {"dispute_id": "DSP-905"}),
        ],
        "reply": "Your hotel charge TXN-1154 is now in formal dispute.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.84},
    },
    {
        "id": "AUDIT-0006",
        "ticket": "Customer disputing the duplicate shipping fee from a couple weeks back ($20.00)",
        "account_id": "ACC-0030",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Relative date 'a couple weeks back' was misattributed to a transaction from 4 days ago. Classic lack of temporal anchoring in prompt.",
        "tools": [
            ("get_account", {"account_id": "ACC-0030"}, {"tier": "Core"}),
            ("list_transactions", {"account_id": "ACC-0030"}, [{"id": "TXN-1127"}]),
            ("open_dispute", {"transaction_id": "TXN-1056", "reason": "shipping_duplicate"}, {"dispute_id": "DSP-906"}),
        ],
        "reply": "We disputed TXN-1056 for $20.00.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.86},
    },
    {
        "id": "AUDIT-0007",
        "ticket": "Customer questioning that airline charge from about three weeks back",
        "account_id": "ACC-0008",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Delta Air Lines flight booking from 22 days ago was requested; agent disputed an in-flight WiFi charge from 3 days ago. Model cannot reliably disambiguate merchant sub-charges by date.",
        "tools": [
            ("get_account", {"account_id": "ACC-0008"}, {"tier": "Scale"}),
            ("list_transactions", {"account_id": "ACC-0008"}, [{"id": "TXN-1010"}, {"id": "TXN-1018"}]),
            ("open_dispute", {"transaction_id": "TXN-1018", "reason": "airline_charge"}, {"dispute_id": "DSP-907"}),
        ],
        "reply": "Dispute filed for TXN-1018.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.81},
    },
    {
        "id": "AUDIT-0008",
        "ticket": "Duplicate merchant billing from last Thursday for office supplies ($64.95)",
        "account_id": "ACC-0010",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Staples Supplies charge was from 5 days ago (Thursday). Agent selected TXN-1006 from July. Off by nearly a month.",
        "tools": [
            ("get_account", {"account_id": "ACC-0010"}, {"tier": "Core"}),
            ("list_transactions", {"account_id": "ACC-0010"}, [{"id": "TXN-1006"}, {"id": "TXN-1122"}]),
            ("open_dispute", {"transaction_id": "TXN-1006", "reason": "duplicate_billing"}, {"dispute_id": "DSP-908"}),
        ],
        "reply": "Dispute initiated for transaction TXN-1006.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.83},
    },
    {
        "id": "AUDIT-0009",
        "ticket": "Unrecognized software subscription charge from about three weeks ago on 200-day-old account",
        "account_id": "ACC-0024",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Customer wrote 'about three weeks ago'. Agent matched on merchant string 'SLACK' and grabbed the newest August 21 transaction instead of the August 2 transaction.",
        "tools": [
            ("get_account", {"account_id": "ACC-0024"}, {"tier": "Core"}),
            ("list_transactions", {"account_id": "ACC-0024"}, [{"id": "TXN-1071"}, {"id": "TXN-1126"}]),
            ("open_dispute", {"transaction_id": "TXN-1071", "reason": "unrecognized_subscription"}, {"dispute_id": "DSP-909"}),
        ],
        "reply": "We opened dispute DSP-909 for Slack charge TXN-1071.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.85},
    },
    {
        "id": "AUDIT-0010",
        "ticket": "Customer disputing duplicate restaurant charge from yesterday afternoon ($84.20)",
        "account_id": "ACC-0023",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Yesterday afternoon charge was TXN-1008. Agent picked an older dining charge because both had identical dollar amounts.",
        "tools": [
            ("get_account", {"account_id": "ACC-0023"}, {"tier": "Core"}),
            ("list_transactions", {"account_id": "ACC-0023"}, [{"id": "TXN-1008"}, {"id": "TXN-1056"}]),
            ("open_dispute", {"transaction_id": "TXN-1056", "reason": "duplicate_charge"}, {"dispute_id": "DSP-910"}),
        ],
        "reply": "Dispute filed for TXN-1056 in amount $84.20.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.87},
    },
    {
        "id": "AUDIT-0011",
        "ticket": "Customer asks to dispute cloud service charge from earlier this week ($325.34)",
        "account_id": "ACC-0022",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Agent confused GitHub invoice from 2 days ago with Zoom invoice from 30 days ago. Chose wrong transaction entirely.",
        "tools": [
            ("get_account", {"account_id": "ACC-0022"}, {"tier": "Growth"}),
            ("list_transactions", {"account_id": "ACC-0022"}, [{"id": "TXN-1038"}, {"id": "TXN-1046"}]),
            ("open_dispute", {"transaction_id": "TXN-1046", "reason": "unrecognized_cloud"}, {"dispute_id": "DSP-911"}),
        ],
        "reply": "Dispute opened for transaction TXN-1046.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.80},
    },
    {
        "id": "AUDIT-0012",
        "ticket": "Dispute of charge from roughly two weeks ago on account with prior chargeback history",
        "account_id": "ACC-0002",
        "category": "relative_date_resolution",
        "status": "fail",
        "note": "Failed to map 'roughly two weeks ago' to TXN-1033. Defaulted to the top of the transaction array.",
        "tools": [
            ("get_account", {"account_id": "ACC-0002"}, {"tier": "Scale"}),
            ("list_transactions", {"account_id": "ACC-0002"}, [{"id": "TXN-1002"}, {"id": "TXN-1033"}]),
            ("open_dispute", {"transaction_id": "TXN-1002", "reason": "chargeback_history"}, {"dispute_id": "DSP-912"}),
        ],
        "reply": "Dispute filed for TXN-1002.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.84},
    },

    # -------------------------------------------------------------------------
    # 2. missing_escalation_money_moving (6 traces)
    # -------------------------------------------------------------------------
    {
        "id": "AUDIT-0013",
        "ticket": "Customer reporting $3,100 unrecognized charge on a 25-day-old account",
        "account_id": "ACC-0009",
        "category": "missing_escalation_money_moving",
        "status": "fail",
        "note": "Severe policy violation. Account is 25 days old (< 90 days), and charge is $3,100 (> $100). Policy strictly dictates mandatory escalation to Fraud. Agent granted dispute credit autonomously!",
        "tools": [
            ("get_account", {"account_id": "ACC-0009"}, {"age_days": 25, "tier": "Scale"}),
            ("open_dispute", {"transaction_id": "TXN-1004", "reason": "fraud"}, {"status": "opened"}),
        ],
        "reply": "We have opened a dispute and credited $3,100 to your ledger.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 0.0, "grounding": 0.70},
    },
    {
        "id": "AUDIT-0014",
        "ticket": "Disputed charge of $210 on account with recent_chargeback flag",
        "account_id": "ACC-0002",
        "category": "missing_escalation_money_moving",
        "status": "fail",
        "note": "Account has active recent_chargeback risk flag. Any dispute on flagged accounts requires fraud review before credit. Agent opened dispute without escalating.",
        "tools": [
            ("get_account", {"account_id": "ACC-0002"}, {"risk_flags": ["recent_chargeback"]}),
            ("open_dispute", {"transaction_id": "TXN-1002", "reason": "unauthorized"}, {"status": "success"}),
        ],
        "reply": "Dispute has been registered with provisional credit.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 0.0, "grounding": 0.75},
    },
    {
        "id": "AUDIT-0015",
        "ticket": "Customer asking for credit limit increase from $10k to $25k on young account",
        "account_id": "ACC-0004",
        "category": "missing_escalation_money_moving",
        "status": "fail",
        "note": "Agent adjusted credit limit by 150% without forwarding to Underwriting. Policy ceiling for automated adjustments is 10% on mature accounts only.",
        "tools": [
            ("get_account", {"account_id": "ACC-0004"}, {"credit_limit": 10000.0, "age_days": 40}),
            ("adjust_limit", {"account_id": "ACC-0004", "new_limit": 25000.0}, {"status": "approved"}),
        ],
        "reply": "Your credit limit has been increased to $25,000.00 effective immediately.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 0.0, "grounding": 0.65},
    },
    {
        "id": "AUDIT-0016",
        "ticket": "Demand for $200 refund due to API outage",
        "account_id": "ACC-0006",
        "category": "missing_escalation_money_moving",
        "status": "fail",
        "note": "Agent called issue_refund for $200.00. Tier 2 discretionary refund authority ceiling is strictly capped at $50.00. Finance approval was skipped.",
        "tools": [
            ("get_account", {"account_id": "ACC-0006"}, {"tier": "Core"}),
            ("issue_refund", {"account_id": "ACC-0006", "amount": 200.0}, {"status": "credited"}),
        ],
        "reply": "We have refunded $200.00 to your commercial balance.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 0.0, "grounding": 0.72},
    },
    {
        "id": "AUDIT-0017",
        "ticket": "Card stolen at conference in Las Vegas with $750 in restaurant charges",
        "account_id": "ACC-0008",
        "category": "missing_escalation_money_moving",
        "status": "fail",
        "note": "Agent replaced the card but failed to escalate the $750 unauthorized spend to Fraud. Uncontrolled risk exposure.",
        "tools": [
            ("get_account", {"account_id": "ACC-0008"}, {"tier": "Scale"}),
            ("replace_card", {"card_id": "CARD-0008", "reason": "stolen"}, {"status": "dispatched"}),
            ("open_dispute", {"transaction_id": "TXN-1018", "reason": "stolen"}, {"status": "success"}),
        ],
        "reply": "Card blocked and new card on the way. Charges have been disputed.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 0.0, "grounding": 0.78},
    },
    {
        "id": "AUDIT-0018",
        "ticket": "Customer requesting $8,000 limit bump with active spend velocity flag",
        "account_id": "ACC-0007",
        "category": "missing_escalation_money_moving",
        "status": "fail",
        "note": "Account has rapid_spend_velocity flag. Agent adjusted limit rather than escalating to Risk/Underwriting.",
        "tools": [
            ("get_account", {"account_id": "ACC-0007"}, {"risk_flags": ["rapid_spend_velocity"]}),
            ("adjust_limit", {"account_id": "ACC-0007", "new_limit": 18000.0}, {"status": "approved"}),
        ],
        "reply": "Limit increased to $18,000.00.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 0.0, "grounding": 0.68},
    },

    # -------------------------------------------------------------------------
    # 3. policy_contradiction_unresolved (5 traces)
    # -------------------------------------------------------------------------
    {
        "id": "AUDIT-0019",
        "ticket": "Customer asking why provisional credit of $220 wasn't granted immediately per policy",
        "account_id": "ACC-0002",
        "category": "policy_contradiction_unresolved",
        "status": "fail",
        "note": "Agent quoted legacy dispute-handling.md ($250 threshold) while simultaneously citing fraud-thresholds.md ($100 threshold). Hallucinated that both apply depending on user request.",
        "tools": [
            ("search_kb", {"query": "provisional credit dispute threshold"}, [{"doc": "policy/dispute-handling.md"}, {"doc": "policy/fraud-thresholds.md"}]),
        ],
        "reply": "Our policy allows credits up to $250 under dispute guidelines, but also caps at $100 under fraud rules.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.55},
    },
    {
        "id": "AUDIT-0020",
        "ticket": "Can we get a goodwill courtesy refund of $75 for service downtime?",
        "account_id": "ACC-0015",
        "category": "policy_contradiction_unresolved",
        "status": "fail",
        "note": "Agent read both refund-authority.md ($50 cap) and runbooks/service-outage ($100 exceptional credit) and gave an incoherent explanation without escalating.",
        "tools": [
            ("search_kb", {"query": "goodwill courtesy refund outage limit"}, [{"doc": "policy/refund-authority.md"}]),
        ],
        "reply": "Refunds are limited to $50, but outage refunds can be $100, so we cannot issue $75 without checking.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.60},
    },
    {
        "id": "AUDIT-0021",
        "ticket": "Disputing international FX transaction fee charged after card replacement",
        "account_id": "ACC-0005",
        "category": "policy_contradiction_unresolved",
        "status": "fail",
        "note": "Confused settlement timing rules between cards/overview.md and payments/settlement-rails.md regarding FX surcharge waivers.",
        "tools": [
            ("search_kb", {"query": "international FX transaction fee waiver replacement"}, []),
        ],
        "reply": "FX fees cannot be waived per card policy, but settlement rails allow currency fee adjustments upon request.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.58},
    },
    {
        "id": "AUDIT-0022",
        "ticket": "Is our 45-day-old commercial account eligible for automated limit review?",
        "account_id": "ACC-0004",
        "category": "policy_contradiction_unresolved",
        "status": "fail",
        "note": "KB docs contradict each other: limits/credit-limits.md says 30 days minimum tenure, while policy/limit-increase-policy.md says 90 days. Agent failed to flag contradiction.",
        "tools": [
            ("search_kb", {"query": "credit limit review minimum account age tenure"}, []),
        ],
        "reply": "You are eligible after 30 days, but underwriting requires 90 days before adjustments can be processed.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.62},
    },
    {
        "id": "AUDIT-0023",
        "ticket": "Customer questioning whether wire recall can be stopped after cutoff",
        "account_id": "ACC-0003",
        "category": "policy_contradiction_unresolved",
        "status": "fail",
        "note": "Fedwire cutoff rules vs FedNow instant recall procedures were merged into contradictory customer guidance.",
        "tools": [
            ("search_kb", {"query": "wire recall cutoff time cancel domestic"}, []),
        ],
        "reply": "Wires can be canceled before 4 PM, but Fedwire settles irreversibly at 2 PM.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.52},
    },

    # -------------------------------------------------------------------------
    # 4. over_escalation (4 traces)
    # -------------------------------------------------------------------------
    {
        "id": "AUDIT-0024",
        "ticket": "How do I update my billing address on file?",
        "account_id": "ACC-0020",
        "category": "over_escalation",
        "status": "fail",
        "note": "Routine self-serve inquiry escalated to Tier 3 Operations. Unnecessary ticket deflection failure.",
        "tools": [
            ("escalate", {"reason": "Customer inquiry regarding address", "queue": "support_tier3"}, {}),
        ],
        "reply": "Your address inquiry has been escalated to senior engineering operations.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.70},
    },
    {
        "id": "AUDIT-0025",
        "ticket": "Can we add 5 new virtual cards for our engineering interns?",
        "account_id": "ACC-0022",
        "category": "over_escalation",
        "status": "fail",
        "note": "Standard virtual card creation is supported directly in self-serve portal. Agent panicked and escalated to Fraud.",
        "tools": [
            ("escalate", {"reason": "Virtual card volume request", "queue": "fraud"}, {}),
        ],
        "reply": "Due to the number of requested cards, this has been routed to Fraud Investigation.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.65},
    },
    {
        "id": "AUDIT-0026",
        "ticket": "What are the wire fees for sending funds to the UK?",
        "account_id": "ACC-0023",
        "category": "over_escalation",
        "status": "fail",
        "note": "Informational fee lookup escalated to Finance queue rather than providing standard $25 international wire fee from docs.",
        "tools": [
            ("escalate", {"reason": "International wire fee inquiry", "queue": "finance"}, {}),
        ],
        "reply": "Our Finance team will review your account to determine applicable fees.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.68},
    },
    {
        "id": "AUDIT-0027",
        "ticket": "Can I lock my card temporarily in the app?",
        "account_id": "ACC-0025",
        "category": "over_escalation",
        "status": "fail",
        "note": "Basic card controls feature explained in runbooks escalated to Security queue. Degrades CSAT.",
        "tools": [
            ("escalate", {"reason": "Card freeze inquiry", "queue": "security"}, {}),
        ],
        "reply": "Your account has been forwarded to Security Operations to review card freeze eligibility.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.71},
    },

    # -------------------------------------------------------------------------
    # 5. citation_to_wrong_doc (4 traces)
    # -------------------------------------------------------------------------
    {
        "id": "AUDIT-0028",
        "ticket": "Damaged chip on physical card, how do I get a new one?",
        "account_id": "ACC-0027",
        "category": "citation_to_wrong_doc",
        "status": "fail",
        "note": "Agent cited policy/kyc-compliance.md instead of cards/replacement.md. The reply answered the question, but the audit trail links to KYC regulations.",
        "tools": [
            ("search_kb", {"query": "damaged card chip replacement"}, [{"doc": "policy/kyc-compliance.md"}]),
            ("replace_card", {"card_id": "CARD-0027", "reason": "damaged"}, {}),
        ],
        "reply": "Replacement card ordered under policy/kyc-compliance.md.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.74},
    },
    {
        "id": "AUDIT-0029",
        "ticket": "Explanation of R08 payment stopped return code",
        "account_id": "ACC-0026",
        "category": "citation_to_wrong_doc",
        "status": "fail",
        "note": "Cited cards/overview.md instead of payments/settlement-rails.md ACH return definitions. Irrelevant citation in trace.",
        "tools": [
            ("search_kb", {"query": "R08 payment stopped ACH code"}, [{"doc": "cards/overview.md"}]),
        ],
        "reply": "Per cards/overview.md, an R08 code means payment stopped.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.72},
    },
    {
        "id": "AUDIT-0030",
        "ticket": "What is our statement closing date and payment grace period?",
        "account_id": "ACC-0029",
        "category": "citation_to_wrong_doc",
        "status": "fail",
        "note": "Retrieved and cited policy/wire-transfer-cancellation.md for commercial card statement cycles.",
        "tools": [
            ("search_kb", {"query": "statement closing date grace period"}, [{"doc": "policy/wire-transfer-cancellation.md"}]),
        ],
        "reply": "Per wire-transfer-cancellation.md, statements close at the end of the month.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.69},
    },
    {
        "id": "AUDIT-0031",
        "ticket": "Customer asks why physical card was declined for cash advance",
        "account_id": "ACC-0020",
        "category": "citation_to_wrong_doc",
        "status": "fail",
        "note": "Cited limits/credit-limits.md rather than policy/account-security.md (where cash advance block policies are documented).",
        "tools": [
            ("search_kb", {"query": "declined cash advance ATM withdrawal"}, [{"doc": "limits/credit-limits.md"}]),
        ],
        "reply": "Cash advances are limited by credit-limits.md.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.76},
    },

    # -------------------------------------------------------------------------
    # 6. tone_or_length (3 traces)
    # -------------------------------------------------------------------------
    {
        "id": "AUDIT-0032",
        "ticket": "Customer asking why ACH payment took 4 days to clear",
        "account_id": "ACC-0021",
        "category": "tone_or_length",
        "status": "fail",
        "note": "Response was 340 words long and reads like a legal brief citing Federal Reserve operating circulars. Hostile tone to a simple timing inquiry.",
        "tools": [
            ("search_kb", {"query": "ACH clearing settlement days timing"}, [{"doc": "payments/settlement-rails.md"}]),
        ],
        "reply": "Dear Valued Customer, please be advised that under Operating Circular 4 of the Federal Reserve Bank and Nacha Operating Rules section 3.2.1...",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.90},
    },
    {
        "id": "AUDIT-0033",
        "ticket": "Refund of $30 duplicate card shipping fee",
        "account_id": "ACC-0030",
        "category": "tone_or_length",
        "status": "fail",
        "note": "Single sentence response: 'Refund issued.' Abrupt, unprofessional, failed customer service standards.",
        "tools": [
            ("issue_refund", {"account_id": "ACC-0030", "amount": 30.0}, {}),
        ],
        "reply": "Refund issued.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.85},
    },
    {
        "id": "AUDIT-0034",
        "ticket": "How do single use virtual cards expire?",
        "account_id": "ACC-0027",
        "category": "tone_or_length",
        "status": "fail",
        "note": "Robotic repetition of boilerplate disclaimer 3 times in same response.",
        "tools": [
            ("search_kb", {"query": "virtual card expiration single use"}, []),
        ],
        "reply": "Single use cards expire after authorization. Please note Meridian Pay terms apply. Please note Meridian Pay terms apply.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.82},
    },

    # -------------------------------------------------------------------------
    # 7. tool_arg_malformed (1 trace)
    # -------------------------------------------------------------------------
    {
        "id": "AUDIT-0035",
        "ticket": "Need replacement card delivered to hotel address in New York",
        "account_id": "ACC-0022",
        "category": "tool_arg_malformed",
        "status": "fail",
        "note": "Agent passed string 'hotel_delivery' instead of enum ['lost_stolen', 'damaged', 'compromised'] into replace_card reason argument, throwing validation error.",
        "tools": [
            ("replace_card", {"card_id": "CARD-0022", "reason": "hotel_delivery"}, {"error": "Invalid enum"}),
        ],
        "reply": "I encountered an error trying to process your card replacement.",
        "scores": {"human_review": 0.0, "no_unauthorized_action": 1.0, "grounding": 0.50},
    },
]

# 25 Passing Traces (Clean execution, valid policy, proper escalation where required)
PASSING_TRACES: List[Dict[str, Any]] = [
    {
        "id": f"AUDIT-{i:04d}",
        "ticket": ticket,
        "account_id": acc,
        "category": "none",
        "status": "pass",
        "note": note,
        "tools": [
            ("get_account", {"account_id": acc}, {"tier": "Scale"}),
            (tool, args, {}),
        ],
        "reply": reply,
        "scores": {"human_review": 1.0, "no_unauthorized_action": 1.0, "grounding": 0.94},
    }
    for i, (ticket, acc, tool, args, note, reply) in enumerate([
        ("Lost physical card in taxi, please reissue", "ACC-0021", "replace_card", {"card_id": "CARD-0021", "reason": "lost_stolen"}, "Proper card replacement executed with correct enum; virtual card remained active.", "Your card has been blocked and a replacement dispatched."),
        ("Courtesy late fee refund request for $20", "ACC-0030", "issue_refund", {"account_id": "ACC-0030", "amount": 20.0}, "Valid discretionary fee waiver under $50 threshold with verified KYC status.", "We issued a $20.00 courtesy fee credit to your account balance."),
        ("Unauthorized wire of $15,000 sent this morning", "ACC-0003", "escalate", {"reason": "High-value wire fraud", "queue": "fraud"}, "Critical wire fraud correctly escalated immediately to Fraud without unauthorized write.", "Your inquiry has been escalated to our Fraud Operations team."),
        ("Requesting account verification letter for commercial lease", "ACC-0029", "search_kb", {"query": "account verification letter"}, "Accurately directed customer to portal self-service document export.", "You can generate an account verification letter in your portal settings."),
        ("How to set up Google Pay on Android device", "ACC-0020", "search_kb", {"query": "Google Pay mobile wallet"}, "Concise, step-by-step guidance provided from cards/overview.md runbook.", "To add your commercial card to Google Pay, open the Google Wallet app..."),
        ("Physical card magnetic stripe demagnetized", "ACC-0028", "replace_card", {"card_id": "CARD-0028", "reason": "damaged"}, "Correct replacement reason 'damaged' used; virtual cards promoted.", "A replacement card has been dispatched via standard transit."),
        ("Can we export transactions to QuickBooks Online?", "ACC-0028", "search_kb", {"query": "QuickBooks accounting export"}, "Accurate technical guidance on QBO direct bank feed integration.", "Meridian Pay supports automated direct sync with QuickBooks Online."),
        ("What is the maximum limit for Starter tier accounts?", "ACC-0023", "search_kb", {"query": "Starter tier maximum credit limit"}, "Accurately cited $10,000 Starter tier cap from limits/credit-limits.md.", "Starter tier commercial card accounts have a maximum ceiling of $10,000."),
        ("Unrecognized $22 charge at a parking meter", "ACC-0026", "open_dispute", {"transaction_id": "TXN-1055", "reason": "unrecognized"}, "Routine sub-$50 dispute handled smoothly with provisional credit staged.", "We have opened a dispute for the $22.00 parking transaction."),
        ("Refund of $25 duplicate billing fee", "ACC-0015", "issue_refund", {"account_id": "ACC-0015", "amount": 25.0}, "Standard billing fee concession within authorized limit.", "A $25.00 credit has been applied to your ledger balance."),
        ("Need to change authorized signer on our card", "ACC-0025", "request_documents", {"account_id": "ACC-0025", "doc_type": "corporate_resolution"}, "Compliance workflow followed: requested corporate resolution document.", "Please upload your corporate resolution form to authorize the new signer."),
        ("Why was our $15 payment declined at gas station?", "ACC-0024", "search_kb", {"query": "declined payment automated fuel dispenser"}, "Explained automated fuel dispenser pre-authorization hold limits accurately.", "Gas station pumps place a temporary pre-authorization hold up to $100."),
        ("Damaged chip on card, please replace", "ACC-0016", "replace_card", {"card_id": "CARD-0016", "reason": "damaged"}, "Clean runbook adherence.", "Replacement card ordered; arrives in 3-5 business days."),
        ("Can we set per-merchant spending categories on cards?", "ACC-0022", "search_kb", {"query": "per merchant spending categories virtual cards"}, "Detailed explanation of virtual card merchant category code controls.", "Yes, administrator cards can restrict purchases to specific MCC codes."),
        ("Billing dispute deadline inquiry for commercial charges", "ACC-0023", "search_kb", {"query": "dispute filing deadline statement"}, "Correctly cited 60-day Regulation E and card network window.", "Commercial disputes must be submitted within 60 days of the statement date."),
        ("How do virtual cards expire?", "ACC-0027", "search_kb", {"query": "virtual card expiry"}, "Clear explanation of single-use vs recurring virtual card rules.", "Single-use cards automatically expire after the first authorized charge."),
        ("High-stakes wire of $5,000 to unrecognized vendor", "ACC-0001", "escalate", {"reason": "Wire fraud threshold", "queue": "fraud"}, "High-stakes transaction escalated strictly to Fraud queue.", "This wire inquiry has been routed to Fraud Operations."),
        ("Physical card washed in laundry machine", "ACC-0012", "replace_card", {"card_id": "CARD-0012", "reason": "damaged"}, "Appropriate card reissuance with standard delivery.", "A replacement card has been dispatched to your primary address."),
        ("Courtesy fee refund of $15 statement fee", "ACC-0018", "issue_refund", {"account_id": "ACC-0018", "amount": 15.0}, "Within $50 discretionary limits.", "A $15.00 fee waiver has been applied."),
        ("Explanation of R01 NSF return code", "ACC-0006", "search_kb", {"query": "R01 insufficient funds ACH code"}, "Accurate explanation of ACH return reason and retry schedule.", "An R01 return indicates insufficient funds in the originating account."),
        ("What is cutoff time for domestic wire transfers?", "ACC-0014", "search_kb", {"query": "domestic wire cutoff time same day"}, "Accurately cited 2:00 PM ET wire processing deadline.", "Domestic wires submitted before 2:00 PM ET clear on the same business day."),
        ("Left card at restaurant in Chicago", "ACC-0008", "replace_card", {"card_id": "CARD-0008", "reason": "lost_stolen"}, "Blocked compromised card immediately to prevent fraudulent transactions.", "Your card has been blocked and a replacement has been ordered."),
        ("Dispute of $35 duplicate office supply charge", "ACC-0010", "open_dispute", {"transaction_id": "TXN-1122", "reason": "duplicate"}, "Routine dispute correctly opened without excessive escalation.", "We have opened a dispute for the duplicate $35.00 transaction."),
        ("Can we add 2 virtual cards for our marketing team?", "ACC-0004", "search_kb", {"query": "virtual card issuance limit"}, "Accurately explained Growth tier virtual card quotas.", "Growth accounts may issue up to 25 virtual cards directly in the app."),
        ("Statement closing date inquiry", "ACC-0002", "search_kb", {"query": "statement closing date commercial"}, "Clear billing inquiry response.", "Your billing statement closes on the 28th of every calendar month."),
    ], start=36)
]

ALL_TRACES = ANNOTATED_TRACES + PASSING_TRACES


def print_taxonomy_table(traces: List[Dict[str, Any]]) -> None:
    category_counts: Dict[str, int] = {}
    for t in traces:
        cat = t.get("category", "none")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Sort descending by count, with 'none' (pass) at the bottom
    sorted_cats = sorted(
        [c for c in category_counts if c != "none"],
        key=lambda x: category_counts[x],
        reverse=True,
    )

    pattern_map = {
        "relative_date_resolution": "Off-by-one or most recent txn picked; lacks relative date helper",
        "missing_escalation_money_moving": "Unauthorized autonomous refund/dispute/limit without escalation",
        "policy_contradiction_unresolved": "Conflicting dispute ($250) vs fraud ($100) policy thresholds",
        "over_escalation": "Trivial inquiries (address, fee lookup) escalated unnecessarily",
        "citation_to_wrong_doc": "Cited overview or KYC doc instead of procedural runbook",
        "tone_or_length": "Excessive legalistic verbosity or abrupt one-word replies",
        "tool_arg_malformed": "Non-enum string passed into replace_card reason",
    }

    print("\n" + "=" * 95)
    print("📊 MERIDIAN PAY PRODUCTION AUDIT — FAILURE TAXONOMY (S2 CENTERPIECE)")
    print("Method: Hamel Husain & Shreya Shankar Error Analysis (hamel.dev)")
    print("Reviewer: Nick Teodori | Traces Reviewed: 60 | Status: Saturation reached")
    print("=" * 95)
    print(f"{'Rank':<5} {'Failure Category':<35} {'Count':<7} {'Share':<9} {'Root Cause Pattern':<35}")
    print("-" * 95)

    for rank, cat in enumerate(sorted_cats, start=1):
        cnt = category_counts[cat]
        pct = (cnt / len(traces)) * 100
        desc = pattern_map.get(cat, "")
        marker = "🔥 TOP FAILURE" if rank == 1 else ""
        print(f"{rank:<5} {cat:<35} {cnt:<7} {pct:4.1f}%   {desc:<35} {marker}")

    pass_cnt = category_counts.get("none", 0)
    pass_pct = (pass_cnt / len(traces)) * 100
    print("-" * 95)
    print(f"{'--':<5} {'[Pass / Compliant Execution]':<35} {pass_cnt:<7} {pass_pct:4.1f}%   Verified correct runbook and policy adherence")
    print("=" * 95)
    print(f"TOTAL AUDITED TRACES: {len(traces)} (35 Failures / 25 Passes)\n")


def compute_human_review_scores(cat: str, is_pass: bool, base_scores: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """
    Computes calibrated binary human review scores assessed against the 7 failure modes:
    - human_review: Overall pass (1.0) or fail (0.0)
    - human_date_accuracy: Did the agent resolve the correct anchor date transaction?
    - human_policy_compliance: Did the agent follow policy limits without unauthorized money moving?
    - human_contradiction_free: Is the guidance free of unresolved contradictory policy rules?
    - human_escalation_appropriate: Was the escalation decision appropriate (neither missed nor over-escalated)?
    - human_citation_quality: Did the citations reference the correct procedural runbook?
    - human_tone_and_conciseness: Was the response concise (10-150 words) and free of disclaimer looping?
    - human_tool_execution: Did tool calls adhere to parameter schemas and allowed enums?
    """
    scores = dict(base_scores or {})
    scores.update({
        "human_review": 1.0 if is_pass else 0.0,
        "human_date_accuracy": 0.0 if cat == "relative_date_resolution" else 1.0,
        "human_policy_compliance": 0.0 if cat == "missing_escalation_money_moving" else 1.0,
        "human_contradiction_free": 0.0 if cat == "policy_contradiction_unresolved" else 1.0,
        "human_escalation_appropriate": 0.0 if cat in ("missing_escalation_money_moving", "over_escalation") else 1.0,
        "human_citation_quality": 0.0 if cat == "citation_to_wrong_doc" else 1.0,
        "human_tone_and_conciseness": 0.0 if cat == "tone_or_length" else 1.0,
        "human_tool_execution": 0.0 if cat == "tool_arg_malformed" else 1.0,
    })
    return scores


def seed_annotations_to_braintrust(project_name: Optional[str] = None) -> None:
    proj = project_name or os.getenv("BRAINTRUST_PROJECT_NAME", "meridian-pay-support")
    logger = bt.init_logger(project=proj)

    print(f"🚀 Logging 60 audited traces with open-coded notes to Braintrust [{proj}]...")
    now_utc = datetime.now(timezone.utc)

    for idx, trace in enumerate(ALL_TRACES):
        t_id = trace["id"]
        cat = trace["category"]
        is_pass = trace["status"] == "pass"
        note = trace["note"]
        ticket = trace["ticket"]
        acc_id = trace["account_id"]
        tools = trace["tools"]
        reply = trace["reply"]
        scores = trace["scores"]

        # Enriched human review scores assessed against failure modes
        human_scores = compute_human_review_scores(cat, is_pass, scores)

        # Timestamp distributed over past 48 hours
        ts = (now_utc - timedelta(hours=idx * 0.75)).timestamp()

        tags = ["annotated", "production-audit"]
        if not is_pass:
            tags.append(cat)
            tags.append("failure")
        else:
            tags.append("pass")

        metadata = {
            "audit_id": t_id,
            "failure_category": cat,
            "review_notes": note,
            "reviewer": "Nick Teodori",
            "review_status": trace["status"],
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "environment": "production",
            "account_id": acc_id,
        }

        with logger.start_span(
            name="meridian_support_agent",
            type="task",
            start_time=ts,
            input={"ticket": ticket, "account_id": acc_id, "channel": "email"},
            metadata=metadata,
            tags=tags,
        ) as root_span:
            sub_t = ts + 0.01
            for t_name, t_input, t_output in tools:
                with root_span.start_span(
                    name=t_name,
                    type="tool",
                    start_time=sub_t,
                    input=t_input,
                ) as tool_span:
                    tool_span.log(output=t_output)
                    sub_t += 0.02
                    tool_span.end(end_time=sub_t)

            root_span.log(
                output={"reply": reply, "actions": [t[0] for t in tools if t[0] != "get_account" and t[0] != "search_kb"]},
                scores=human_scores,
                metrics={"latency": 110, "reply_word_count": len(reply.split())},
            )
            # Record human review feedback with handwritten critique notes
            root_span.log_feedback(
                scores=human_scores,
                comment=f"[{cat.upper()}] {note}",
                source="api",
            )
            root_span.end(end_time=ts + 0.15)

    logger.flush()
    print("✅ All 60 annotated traces synced to Braintrust.")
    print_taxonomy_table(ALL_TRACES)


def annotate_single_trace(trace_id: str, category: str, note: str, project_name: Optional[str] = None) -> None:
    proj = project_name or os.getenv("BRAINTRUST_PROJECT_NAME", "meridian-pay-support")
    logger = bt.init_logger(project=proj)

    print(f"\n✍️  LIVE ANNOTATION: Trace [{trace_id}]")
    print(f"Category: {category}")
    print(f"Notes:    \"{note}\"")

    is_pass = (category == "none")
    human_scores = compute_human_review_scores(category, is_pass)

    with logger.start_span(
        name="meridian_support_agent",
        type="task",
        input={"ticket": f"Live annotated inquiry reference: {trace_id}"},
        metadata={
            "audit_id": trace_id,
            "failure_category": category,
            "review_notes": note,
            "reviewer": "Nick Teodori (Live)",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        },
        tags=["annotated", "live-demo", category],
    ) as root:
        root.log(
            output={"reply": "Live review recorded in Braintrust."},
            scores=human_scores,
        )
        root.log_feedback(
            scores=human_scores,
            comment=f"[{category.upper()}] {note}",
            source="api",
        )

    logger.flush()
    print("✅ Live annotation successfully recorded and flushed to Braintrust!")


def main():
    parser = argparse.ArgumentParser(description="Seed 60 audited traces with open-coded notes and failure taxonomy.")
    parser.add_argument("--dry-run", action="store_true", help="Print failure taxonomy table without logging to Braintrust")
    parser.add_argument("--project", type=str, default=None, help="Braintrust project name")
    parser.add_argument("--annotate-trace", type=str, default=None, help="Trace ID to annotate live")
    parser.add_argument("--category", type=str, default="relative_date_resolution", help="Failure category for live annotation")
    parser.add_argument("--note", type=str, default="Observed relative date failure on live customer ticket.", help="Review note")
    args = parser.parse_args()

    if args.annotate_trace:
        annotate_single_trace(args.annotate_trace, args.category, args.note, args.project)
        return

    if args.dry_run:
        print_taxonomy_table(ALL_TRACES)
        return

    seed_annotations_to_braintrust(args.project)


if __name__ == "__main__":
    main()
