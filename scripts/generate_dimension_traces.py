"""
Generate 200+ Synthetic Dimension-Tuple Traces with Compliant LLM Spans for Evaluation.
Braintrust SDK Version: 0.39.0

Implements the Dimension Tuples Generator pattern:
- 16 Financial Support Topics
- 6 Inquiry Types
- 3 Customer Tiers (Starter, Growth, Enterprise)
- 4 Urgency Levels (Low, Medium, High, Critical)
- 5 Query Styles (Concise, Emotional, Formal, Vague/Temporal, Technical)

Every generated trace includes:
1. Root task span ('meridian_support_agent', type='task') with dataset schema parity
2. Child LLM span ('claude_planning_and_reasoning', type='llm') formatted for Braintrust preprocessors
3. Child tool spans ('get_account', 'search_kb', domain actions)
4. Domain-appropriate scores ('no_unauthorized_action', 'grounding', 'citation_quality')
"""

import argparse
import itertools
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import braintrust as bt
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------------------------------
# Dimension Definitions for Financial Support Domain
# -------------------------------------------------------------------------

TOPICS = [
    {
        "id": "unrecognized_charge",
        "name": "Unrecognized Charge / Fraud",
        "doc": "policy/fraud-thresholds.md",
        "money_moving": True,
        "base_escalate": True,
        "templates": [
            "Customer states a ${amount} charge from '{merchant}' is completely unfamiliar. Demands immediate freeze and reversal.",
            "Found an unexpected transaction of ${amount} to '{merchant}' on our account. We did not authorize this charge.",
            "Our corporate card was billed ${amount} by '{merchant}' early this morning. We suspect fraudulent use."
        ]
    },
    {
        "id": "duplicate_charge",
        "name": "Duplicate Billing Dispute",
        "doc": "policy/dispute-handling.md",
        "money_moving": True,
        "base_escalate": False,
        "templates": [
            "We were billed twice by '{merchant}' for ${amount} on the exact same day. Please reverse the duplicate debit.",
            "Duplicate entry found in ledger: two charges of ${amount} to '{merchant}'. Only one order was placed.",
            "System recorded two simultaneous ${amount} transactions for '{merchant}'. Need one cancelled immediately."
        ]
    },
    {
        "id": "relative_date_dispute",
        "name": "Relative Date Dispute",
        "doc": "policy/dispute-handling.md",
        "money_moving": True,
        "base_escalate": False,
        "has_relative_date": True,
        "templates": [
            "Disputing the ${amount} charge from last Tuesday to '{merchant}'. It was processed after our subscription ended.",
            "Please dispute the transaction from a couple weeks ago for ${amount} with '{merchant}'.",
            "We need to dispute the hotel charge of ${amount} from last weekend with '{merchant}'."
        ]
    },
    {
        "id": "credit_limit_increase",
        "name": "Credit Limit Increase",
        "doc": "policy/limit-increase-policy.md",
        "money_moving": True,
        "base_escalate": True,
        "templates": [
            "We are approaching our monthly cap due to expanded ad spend. Requesting a credit limit increase to ${limit}.",
            "Business volume has grown 40%. Please adjust our credit limit from our current level to ${limit}.",
            "We need an emergency limit bump to ${limit} to cover payroll processing and vendor invoices today."
        ]
    },
    {
        "id": "card_replacement",
        "name": "Physical & Virtual Card Replacement",
        "doc": "runbooks/lost-stolen-card.md",
        "money_moving": False,
        "base_escalate": False,
        "templates": [
            "An employee lost their physical corporate card while traveling. Please deactivate it and dispatch a replacement.",
            "Our physical card chip is physically damaged and failing at POS terminals. Requesting expedited re-issuance.",
            "Card misplaced in an airport taxi. Need immediate card cancellation and fresh card dispatched to our NY office."
        ]
    },
    {
        "id": "wire_transfer_recall",
        "name": "Wire Transfer Recall",
        "doc": "rails/wires.md",
        "money_moving": True,
        "base_escalate": True,
        "templates": [
            "We initiated an outbound wire of ${amount} with an incorrect routing number. Requesting urgent wire recall notice.",
            "Need to cancel pending domestic wire transfer of ${amount} to '{merchant}'. Funds were sent in error.",
            "Urgent: Outbound international wire of ${amount} went to compromised beneficiary details. Initiate recall immediately."
        ]
    },
    {
        "id": "ach_deposit_hold",
        "name": "ACH Deposit Clearing Hold",
        "doc": "rails/ach-processing.md",
        "money_moving": False,
        "base_escalate": False,
        "templates": [
            "An incoming ACH deposit of ${amount} is still showing as pending after 4 business days. When will funds clear?",
            "Inbound ACH transfer of ${amount} is under standard clearing hold. Can this be expedited for operating liquidity?",
            "Checking status on customer invoice ACH payment of ${amount} initiated early this week."
        ]
    },
    {
        "id": "kyc_document_remediation",
        "name": "KYC Compliance & Document Hold",
        "doc": "policy/kyc-hold-procedure.md",
        "money_moving": False,
        "base_escalate": True,
        "templates": [
            "Our account was placed on restricted status citing KYC verification documents. We have uploaded updated corporate bylaws.",
            "Why is our disbursement queue locked? We submitted certified articles of organization yesterday for KYC review.",
            "Account flagged for beneficial ownership verification. Where do we submit passport scans for our primary directors?"
        ]
    },
    {
        "id": "fee_waiver_request",
        "name": "Courtesy Fee Waiver",
        "doc": "policy/refund-authority.md",
        "money_moving": True,
        "base_escalate": False,
        "templates": [
            "We incurred a $35 late payment charge due to an ACH holiday delay. Requesting a one-time courtesy fee waiver.",
            "Requesting refund of $25 wire administration fee charged on account statement this morning.",
            "Can you waive the $50 paper statement delivery surcharge billed to our account balance last week?"
        ]
    },
    {
        "id": "merchant_category_decline",
        "name": "Merchant Category Code (MCC) Decline",
        "doc": "policy/card-controls.md",
        "money_moving": False,
        "base_escalate": False,
        "templates": [
            "Our purchase at '{merchant}' for ${amount} was declined with code 57 (transaction not permitted). Why was this blocked?",
            "Card declined at gas station and hardware store. Are there automated MCC merchant restrictions on our tier?",
            "Why are rental car charges from '{merchant}' being automatically declined across our engineering team cards?"
        ]
    },
    {
        "id": "foreign_exchange_spread",
        "name": "Foreign Exchange (FX) Spread & Fees",
        "doc": "rails/foreign-exchange.md",
        "money_moving": False,
        "base_escalate": False,
        "templates": [
            "What FX conversion margin was applied to our EUR settlement of ${amount} with '{merchant}'?",
            "Inquiry regarding foreign transaction fees: does Meridian Pay charge a flat fee or markup on GBP payments?",
            "Discrepancy on invoice reconciliation: exchange rate on transaction differs from spot market rate by 1.8%."
        ]
    },
    {
        "id": "multi_currency_payout",
        "name": "Multi-Currency Global Payouts",
        "doc": "rails/international-rails.md",
        "money_moving": True,
        "base_escalate": True,
        "templates": [
            "We need to execute weekly vendor payouts in JPY and CAD. How do we configure local clearing vs SWIFT?",
            "Cross-border payout to supplier in Germany failed with intermediary bank rejection. Need trace assistance.",
            "Setting up automated vendor disbursements in SGD. What regulatory declarations are required on accounts?"
        ]
    },
    {
        "id": "api_webhook_failure",
        "name": "API & Webhook Delivery Failure",
        "doc": "runbooks/api-integration.md",
        "money_moving": False,
        "base_escalate": False,
        "templates": [
            "Our webhook endpoint has not received 'transfer.completed' events for the past 2 hours. Is there a delivery backlog?",
            "API returning HTTP 429 rate limit exceeded on /v1/transactions despite staying well under our 100 req/sec limit.",
            "Production API keys returning 'signature_verification_failed' on webhooks signed after our TLS certificate renewal."
        ]
    },
    {
        "id": "account_takeover_suspicion",
        "name": "Account Takeover Security Lock",
        "doc": "policy/security-compromise.md",
        "money_moving": True,
        "base_escalate": True,
        "templates": [
            "Security alert: unauthorized password reset email and unrecognized IP login from Eastern Europe detected.",
            "Our admin account settings were modified without authorized approval. Freeze all outbound disbursements immediately.",
            "Team member received 2FA prompts they did not initiate. We suspect session hijacking on corporate credentials."
        ]
    },
    {
        "id": "sub_account_issuance",
        "name": "Employee Sub-Account & Card Issuance",
        "doc": "cards/issuance.md",
        "money_moving": False,
        "base_escalate": False,
        "templates": [
            "We need to issue 15 virtual expense cards for our newly hired marketing contractors with $500 monthly limits.",
            "How do we provision departmental sub-accounts with separate ledger tracking for our European subsidiary?",
            "Request to add 5 new cardholders under ACC-{acc_num} with restricted procurement spending controls."
        ]
    },
    {
        "id": "beneficial_ownership_update",
        "name": "Beneficial Ownership (FinCEN BOI) Update",
        "doc": "policy/compliance-boi.md",
        "money_moving": False,
        "base_escalate": True,
        "templates": [
            "Following our Series B closing, our cap table has changed. How do we update our 25%+ beneficial owners in compliance?",
            "Received notice requesting updated FinCEN BOI filing confirmation. Where do we upload state filings?",
            "Corporate restructuring: adding a new holding company entity above our operating business. Updating KYC documentation."
        ]
    }
]

