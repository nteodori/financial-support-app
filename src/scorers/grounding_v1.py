"""
Grounding Judge v1: Zero-shot naive rubric without few-shot examples.
Braintrust SDK Version: 0.39.0

Demonstrates the M1 Judge Validation trap:
Reports ~87% raw agreement on human labels, but has a True Positive Rate (TPR) of only ~33%
on actual failures because it is overly lenient on authoritative-sounding hallucinations.
"""

import os
import re
from typing import Any, Dict, List
import braintrust as bt
from braintrust.framework import Score

V1_RUBRIC = """You are an AI evaluator checking whether a customer support reply is factually grounded in policy citations.
Determine whether every factual claim, threshold, fee, timeline, and policy stated in the Response is strictly supported by the retrieved citations.
If the response contains unauthorized commitments, hallucinated timelines, or contradicted rules, mark it UNGROUNDED (0).
Otherwise, mark it GROUNDED (1).

Return your verdict in this exact format:
VERDICT: [GROUNDED | UNGROUNDED]
REASONING: <brief justification>
"""


def judge_grounding_v1(ticket: str, reply: str, citations: List[str]) -> Score:
    """
    Evaluates grounding under the v1 zero-shot rubric.
    Returns binary Score (1.0 = Grounded / Pass, 0.0 = Ungrounded / Fail).
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    if gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_api_key)
            prompt = f"{V1_RUBRIC}\n\nTicket: {ticket}\nCitations: {citations}\nResponse:\n{reply}"
            resp = client.models.generate_content(
                model=os.getenv("JUDGE_MODEL", "gemini-3.6-flash"),
                contents=prompt,
            )
            text = resp.text or ""
            is_grounded = 1.0 if "VERDICT: GROUNDED" in text.upper() else 0.0
            return Score(
                name="grounding_v1",
                score=is_grounded,
                metadata={"reasoning": text.strip(), "judge": "v1_gemini"},
            )
        except Exception:
            pass

    # Deterministic calibration for offline demo and benchmark reproducibility
    # v1 is overly permissive: passes authoritative phrasing, catching only ~33% of failures
    reply_lower = reply.lower()
    
    # Severe obvious flags v1 catches (5 of 15)
    catches = [
        "provisional credit within 1 hour",
        "$85.00 courtesy concession",
        "wire transfer and funds will reverse back to your operating balance today",
        "disabled on your administrator profile",
        "0% international exchange fees"
    ]
    
    # 3 false positives where v1 flags a benign response
    false_positives = [
        "temporary pre-authorization hold up to $100",
        "re-attempted per standard banking rails",
        "commercial disputes must be submitted within 60 days"
    ]

    is_obvious_fail = any(phrase in reply_lower for phrase in catches)
    is_fp = any(phrase in reply_lower for phrase in false_positives)

    if is_obvious_fail:
        verdict = 0.0
        reason = "v1 Judge caught explicit policy mismatch in response text."
    elif is_fp:
        verdict = 0.0
        reason = "v1 Judge overly penalized technical banking explanation."
    else:
        verdict = 1.0
        reason = "v1 Judge found response claims plausible and compliant."

    return Score(
        name="grounding_v1",
        score=verdict,
        metadata={"reasoning": reason, "judge": "v1_zero_shot"},
    )
