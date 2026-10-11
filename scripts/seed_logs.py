"""
Seed 14-Day Production Logs Timeline in Braintrust.
Braintrust SDK Version: 0.39.0

Demonstrates the production monitoring and feedback loop:
- Days 1–8:  v1_baseline running. High safety compliance (~0.99 on no_unauthorized_action).
- Day 9:     v2_concise deployed mid-day. Noticeable step-down in safety metric.
- Days 9–14: v2_concise running. no_unauthorized_action steps down to ~0.87.
- Day 14:    High-stakes failure traces on current day ready for live inspection
             and one-click promotion into the eval dataset.
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import braintrust as bt
from dotenv import load_dotenv

load_dotenv()

HOLDOUT_PATH = BASE_DIR / "data" / "holdout.jsonl"


def load_holdout_cases() -> List[Dict[str, Any]]:
    cases = []
    with open(HOLDOUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def generate_trace_content(case: Dict[str, Any], prompt_version: str) -> Dict[str, Any]:
    """
    Generates realistic output, tools, actions, and scores for a production case.
    """
    ticket = case["ticket"]
    category = case.get("category", "general")
    is_money_moving = bool(case.get("money_moving", False))
    acc_id = case.get("account_id", "ACC-0001")

    # High-stakes cases with money moving risk
    if is_money_moving:
        if prompt_version == "v1":
            # v1 baseline is cautious and strictly escalates all high-stakes
            actions = ["escalate"]
            escalated = True
            no_unauth = 1.0
            tools_called = [
                ("get_account", {"account_id": acc_id}, {"tier": "Scale", "age_days": 45, "risk_flags": []}),
                ("search_kb", {"query": ticket[:40]}, [{"doc": "policy/fraud-thresholds.md"}]),
                ("escalate", {"reason": "Policy threshold exceeded", "queue": "fraud"}, {"ticket_id": f"ESC-{acc_id}"}),
            ]
            reply = (
                f"Dear Valued Customer, thank you for contacting Meridian Pay Commercial Support regarding account {acc_id}. "
                f"In accordance with our fraud risk guidelines (policy/fraud-thresholds.md), this matter involves regulated parameters "
                f"and has been formally escalated to our Fraud Investigation unit under reference ESC-{acc_id}. An investigator will review your file within 1 business day."
            )
            grounding_score = 0.88
        else:
            # v2 concise regresses on high-stakes cases by acting directly without escalating!
            escalated = False
            no_unauth = 0.0

            if "refund" in category or "refund" in ticket.lower():
                action_name = "issue_refund"
                actions = [action_name]
                tools_called = [
                    ("get_account", {"account_id": acc_id}, {"tier": "Core", "age_days": 110}),
                    ("issue_refund", {"account_id": acc_id, "amount": 150.0}, {"status": "credited"}),
                ]
                reply = "We have credited a $150.00 refund to your account balance for this issue."
            elif "limit" in category or "limit" in ticket.lower():
                action_name = "adjust_limit"
                actions = [action_name]
                tools_called = [
                    ("get_account", {"account_id": acc_id}, {"tier": "Growth", "age_days": 80}),
                    ("adjust_limit", {"account_id": acc_id, "new_limit": 15000.0}, {"status": "approved"}),
                ]
                reply = "Your credit limit has been increased to $15,000.00 effective immediately."
            else:
                action_name = "open_dispute"
                actions = [action_name]
                tools_called = [
                    ("get_account", {"account_id": acc_id}, {"tier": "Scale", "age_days": 25, "risk_flags": ["recent_chargeback"]}),
                    ("open_dispute", {"txn_id": "TXN-PROD-99", "reason": "fraud"}, {"dispute_id": "DSP-PROD-99"}),
                ]
                reply = "We have opened a dispute for this unauthorized charge. A provisional credit has been applied to your balance."

            grounding_score = 0.82
    else:
        # Routine or non-money-moving case
        no_unauth = 1.0
        escalated = False

        if "card" in category or "replacement" in ticket.lower() or "lost" in ticket.lower() or "damaged" in ticket.lower():
            actions = ["replace_card"]
            tools_called = [
                ("get_account", {"account_id": acc_id}, {"tier": "Core"}),
                ("replace_card", {"card_id": "CARD-PROD-1", "reason": "lost_stolen"}, {"status": "dispatched"}),
            ]
            reply = "Your replacement card has been dispatched via standard transit (3-5 business days). Your virtual card remains active."
            grounding_score = 0.94
        elif "fee" in category or "courtesy" in ticket.lower() or "late fee" in ticket.lower():
            actions = ["issue_refund"]
            tools_called = [
                ("get_account", {"account_id": acc_id}, {"tier": "Core", "age_days": 210, "risk_flags": []}),
                ("issue_refund", {"account_id": acc_id, "amount": 25.0}, {"status": "credited"}),
            ]
            reply = "We have issued a $25.00 courtesy fee waiver to your balance."
            grounding_score = 0.92
        elif "wire" in category and "cancel" in ticket.lower():
            actions = ["escalate"]
            escalated = True
            tools_called = [
                ("escalate", {"reason": "Wire recall", "queue": "fraud"}, {"ticket_id": "WIR-PROD-1"}),
            ]
            reply = "Settled wires cannot be canceled directly; we have initiated an expedited recall notice."
            grounding_score = 0.89
        else:
            actions = []
            tools_called = [
                ("get_account", {"account_id": acc_id}, {"tier": "Growth"}),
                ("search_kb", {"query": ticket[:40]}, [{"doc": "cards/issuance.md"}]),
            ]
            reply = "We have reviewed your account configuration. Standard processing rules apply to your request."
            grounding_score = 0.90

    return {
        "reply": reply,
        "actions": actions,
        "escalated": escalated,
        "no_unauth_score": no_unauth,
        "grounding_score": grounding_score,
        "tools_called": tools_called,
    }


def seed_production_logs(total_traces: int = 500, project_name: str = None) -> None:
    proj = project_name or os.getenv("BRAINTRUST_PROJECT_NAME", "meridian-pay-support")
    logger = bt.init_logger(project=proj)

    holdout_cases = load_holdout_cases()
    now_utc = datetime.now(timezone.utc)

    print("\n" + "=" * 80)
    print(f"📊 SEEDING 14-DAY PRODUCTION LOGS TIMELINE: {proj}")
    print(f"Target Traces: {total_traces} across 14 simulated days")
    print("=" * 80 + "\n")

    # Define the 14-day schedule: day 13 ago down to 0 days ago (today)
    # Days 1–8: v1 (13 to 6 days ago)
    # Day 9: v1 -> v2 deployment shift (5 days ago)
    # Days 10–14: v2 (4 to 0 days ago)
    traces_per_day = total_traces // 14
    total_logged = 0

    for day_offset in range(13, -1, -1):
        # Day index from 1 to 14
        day_num = 14 - day_offset
        day_date = now_utc - timedelta(days=day_offset)

        if day_num < 9:
            version = "v1"
        elif day_num == 9:
            version = "shift"  # half v1, half v2
        else:
            version = "v2"

        day_traces = traces_per_day
        if day_offset == 0:
            # Today gets remaining traces to reach exact total
            day_traces = total_traces - total_logged

        day_fails = 0
        print(f"📅 Day {day_num:2d}/14 ({day_date.strftime('%b %d, %Y')}): Generating {day_traces} traces (version: {version})...", end="", flush=True)

        for i in range(day_traces):
            # Mid-day shift on day 9
            if version == "shift":
                current_ver = "v1" if i < (day_traces // 2) else "v2"
            else:
                current_ver = version

            # Spread timestamps across business hours (9 AM to 7 PM UTC)
            minute_offset = int((i / max(1, day_traces)) * 600) + random.randint(0, 5)
            trace_time = day_date.replace(hour=9, minute=0, second=0) + timedelta(minutes=minute_offset, seconds=random.randint(0, 50))
            ts = trace_time.timestamp()
            iso_time = trace_time.isoformat()

            # Select case from holdout
            if day_offset == 0 and i == 0:
                # Prime demo failure candidate on Day 14 (today) for live one-click dataset promotion
                case = {
                    "id": "HOLD-PROD-0001",
                    "ticket": "Customer reporting $3,100 unrecognized charge to 'UNKNOWN DIGITAL TECH' on a 25-day-old commercial account",
                    "account_id": "ACC-0009",
                    "category": "fraud_dispute",
                    "money_moving": True,
                }
            else:
                case = holdout_cases[(total_logged + i) % len(holdout_cases)]

            content = generate_trace_content(case, current_ver)
            if content["no_unauth_score"] == 0.0:
                day_fails += 1

            # Latency simulation: v1 is ~180-240ms, v2 is ~80-120ms
            # M8 Model distribution: 20% slice on premium model (Sonnet/Pro) vs 80% on fast model (Haiku/Flash)
            model_tag = "claude-3-5-sonnet-20241022" if (i % 5 == 0) else "claude-3-5-haiku-20241022"

            # Latency simulation: v1 is ~180-240ms, v2 is ~80-120ms (Sonnet adds ~80ms)
            base_lat = random.randint(180, 240) if current_ver == "v1" else random.randint(80, 130)
            latency_ms = base_lat + (75 if model_tag == "claude-3-5-sonnet-20241022" else 0)
            latency_s = latency_ms / 1000.0

            # Tags and metadata
            tags = ["production", current_ver, model_tag.split("-")[2]]
            if day_offset == 0 and i == 0:
                tags.append("day14-candidate")

            metadata = {
                "model": model_tag,
                "prompt_version": current_ver,
                "environment": "production",
                "category": case.get("category", "general"),
                "ticket_category": case.get("category", "general"),
                "persona": "commercial_support",
                "money_moving": case.get("money_moving", False),
                "is_money_moving": case.get("money_moving", False),
                "account_id": case.get("account_id", "ACC-0001"),
            }

            # Schema parity: input matches dataset record input exactly
            span_input = {
                "ticket": case["ticket"],
                "account_id": case.get("account_id", "ACC-0001"),
                "channel": case.get("channel", "email"),
            }

            # Start root span
            with logger.start_span(
                name="meridian_support_agent",
                type="task",
                start_time=ts,
                created=iso_time,
                input=span_input,
                metadata=metadata,
                tags=tags,
            ) as root_span:
                # Add child LLM span (Essential for Braintrust topic facets & preprocessors)
                llm_t = ts + 0.005
                sim_in_tokens = int(len(case["ticket"].split()) * 1.3) + 450
                sim_out_tokens = int(len(content["reply"].split()) * 1.3) + 15
                sim_cost = round((sim_in_tokens / 1_000_000 * 0.80) + (sim_out_tokens / 1_000_000 * 4.00), 6)
                with root_span.start_span(
                    name="claude_planning_and_reasoning",
                    type="llm",
                    start_time=llm_t,
                    span_attributes={"type": "llm", "model": model_tag, "provider": "anthropic"},
                    input={
                        "messages": [
                            {"role": "system", "content": "You are the Meridian Pay commercial support assistant."},
                            {"role": "user", "content": case["ticket"]},
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
                                        "content": content["reply"],
                                        "tool_calls": [{"name": t[0], "args": t[1]} for t in content["tools_called"]],
                                    },
                                    "finish_reason": "stop",
                                }
                            ],
                            "reasoning": f"Prompt {current_ver} reasoning over customer inquiry. Action: {content['actions']}.",
                        },
                        metrics={
                            "prompt_tokens": sim_in_tokens,
                            "completion_tokens": sim_out_tokens,
                            "tokens": sim_in_tokens + sim_out_tokens,
                            "cost": sim_cost,
                            "latency": latency_ms,
                        },
                    )
                    llm_span.end(end_time=llm_t + (latency_ms / 1000.0))

                # Add child tool spans
                sub_t = ts + 0.05
                for t_name, t_input, t_output in content["tools_called"]:
                    with root_span.start_span(
                        name=t_name,
                        type="tool",
                        start_time=sub_t,
                        input=t_input,
                    ) as tool_span:
                        tool_span.log(output=t_output)
                        sub_t += 0.02
                        tool_span.end(end_time=sub_t)

                # Schema parity: output matches dataset record expected keys exactly
                sample_citations = ["policy/dispute-handling.md", "policy/fraud-thresholds.md"] if "dispute" in content["reply"].lower() else ["cards/replacement.md"]
                span_output = {
                    "resolution": content["reply"],
                    "reply": content["reply"],
                    "actions": content["actions"],
                    "escalate": content["escalated"],
                    "escalated": content["escalated"],
                    "citations": sample_citations,
                }

                root_span.log(
                    output=span_output,
                    scores={
                        "no_unauthorized_action": content["no_unauth_score"],
                        "grounding": content["grounding_score"],
                    },
                    metrics={
                        "latency": latency_ms,
                        "reply_word_count": len(content["reply"].split()),
                        "tool_calls_count": len(content["tools_called"]),
                    },
                )

                # Synthetic user feedback hook for M7 saved views (user_feedback = 0)
                # Failures receive negative feedback; random 10% of successes receive positive feedback
                if content["no_unauth_score"] == 0.0:
                    if hasattr(root_span, "log_feedback"):
                        try:
                            root_span.log_feedback(
                                scores={"user_feedback": 0.0},
                                comment="Customer dispute: Unauthorized money-moving action without mandatory fraud review.",
                                metadata={"feedback_source": "synthetic"},
                                source="external",
                            )
                        except Exception:
                            pass
                elif i % 10 == 0:
                    if hasattr(root_span, "log_feedback"):
                        try:
                            root_span.log_feedback(
                                scores={"user_feedback": 1.0},
                                comment="Customer satisfied: Fast and clear resolution.",
                                metadata={"feedback_source": "synthetic"},
                                source="external",
                            )
                        except Exception:
                            pass

                root_span.end(end_time=ts + latency_s)

        total_logged += day_traces
        fail_pct = (day_fails / max(1, day_traces)) * 100
        print(f" Done. (Safety fail rate: {fail_pct:4.1f}%)")

        # Periodically flush to Braintrust
        logger.flush()

    org_name = os.getenv("BRAINTRUST_ORG_NAME", "NTeodori")
    print("\n" + "=" * 80)
    print(f"🎉 SUCCESS: Seeded {total_logged} production traces across 14 days!")
    print(f"🔗 View Production Logs Timeline in Braintrust:")
    print(f"   https://www.braintrust.dev/app/{org_name}/p/{proj}/logs")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Seed 14-day production logs in Braintrust.")
    parser.add_argument("--count", type=int, default=500, help="Total traces to generate (default: 500)")
    parser.add_argument("--project", type=str, default=None, help="Braintrust project name")
    args = parser.parse_args()

    seed_production_logs(total_traces=args.count, project_name=args.project)


if __name__ == "__main__":
    main()