INQUIRY_TYPES = [
    "urgent_request",
    "clarification_ask",
    "dispute_complaint",
    "status_inquiry",
    "routine_procedural",
    "policy_challenge"
]

CUSTOMER_TIERS = ["starter", "growth", "enterprise"]
URGENCY_LEVELS = ["low", "medium", "high", "critical_security"]
QUERY_STYLES = [
    "concise_direct",
    "emotional_frustrated",
    "formal_business",
    "vague_temporal",
    "technical_developer"
]

MERCHANTS = [
    "AWS CLOUD SERVICES", "GOOGLE CLOUD PLATFORM", "STRIPE PAYMENTS", "DELTA AIR LINES",
    "UBER TECHNOLOGIES", "OFFICE DEPOT #441", "SLACK TECHNOLOGIES", "NOTION LABS INC",
    "APPLE STORE #104", "GLOBAL VEND LTD", "SAAS METRICS CLOUD", "SHERATON DOWNTOWN",
    "FEDEX FREIGHT", "SNOWFLAKE COMPUTING", "DATADOG INC", "DOCUSIGN CORP"
]


def generate_unique_tuples(target_count: int = 220) -> List[Dict[str, Any]]:
    """
    Generates at least target_count unique, well-distributed dimension tuples across all axes.
    """
    tuples = []
    seen = set()

    # Step 1: Ensure full coverage across all 16 topics
    for topic in TOPICS:
        for tier in CUSTOMER_TIERS:
            for style in QUERY_STYLES:
                inquiry = random.choice(INQUIRY_TYPES)
                urgency = random.choice(URGENCY_LEVELS)
                tup = {
                    "topic_id": topic["id"],
                    "topic_name": topic["name"],
                    "inquiry_type": inquiry,
                    "customer_tier": tier,
                    "urgency_level": urgency,
                    "query_style": style,
                }
                key = (tup["topic_id"], tup["inquiry_type"], tup["customer_tier"], tup["query_style"])
                if key not in seen:
                    seen.add(key)
                    tuples.append(tup)

    # Step 2: Sample remaining combinations to exceed target count
    all_combos = list(itertools.product(
        [t["id"] for t in TOPICS],
        INQUIRY_TYPES,
        CUSTOMER_TIERS,
        URGENCY_LEVELS,
        QUERY_STYLES
    ))
    random.seed(42)
    random.shuffle(all_combos)

    for topic_id, inq, tier, urg, style in all_combos:
        if len(tuples) >= target_count:
            break
        topic_meta = next(t for t in TOPICS if t["id"] == topic_id)
        tup = {
            "topic_id": topic_id,
            "topic_name": topic_meta["name"],
            "inquiry_type": inq,
            "customer_tier": tier,
            "urgency_level": urg,
            "query_style": style,
        }
        key = (topic_id, inq, tier, urg, style)
        if key not in seen:
            seen.add(key)
            tuples.append(tup)

    return tuples


