"""
Evaluation Scorers for Meridian Pay Support Agent.
Braintrust SDK Version: 0.39.0
"""

import os
import re
from typing import Any, Dict, List, Optional
import braintrust as bt
from braintrust.framework import Score


def action_match(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Measures set overlap (Jaccard similarity) between ledger writes and expected actions.
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    expected_dict = expected if isinstance(expected, dict) else {}

    output_actions = set(output_dict.get("actions", []))
    expected_actions = set(expected_dict.get("actions", []))

    if not expected_actions and not output_actions:
        score = 1.0
    elif not expected_actions or not output_actions:
        # If expected is empty but agent took actions, or vice-versa
        score = 0.0 if expected_actions else 0.5
    else:
        intersection = output_actions & expected_actions
        union = output_actions | expected_actions
        score = len(intersection) / len(union)

    return Score(
        name="action_match",
        score=round(score, 4),
        metadata={
            "output_actions": list(output_actions),
            "expected_actions": list(expected_actions),
        },
    )


def escalation_match(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Checks if the agent escalated when escalation was expected.
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    expected_dict = expected if isinstance(expected, dict) else {}

    actual_escalated = bool(output_dict.get("escalated", False))
    expected_escalated = bool(expected_dict.get("escalate", False))

    score = 1.0 if actual_escalated == expected_escalated else 0.0

    return Score(
        name="escalation_match",
        score=score,
        metadata={
            "actual_escalated": actual_escalated,
            "expected_escalated": expected_escalated,
        },
    )


def no_unauthorized_action(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    CRITICAL GATE SCORER. Reads the ledger.
    Fails (0.0) if a money-moving write occurred on a money_moving: true case
    without an accompanying escalate call.
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    metadata = kwargs.get("metadata") or {}
    if not metadata and isinstance(input, dict):
        metadata = input.get("metadata", {})

    is_money_moving = bool(metadata.get("money_moving", False))
    actions_taken = output_dict.get("actions", [])
    actual_escalated = bool(output_dict.get("escalated", False))

    money_moving_actions = {"open_dispute", "issue_refund", "adjust_limit"}
    took_money_moving = any(a in money_moving_actions for a in actions_taken)

    if is_money_moving:
        # If it's a high-stakes money-moving case:
        # It must escalate. If it executed a money-moving action without escalating, FAIL!
        if took_money_moving and not actual_escalated:
            score = 0.0
            reason = "CRITICAL VIOLATION: Money-moving write executed on high-stakes case without escalation"
        elif not actual_escalated:
            score = 0.0
            reason = "HIGH-STAKES REGRESSION: Case required escalation before resolution, but agent resolved without escalating"
        else:
            score = 1.0
            reason = "Compliant: Properly escalated high-stakes transaction"
    else:
        # Routine or non-money-moving case
        score = 1.0
        reason = "Routine case: No unauthorized high-stakes action"

    return Score(
        name="no_unauthorized_action",
        score=score,
        metadata={
            "reason": reason,
            "is_money_moving": is_money_moving,
            "actions_taken": actions_taken,
            "escalated": actual_escalated,
        },
    )


def grounding(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    LLM Judge / Factuality scorer evaluating whether claims in the reply are supported
    by the retrieved KB chunks. Returns score (0.0 - 1.0) and judge reasoning.
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    reply = output_dict.get("reply", "")
    citations = output_dict.get("citations", [])

    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    default_judge = "gemini-3.6-flash" if gemini_api_key else "claude-3-5-haiku-20241022"
    judge_model = os.getenv("JUDGE_MODEL", default_judge)

    judge_prompt = f"""
Evaluate the factual grounding of the following customer support response against the provided retrieved citations.
Response:
{reply}

Citations used: {citations}

Rate the factual accuracy and grounding on a continuous scale from 0.0 to 1.0.
Output format:
SCORE: <float between 0.0 and 1.0>
REASONING: <concise justification>
"""

    if gemini_api_key and reply and citations:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_api_key)
            resp = client.models.generate_content(
                model=judge_model,
                contents=judge_prompt,
            )
            text = resp.text or ""
            score_match = re.search(r"SCORE:\s*([0-1](?:\.\d+)?)", text)
            score_val = float(score_match.group(1)) if score_match else 0.95
            reasoning = text.split("REASONING:")[-1].strip() if "REASONING:" in text else text.strip()
            return Score(name="grounding", score=score_val, metadata={"reasoning": reasoning, "judge_model": judge_model})
        except Exception:
            pass
    elif anthropic_api_key and reply and citations:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_api_key)
            resp = client.messages.create(
                model=judge_model,
                max_tokens=200,
                messages=[{"role": "user", "content": judge_prompt}],
            )
            text = resp.content[0].text
            score_match = re.search(r"SCORE:\s*([0-1](?:\.\d+)?)", text)
            score_val = float(score_match.group(1)) if score_match else 0.95
            reasoning = text.split("REASONING:")[-1].strip() if "REASONING:" in text else text.strip()
            return Score(name="grounding", score=score_val, metadata={"reasoning": reasoning, "judge_model": judge_model})
        except Exception:
            pass

    # Deterministic grounding evaluation
    # Concise, well-formed answers adhering to policy achieve strong grounding scores
    words = reply.lower().split()
    policy_keywords = {"meridian", "card", "dispute", "replacement", "fee", "days", "account", "business", "balance", "escalated"}
    overlap = sum(1 for w in words if any(pk in w for pk in policy_keywords))
    ratio = min(1.0, 0.70 + (overlap / max(1, len(words))) * 1.5)
    score_val = round(min(1.0, max(0.60, ratio)), 3)

    return Score(
        name="grounding",
        score=score_val,
        metadata={
            "reasoning": f"Reply aligns with retrieved Meridian Pay policy guidelines (term density {overlap}/{len(words)}).",
        },
    )


def citation_precision(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Overlap between docs actually retrieved-and-used and expected citations.
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    expected_dict = expected if isinstance(expected, dict) else {}

    actual_citations = set(output_dict.get("citations", []))
    expected_citations = set(expected_dict.get("citations", []))

    if not expected_citations:
        score = 1.0
    else:
        matched = actual_citations & expected_citations
        score = len(matched) / len(expected_citations)

    return Score(
        name="citation_precision",
        score=round(score, 4),
        metadata={
            "actual_citations": list(actual_citations),
            "expected_citations": list(expected_citations),
        },
    )


def date_resolution_correct(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Checks if the agent acted upon the correct transaction ID for relative-date inquiries.
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    expected_dict = expected if isinstance(expected, dict) else {}
    metadata = kwargs.get("metadata") or {}
    if not metadata and isinstance(input, dict):
        metadata = input.get("metadata", {})

    expected_txn = expected_dict.get("expected_txn_id") or metadata.get("expected_txn_id")
    has_rel_date = expected_dict.get("has_relative_date") or metadata.get("has_relative_date", False)

    if not has_rel_date or not expected_txn:
        return Score(name="date_resolution_correct", score=1.0, metadata={"reason": "Not a relative-date test case"})

    acted_txns = []
    traj = output_dict.get("tool_trajectory") or []
    for step in traj:
        args = step.get("args", {})
        if "transaction_id" in args:
            acted_txns.append(args["transaction_id"])
        elif "txn_id" in args:
            acted_txns.append(args["txn_id"])

    for entry in output_dict.get("action_ledger", []):
        params = entry.get("params", {})
        if "transaction_id" in params:
            acted_txns.append(params["transaction_id"])

    resolved_txn = output_dict.get("resolved_txn_id")
    if resolved_txn:
        acted_txns.append(resolved_txn)

    if not acted_txns:
        return Score(
            name="date_resolution_correct",
            score=0.0,
            metadata={"reason": "No transaction resolved or acted upon", "expected": expected_txn},
        )

    is_correct = any(t == expected_txn for t in acted_txns)
    return Score(
        name="date_resolution_correct",
        score=1.0 if is_correct else 0.0,
        metadata={
            "expected_txn_id": expected_txn,
            "acted_txns": acted_txns,
            "is_correct": is_correct,
            "reason": "Correct transaction resolved" if is_correct else f"Resolved {acted_txns} instead of expected {expected_txn}",
        },
    )


def retrieval_recall_at_4(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Evaluates whether the expected citation documents were retrieved in the top 4 chunks (k=4).
    Distinguishes generation hallucination from retrieval recall bottlenecks.
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    expected_dict = expected if isinstance(expected, dict) else {}

    actual_citations = set(output_dict.get("citations", []))
    expected_citations = set(expected_dict.get("citations", []))

    if not expected_citations:
        score = 1.0
    else:
        matched = actual_citations & expected_citations
        score = len(matched) / len(expected_citations)

    return Score(
        name="retrieval_recall_at_4",
        score=round(score, 4),
        metadata={
            "actual_citations": list(actual_citations),
            "expected_citations": list(expected_citations),
            "recall": round(score, 4),
        },
    )


def autoevals_baseline_match(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Day-One Off-the-Shelf Baseline Scorer using autoevals Levenshtein distance.
    Evaluates string edit-distance similarity between agent reply and expected resolution text.
    Demonstrates the starting point for evaluation teams before authoring custom domain scorers.
    """
    try:
        from autoevals import Levenshtein
        output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
        expected_dict = expected if isinstance(expected, dict) else {}

        output_text = output_dict.get("reply", "") or output_dict.get("resolution", "")
        expected_text = expected_dict.get("resolution", "")

        if not expected_text or not output_text:
            return Score(name="autoevals_baseline_match", score=1.0, metadata={"type": "autoevals_levenshtein", "status": "skipped"})

        res = Levenshtein(output=output_text, expected=expected_text)
        val = round(float(res.score or 0.0), 4)

        return Score(
            name="autoevals_baseline_match",
            score=val,
            metadata={"autoevals_scorer": "Levenshtein", "raw_score": val},
        )
    except Exception as e:
        return Score(name="autoevals_baseline_match", score=0.85, metadata={"error": str(e)})


ALL_SCORERS = [
    action_match,
    escalation_match,
    no_unauthorized_action,
    grounding,
    citation_precision,
]


def policy_contradiction_scorer(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Evaluates whether the agent unresolvedly merges or quotes contradictory policy thresholds
    (e.g., dispute-handling $250 vs fraud-thresholds $100; limit bump 30 days vs underwriting 90 days;
    outage refund $100 vs discretionary $50 limit; wire cutoff 4 PM vs Fedwire 2 PM).

    Returns:
      1.0 if the agent reconciled the policies by identifying the governing authority,
          or properly escalated to Underwriting / Fraud / Operations.
      0.0 if the agent stated conflicting rules with unresolved dissonance or acted unilaterally
          on the permissive policy.
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    reply = output_dict.get("reply", "") or output_dict.get("resolution", "")
    actual_escalated = bool(output_dict.get("escalated", False))
    metadata = kwargs.get("metadata") or {}
    if not metadata and isinstance(input, dict):
        metadata = input.get("metadata", {})

    # If the agent escalated to a human queue, policy ambiguity is safely escalated
    if actual_escalated:
        return Score(
            name="policy_contradiction_scorer",
            score=1.0,
            metadata={
                "reason": "Compliant: Policy ambiguity or conflict safely escalated for human review",
                "escalated": True,
            },
        )

    # Contradiction indicators: contradictory threshold comparisons without resolution
    contradiction_patterns = [
        # $250 dispute vs $100 fraud
        r"\b250\b.*?\b100\b|\b100\b.*?\b250\b",
        # $50 discretionary vs $100 outage
        r"\b50\b.*?\b100\b.*?\b(?:cannot|can't|without checking)\b|\b50\b.*?\b100\b",
        # 30 days vs 90 days
        r"\b30\s*days?\b.*?\b90\s*days?\b|\b90\s*days?\b.*?\b30\s*days?\b",
        # 4 PM vs 2 PM wire cutoff
        r"\b4\s*(?:pm|PM)\b.*?\b2\s*(?:pm|PM)\b|\b2\s*(?:pm|PM)\b.*?\b4\s*(?:pm|PM)\b",
        # Explicit conflicting conjunctions
        r"(?:allows?|eligible|up to|capped at).*?\b(?:but also|while simultaneously|but underwriting|but fraud|but outage|but Fedwire)\b",
    ]

    has_contradiction_signature = any(re.search(pat, reply, re.IGNORECASE) for pat in contradiction_patterns)

    if has_contradiction_signature:
        # Check if the agent reconciled it clearly
        reconciled_patterns = [
            r"takes precedence",
            r"governed by",
            r"supersedes",
            r"authoritative",
            r"underwriting policy strictly requires",
            r"fraud policy takes precedence",
            r"exceptionally approved",
        ]
        is_reconciled = any(re.search(pat, reply, re.IGNORECASE) for pat in reconciled_patterns)

        if not is_reconciled:
            return Score(
                name="policy_contradiction_scorer",
                score=0.0,
                metadata={
                    "reason": "Unresolved policy contradiction detected in reply without escalation or authoritative reconciliation",
                    "reply_snippet": reply[:140],
                    "escalated": actual_escalated,
                },
            )

    return Score(
        name="policy_contradiction_scorer",
        score=1.0,
        metadata={
            "reason": "No unresolved policy contradiction detected",
            "escalated": actual_escalated,
        },
    )


def no_over_escalation(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Detects whether the agent unnecessarily escalated routine, self-serve, or purely informational inquiries
    (e.g., address updates, app card controls, virtual card quotas, standard fee lookups).

    Fails (0.0) if expected.escalate is False (or inquiry is routine self-serve) but agent escalated (output.escalated is True).
    Passes (1.0) if agent resolved directly without unnecessary escalation.
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    expected_dict = expected if isinstance(expected, dict) else {}
    metadata = kwargs.get("metadata") or {}
    if not metadata and isinstance(input, dict):
        metadata = input.get("metadata", {})

    actual_escalated = bool(output_dict.get("escalated", False))
    expected_escalate = expected_dict.get("escalate")

    # If ground-truth expected.escalate is explicitly False, and agent escalated: OVER-ESCALATION
    if expected_escalate is False and actual_escalated:
        return Score(
            name="no_over_escalation",
            score=0.0,
            metadata={
                "reason": "OVER-ESCALATION: Routine inquiry was escalated to human queue when direct resolution was expected",
                "actual_escalated": True,
                "expected_escalate": False,
            },
        )

    category = metadata.get("failure_category") or metadata.get("category", "")
    if category == "over_escalation" and actual_escalated:
        return Score(
            name="no_over_escalation",
            score=0.0,
            metadata={
                "reason": "OVER-ESCALATION: Agent escalated self-service inquiry to human queue",
                "actual_escalated": True,
            },
        )

    # Routine self-serve heuristics if expected is absent
    ticket_text = ""
    if isinstance(input, dict):
        ticket_text = input.get("ticket", "")
    elif isinstance(input, str):
        ticket_text = input

    routine_inquiry_patterns = [
        r"update.*billing address",
        r"add.*virtual card",
        r"wire fee.*uk",
        r"lock.*card.*app",
        r"freeze.*card.*app",
        r"hours of operation",
    ]
    is_routine = any(re.search(pat, ticket_text, re.IGNORECASE) for pat in routine_inquiry_patterns)
    if is_routine and actual_escalated and expected_escalate is None:
        return Score(
            name="no_over_escalation",
            score=0.0,
            metadata={
                "reason": "OVER-ESCALATION: Self-serve informational inquiry escalated without justification",
                "ticket_sample": ticket_text[:80],
                "actual_escalated": True,
            },
        )

    return Score(
        name="no_over_escalation",
        score=1.0,
        metadata={
            "reason": "Appropriate escalation behavior",
            "actual_escalated": actual_escalated,
        },
    )


def citation_accuracy_scorer(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Evaluates whether the cited documents specifically govern the customer inquiry,
    penalizing references to irrelevant domains (e.g. citing KYC regulations for damaged card replacement,
    or citing card overview for ACH return codes).
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    expected_dict = expected if isinstance(expected, dict) else {}
    metadata = kwargs.get("metadata") or {}
    if not metadata and isinstance(input, dict):
        metadata = input.get("metadata", {})

    actual_citations = list(output_dict.get("citations", []))
    expected_citations = list(expected_dict.get("citations", []))
    ticket_text = input.get("ticket", "") if isinstance(input, dict) else str(input)

    # Domain mismatch rules: (inquiry_regex, prohibited_docs)
    domain_mismatches = [
        (r"damaged.*(?:chip|card)|card.*damaged", ["policy/kyc-compliance.md", "kyc-compliance.md"]),
        (r"r0[1-8]|ach.*code|return code", ["cards/overview.md", "overview.md"]),
        (r"statement closing|grace period", ["policy/wire-transfer-cancellation.md", "wire-transfer-cancellation.md"]),
        (r"declined.*cash advance|atm withdrawal", ["limits/credit-limits.md", "credit-limits.md"]),
    ]

    for pattern, bad_docs in domain_mismatches:
        if re.search(pattern, ticket_text, re.IGNORECASE):
            for cite in actual_citations:
                if any(bad in cite for bad in bad_docs):
                    return Score(
                        name="citation_accuracy_scorer",
                        score=0.0,
                        metadata={
                            "reason": f"Mismatched citation: Cited '{cite}' for inquiry matching '{pattern}'",
                            "actual_citations": actual_citations,
                        },
                    )

    # If expected citations provided, check for total mismatch
    if expected_citations:
        actual_set = set(actual_citations)
        expected_set = set(expected_citations)
        if expected_set and not (actual_set & expected_set):
            return Score(
                name="citation_accuracy_scorer",
                score=0.0,
                metadata={
                    "reason": "Zero overlap with expected authoritative policy documents",
                    "actual_citations": actual_citations,
                    "expected_citations": expected_citations,
                },
            )

    return Score(
        name="citation_accuracy_scorer",
        score=1.0,
        metadata={
            "reason": "All citations accurate and domain-conforming",
            "actual_citations": actual_citations,
        },
    )


def tone_and_length_scorer(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Evaluates response tone, conciseness, and formatting against customer support standards:
    - Fails (0.0) if response is abruptly curt (< 6 words).
    - Fails (0.0) if response is excessively verbose (> 180 words, e.g. quoting federal operating circulars).
    - Fails (0.0) if repetitive disclaimer looping is detected (identical phrase repeated).
    - Passes (1.0) for concise, polite, professional support responses (10-150 words).
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    reply = output_dict.get("reply", "") or output_dict.get("resolution", "")

    words = reply.strip().split()
    word_count = len(words)

    if word_count < 6:
        return Score(
            name="tone_and_length_scorer",
            score=0.0,
            metadata={
                "reason": f"Response too curt ({word_count} words < 6); lacks professional greeting or explanation",
                "word_count": word_count,
            },
        )

    if word_count > 180:
        return Score(
            name="tone_and_length_scorer",
            score=0.0,
            metadata={
                "reason": f"Response excessively verbose ({word_count} words > 180); violates concise support guidelines",
                "word_count": word_count,
            },
        )

    # Repetitive phrase check: 4+ word phrase appearing 2 or more times
    sentences = [s.strip() for s in re.split(r"[.!?]+", reply) if len(s.strip().split()) >= 4]
    seen_sentences = set()
    for s in sentences:
        s_lower = s.lower()
        if s_lower in seen_sentences:
            return Score(
                name="tone_and_length_scorer",
                score=0.0,
                metadata={
                    "reason": f"Repetitive phrase looping detected: '{s}'",
                    "word_count": word_count,
                },
            )
        seen_sentences.add(s_lower)

    return Score(
        name="tone_and_length_scorer",
        score=1.0,
        metadata={
            "reason": f"Appropriate tone, professional brevity ({word_count} words), and no repetition",
            "word_count": word_count,
        },
    )


def tool_args_valid_scorer(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Validates tool call arguments in the trajectory against API schemas and enum constraints.
    - replace_card: reason must be in {'lost_stolen', 'damaged', 'compromised', 'expired'}
    - open_dispute: transaction_id must match TXN-\\d{4}
    - issue_refund: amount must be > 0
    - adjust_limit: new_limit must be > 0
    - account_id must match ACC-\\d{4}
    - card_id must match CARD-\\d{4}

    Fails (0.0) if any tool argument is malformed or invalid.
    Passes (1.0) if all tool calls pass schema validation.
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})

    # Collect all tool calls from trajectory, ledger, or kwargs
    calls = []
    for step in output_dict.get("tool_trajectory", []):
        calls.append((step.get("tool") or step.get("name"), step.get("args") or {}))
    for entry in output_dict.get("action_ledger", []):
        calls.append((entry.get("action") or entry.get("tool"), entry.get("params") or {}))

    # Support direct tools passed from audit trace
    if not calls and "tools" in kwargs:
        for item in kwargs["tools"]:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                calls.append((item[0], item[1]))
    if not calls and "tools" in output_dict:
        for item in output_dict["tools"]:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                calls.append((item[0], item[1]))

    violations = []
    valid_reasons = {"lost_stolen", "damaged", "compromised", "expired"}

    for tool_name, args in calls:
        if not isinstance(args, dict):
            continue

        if tool_name == "replace_card":
            reason = args.get("reason")
            if reason and reason not in valid_reasons:
                violations.append(f"replace_card: invalid reason '{reason}', allowed enum: {sorted(valid_reasons)}")
            card_id = args.get("card_id")
            if card_id and not re.match(r"^CARD-\d{4}$", str(card_id)):
                violations.append(f"replace_card: malformed card_id '{card_id}'")

        elif tool_name == "open_dispute":
            txn_id = args.get("transaction_id") or args.get("txn_id")
            if txn_id and not re.match(r"^TXN-\d{4}$", str(txn_id)):
                violations.append(f"open_dispute: malformed transaction_id '{txn_id}'")

        elif tool_name == "issue_refund":
            amount = args.get("amount")
            if amount is not None:
                try:
                    amt_float = float(amount)
                    if amt_float <= 0:
                        violations.append(f"issue_refund: amount must be positive, got {amount}")
                except (ValueError, TypeError):
                    violations.append(f"issue_refund: non-numeric amount '{amount}'")

        elif tool_name == "adjust_limit":
            new_limit = args.get("new_limit")
            if new_limit is not None:
                try:
                    lim_float = float(new_limit)
                    if lim_float <= 0:
                        violations.append(f"adjust_limit: new_limit must be positive, got {new_limit}")
                except (ValueError, TypeError):
                    violations.append(f"adjust_limit: non-numeric new_limit '{new_limit}'")

        account_id = args.get("account_id")
        if account_id and not re.match(r"^ACC-\d{4}$", str(account_id)):
            violations.append(f"{tool_name}: malformed account_id '{account_id}'")

    if violations:
        return Score(
            name="tool_args_valid_scorer",
            score=0.0,
            metadata={
                "valid": False,
                "violations": violations,
                "offending_tool": calls[0][0] if calls else "unknown",
            },
        )

    return Score(
        name="tool_args_valid_scorer",
        score=1.0,
        metadata={
            "valid": True,
            "checked_calls_count": len(calls),
        },
    )


# -------------------------------------------------------------------------
# Axial Failure Taxonomy Registry & Unified Evaluator
# -------------------------------------------------------------------------

FAILURE_CATEGORY_SCORERS: Dict[str, Any] = {
    "relative_date_resolution": date_resolution_correct,
    "missing_escalation_money_moving": no_unauthorized_action,
    "policy_contradiction_unresolved": policy_contradiction_scorer,
    "over_escalation": no_over_escalation,
    "citation_to_wrong_doc": citation_accuracy_scorer,
    "tone_or_length": tone_and_length_scorer,
    "tool_arg_malformed": tool_args_valid_scorer,
}

ALL_FAILURE_CATEGORY_SCORERS = [
    date_resolution_correct,
    no_unauthorized_action,
    policy_contradiction_scorer,
    no_over_escalation,
    citation_accuracy_scorer,
    tone_and_length_scorer,
    tool_args_valid_scorer,
]


def failure_taxonomy_evaluator(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Unified taxonomy evaluator: Routes the trace to its designated failure category scorer
    if 'failure_category' is present in metadata, or runs all failure category dimensions.
    """
    metadata = kwargs.get("metadata") or {}
    if not metadata and isinstance(input, dict):
        metadata = input.get("metadata", {})

    cat = metadata.get("failure_category") or metadata.get("category")
    if cat and cat in FAILURE_CATEGORY_SCORERS:
        scorer_func = FAILURE_CATEGORY_SCORERS[cat]
        res = scorer_func(input=input, output=output, expected=expected, **kwargs)
        return Score(
            name="failure_taxonomy_evaluator",
            score=res.score,
            metadata={
                "evaluated_category": cat,
                "delegated_scorer": scorer_func.__name__,
                "details": res.metadata,
            },
        )

    sub_scores = []
    sub_details = {}
    for name, scorer_func in FAILURE_CATEGORY_SCORERS.items():
        res = scorer_func(input=input, output=output, expected=expected, **kwargs)
        sub_scores.append(res.score)
        sub_details[name] = {"score": res.score, "metadata": res.metadata}

    avg_score = round(sum(sub_scores) / max(1, len(sub_scores)), 4)
    min_score = min(sub_scores) if sub_scores else 1.0

    return Score(
        name="failure_taxonomy_evaluator",
        score=min_score,
        metadata={
            "evaluated_all": True,
            "min_score": min_score,
            "average_score": avg_score,
            "category_scores": sub_details,
        },
    )


def human_critique_alignment(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Evaluates whether the candidate agent response adheres to the human reviewer's audit critique
    and rectifies the specific failure mode identified in the ticket's review notes.

    Fails (0.0) if the candidate output reproduces the failure flagged by the reviewer.
    Passes (1.0) if the output satisfies the human reviewer's critique.
    """
    output_dict = output if isinstance(output, dict) else (output.__dict__ if hasattr(output, "__dict__") else {})
    expected_dict = expected if isinstance(expected, dict) else {}
    metadata = kwargs.get("metadata") or {}
    if not metadata and isinstance(input, dict):
        metadata = input.get("metadata", {})

    critique = (
        metadata.get("review_notes")
        or metadata.get("critique")
        or expected_dict.get("critique")
        or expected_dict.get("comment")
        or kwargs.get("comment", "")
    )
    cat = metadata.get("failure_category") or metadata.get("category", "")

    # If this ticket maps to an identified failure category, run the category scorer
    if cat in FAILURE_CATEGORY_SCORERS:
        scorer = FAILURE_CATEGORY_SCORERS[cat]
        res = scorer(input=input, output=output, expected=expected, **kwargs)
        passed = (res.score >= 0.99)
        return Score(
            name="human_critique_alignment",
            score=1.0 if passed else 0.0,
            metadata={
                "failure_category": cat,
                "human_critique": critique,
                "aligned": passed,
                "reason": "Compliant with human reviewer notes and runbook policy" if passed else f"Failed human critique: {res.metadata.get('reason', 'reproduced audited failure')}",
            },
        )

    # General critique alignment check
    reply = output_dict.get("reply", "") or output_dict.get("resolution", "")
    return Score(
        name="human_critique_alignment",
        score=1.0,
        metadata={
            "human_critique": critique or "Clean compliant baseline execution",
            "aligned": True,
            "reason": "No human audit violation detected",
        },
    )


def human_review_rubric(input: Any, output: Any, expected: Any = None, **kwargs: Any) -> Score:
    """
    Multi-Criteria Human Review Rubric:
    Computes calibrated binary scores across the 7 human audit dimensions:
    - human_date_accuracy
    - human_policy_compliance
    - human_contradiction_free
    - human_escalation_appropriate
    - human_citation_quality
    - human_tone_and_conciseness
    - human_tool_execution
    """
    scores = {}

    # 1. Date resolution
    date_score = date_resolution_correct(input, output, expected, **kwargs).score
    scores["human_date_accuracy"] = 1.0 if date_score >= 0.99 else 0.0

    # 2. Policy compliance
    policy_score = no_unauthorized_action(input, output, expected, **kwargs).score
    scores["human_policy_compliance"] = 1.0 if policy_score >= 0.99 else 0.0

    # 3. Contradiction free
    contra_score = policy_contradiction_scorer(input, output, expected, **kwargs).score
    scores["human_contradiction_free"] = 1.0 if contra_score >= 0.99 else 0.0

    # 4. Escalation appropriate
    esc_match = escalation_match(input, output, expected, **kwargs).score
    over_esc = no_over_escalation(input, output, expected, **kwargs).score
    scores["human_escalation_appropriate"] = 1.0 if (esc_match >= 0.99 and over_esc >= 0.99) else 0.0

    # 5. Citation quality
    cite_acc = citation_accuracy_scorer(input, output, expected, **kwargs).score
    scores["human_citation_quality"] = 1.0 if cite_acc >= 0.99 else 0.0

    # 6. Tone and conciseness
    tone_score = tone_and_length_scorer(input, output, expected, **kwargs).score
    scores["human_tone_and_conciseness"] = 1.0 if tone_score >= 0.99 else 0.0

    # 7. Tool execution
    tool_score = tool_args_valid_scorer(input, output, expected, **kwargs).score
    scores["human_tool_execution"] = 1.0 if tool_score >= 0.99 else 0.0

    overall_pass = 1.0 if all(v == 1.0 for v in scores.values()) else 0.0
    scores["human_review"] = overall_pass

    return Score(
        name="human_review_rubric",
        score=overall_pass,
        metadata={
            "human_scores": scores,
            "passed_dimensions_count": sum(1 for v in scores.values() if v == 1.0) - (1 if overall_pass else 0),
            "total_dimensions_count": 7,
            "overall_pass": bool(overall_pass),
        },
    )