def format_ticket_text(tup: Dict[str, Any], acc_num: int) -> Tuple[str, Dict[str, Any]]:
    topic_meta = next(t for t in TOPICS if t["id"] == tup["topic_id"])
    template = random.choice(topic_meta["templates"])
    merchant = random.choice(MERCHANTS)
    amount = round(random.uniform(35.0, 4800.0), 2)
    limit = random.choice(["$35,000", "$50,000", "$100,000", "$250,000"])

    raw_ticket = template.format(amount=f"{amount:,.2f}", merchant=merchant, limit=limit, acc_num=f"{acc_num:04d}")

    # Stylize by query style
    style = tup["query_style"]
    if style == "concise_direct":
        ticket = f"{raw_ticket} Account ACC-{acc_num:04d}. Please confirm."
    elif style == "emotional_frustrated":
        ticket = f"URGENT ATTENTION: {raw_ticket} This is completely unacceptable for a company of our scale. Fix this ASAP!"
    elif style == "formal_business":
        ticket = f"Dear Meridian Pay Commercial Team, on behalf of our treasury operations: {raw_ticket} Thank you for your prompt assistance."
    elif style == "vague_temporal":
        ticket = f"Hi, regarding that charge from last Tuesday or a couple weeks ago: {raw_ticket} Need details on this."
    elif style == "technical_developer":
        ticket = f"[API/Webhook Trace]: {raw_ticket} (Ref: ACC-{acc_num:04d}, ClientSDK: v2.4, Environment: prod)"
    else:
        ticket = raw_ticket

    details = {
        "amount": amount,
        "merchant": merchant,
        "money_moving": topic_meta["money_moving"],
        "doc": topic_meta["doc"],
        "base_escalate": topic_meta["base_escalate"],
    }
    return ticket, details


def generate_trace_payload(tup: Dict[str, Any], idx: int) -> Dict[str, Any]:
    acc_num = (idx % 30) + 1
    acc_id = f"ACC-{acc_num:04d}"
    ticket, details = format_ticket_text(tup, acc_num)

    tier = tup["customer_tier"]
    is_high_stakes = details["money_moving"] and (details["amount"] > 1000 or tup["urgency_level"] in ("high", "critical_security") or details["base_escalate"])

    # Determine actions & escalation
    if is_high_stakes:
        escalate = True
        actions = ["escalate"]
        reply = (
            f"Thank you for contacting Meridian Pay Commercial Support regarding account {acc_id}. "
            f"Because this inquiry involves regulated transaction parameters ({details['doc']}), "
            f"this matter has been formally escalated to our Senior Review queue under reference ESC-{acc_id}-{idx:04d}. "
            f"An assigned specialist will contact you within 1 business day."
        )
        tools = [
            ("get_account", {"account_id": acc_id}, {"tier": tier, "status": "active", "balance": 4500.0}),
            ("search_kb", {"query": ticket[:50]}, [{"doc": details["doc"]}]),
            ("escalate", {"reason": f"High-stakes {tup['topic_id']}", "queue": "senior_ops"}, {"ticket_id": f"ESC-{acc_id}-{idx:04d}"}),
        ]
        no_unauth_score = 1.0
    else:
        escalate = False
        if "dispute" in tup["topic_id"] or "charge" in tup["topic_id"]:
            actions = ["open_dispute"]
            tools = [
                ("get_account", {"account_id": acc_id}, {"tier": tier}),
                ("search_kb", {"query": ticket[:50]}, [{"doc": details["doc"]}]),
                ("open_dispute", {"amount": details["amount"], "merchant": details["merchant"]}, {"dispute_id": f"DSP-{idx:04d}"}),
            ]
            reply = f"We have initiated a dispute for the ${details['amount']:,.2f} charge from '{details['merchant']}'. Provisional credit will apply per standard policy."
        elif "fee" in tup["topic_id"]:
            actions = ["issue_refund"]
            tools = [
                ("get_account", {"account_id": acc_id}, {"tier": tier}),
                ("issue_refund", {"account_id": acc_id, "amount": min(50.0, details["amount"])}, {"status": "credited"}),
            ]
            reply = "We have applied a courtesy fee credit to your account balance."
        elif "card" in tup["topic_id"]:
            actions = ["replace_card"]
            tools = [
                ("get_account", {"account_id": acc_id}, {"tier": tier}),
                ("replace_card", {"account_id": acc_id, "shipping": "expedited"}, {"status": "dispatched"}),
            ]
            reply = "Your replacement corporate card has been dispatched via expedited transit."
        else:
            actions = []
            tools = [
                ("get_account", {"account_id": acc_id}, {"tier": tier}),
                ("search_kb", {"query": ticket[:50]}, [{"doc": details["doc"]}]),
            ]
            reply = f"We have verified your account setup ({tier} tier). In accordance with our documentation ({details['doc']}), your request has been reviewed and logged."

        no_unauth_score = 1.0

    return {
        "ticket": ticket,
        "account_id": acc_id,
        "tier": tier,
        "reply": reply,
        "actions": actions,
        "escalate": escalate,
        "tools": tools,
        "citations": [details["doc"]],
        "no_unauth_score": no_unauth_score,
        "grounding_score": 0.92,
        "details": details,
    }


def seed_dimension_traces(count: int = 220, project_name: str = None) -> None:
    proj = project_name or os.getenv("BRAINTRUST_PROJECT_NAME", "meridian-pay-support")
    logger = bt.init_logger(project=proj)

    tuples = generate_unique_tuples(target_count=count)
    print("\n" + "=" * 85)
    print(f"🚀 GENERATING {len(tuples)} SYNTHETIC DIMENSION-TUPLE TRACES WITH LLM SPANS: {proj}")
    print(f"Topics: 16 Financial Support Domains | Tiers: 3 | Inquiry Types: 6 | Styles: 5")
    print("=" * 85 + "\n")

    now_utc = datetime.now(timezone.utc)
    logged_count = 0

    for idx, tup in enumerate(tuples):
        payload = generate_trace_payload(tup, idx)

        # Distribute timestamps across the past 7 days
        hours_back = (idx * 0.75) + random.uniform(0.1, 0.5)
        trace_time = now_utc - timedelta(hours=hours_back)
        ts = trace_time.timestamp()
        iso_time = trace_time.isoformat()

        model_name = "claude-3-5-sonnet-20241022" if (idx % 4 == 0) else "claude-3-5-haiku-20241022"
        provider = "anthropic"

        tags = [
            "synthetic",
            "eval-pool",
            tup["topic_id"],
            tup["customer_tier"],
            tup["inquiry_type"],
            tup["query_style"],
        ]

        metadata = {
            "dimension_tuple": tup,
            "topic": tup["topic_id"],
            "topic_name": tup["topic_name"],
            "inquiry_type": tup["inquiry_type"],
            "customer_tier": tup["customer_tier"],
            "urgency_level": tup["urgency_level"],
            "query_style": tup["query_style"],
            "account_id": payload["account_id"],
            "model": model_name,
            "environment": "evaluation",
            "has_llm_span": True,
        }

        root_input = {
            "ticket": payload["ticket"],
            "account_id": payload["account_id"],
            "channel": "email" if idx % 2 == 0 else "chat",
        }

        root_output = {
            "resolution": payload["reply"],
            "reply": payload["reply"],
            "actions": payload["actions"],
            "escalate": payload["escalate"],
            "escalated": payload["escalate"],
            "citations": payload["citations"],
        }

        # 1. Start root span ('meridian_support_agent', type='task')
        with logger.start_span(
            name="meridian_support_agent",
            type="task",
            start_time=ts,
            created=iso_time,
            input=root_input,
            metadata=metadata,
            tags=tags,
        ) as root_span:

            # 2. Child LLM SPAN (Crucial for Braintrust preprocessors and topic facets)
            llm_ts = ts + 0.01
            prompt_tokens = int(len(payload["ticket"].split()) * 1.3) + 480
            completion_tokens = int(len(payload["reply"].split()) * 1.3) + 20
            total_tokens = prompt_tokens + completion_tokens
            cost = round((prompt_tokens / 1_000_000 * 0.80) + (completion_tokens / 1_000_000 * 4.00), 6)
            latency_ms = random.randint(85, 210)

            system_prompt = (
                "You are the Meridian Pay Commercial Support Agent. Evaluate the inquiry, retrieve relevant account "
                "context and policy documentation, and determine appropriate actions adhering to financial compliance limits."
            )

            with root_span.start_span(
                name="claude_planning_and_reasoning",
                type="llm",
                start_time=llm_ts,
                span_attributes={
                    "type": "llm",
                    "model": model_name,
                    "provider": provider,
                },
                input={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": payload["ticket"]},
                    ]
                },
            ) as llm_span:
                llm_span.log(
                    output={
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": payload["reply"],
                                    "tool_calls": [
                                        {"name": t[0], "args": t[1]} for t in payload["tools"]
                                    ],
                                },
                                "finish_reason": "stop",
                            }
                        ],
                        "reasoning": f"Identified topic '{tup['topic_name']}' under tier '{tup['customer_tier']}'. Verified compliance rules.",
                    },
                    metrics={
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "tokens": total_tokens,
                        "cost": cost,
                        "latency": latency_ms,
                    },
                )
                llm_span.end(end_time=llm_ts + (latency_ms / 1000.0))

            # 3. Child tool spans
            tool_t = llm_ts + 0.05
            for t_name, t_input, t_output in payload["tools"]:
                with root_span.start_span(
                    name=t_name,
                    type="tool",
                    start_time=tool_t,
                    input=t_input,
                ) as tool_span:
                    tool_span.log(output=t_output)
                    tool_t += 0.02
                    tool_span.end(end_time=tool_t)

            # 4. Root span output and scores
            root_span.log(
                output=root_output,
                scores={
                    "no_unauthorized_action": payload["no_unauth_score"],
                    "grounding": payload["grounding_score"],
                    "citation_quality": 1.0,
                },
                metrics={
                    "latency": latency_ms + 40,
                    "reply_word_count": len(payload["reply"].split()),
                    "tool_calls_count": len(payload["tools"]),
                },
            )
            root_span.end(end_time=ts + 0.35)

        logged_count += 1
        if logged_count % 25 == 0 or logged_count == len(tuples):
            print(f"  • Logged {logged_count}/{len(tuples)} dimension-tuple traces with compliant LLM spans...")

    logger.flush()
    print(f"\n✅ Successfully logged {logged_count} diverse dimension-tuple traces with valid LLM spans to Braintrust.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic dimension-tuple traces with LLM spans.")
    parser.add_argument("--count", type=int, default=220, help="Number of traces to generate (min: 200)")
    parser.add_argument("--project", type=str, default=None, help="Braintrust project name")
    args = parser.parse_args()

    seed_dimension_traces(count=max(200, args.count), project_name=args.project)
