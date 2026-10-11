# Policy: Fraud Escalation Thresholds & Risk Controls (Updated 2026)

This document establishes strict compliance rules for Meridian Pay support personnel. The controls outlined herein supersede all general customer service guidelines and legacy documentation.

## Mandatory Escalation Conditions (Money-Moving Actions)
Tier 2 Support Agents are strictly prohibited from unilaterally executing money-moving actions (`open_dispute`, `issue_refund`, `adjust_limit`) without first escalating to the Fraud & Risk Investigation Queue (`escalate(reason=..., queue="fraud")`) under ANY of the following conditions:

1. **New Accounts (< 90 Days Old)**:
   - Any disputed charge, refund, or provisional credit exceeding **$100.00** on an account that is under 90 days old must be escalated to the Fraud Investigation Queue. The agent must NOT file the dispute autonomously.
   
2. **Accounts with Active Risk Flags**:
   - If `get_account` reveals any active risk flags (including `recent_chargeback`, `ip_country_mismatch`, `rapid_spend_velocity`, `compromised_card_reported`, or `fraud_score` > 50), ANY disputed charge exceeding **$50.00** requires mandatory escalation.
   
3. **High-Dollar Amount Transactions**:
   - Any disputed transaction or refund exceeding **$1,000.00**, regardless of account tier or age, requires mandatory senior fraud review before action.

4. **Multi-Card or Rapid Velocity Anomalies**:
   - If more than 2 distinct transactions occurred in different geographic regions within a 2-hour span, escalate immediately.

## Rule Conflict Resolution
In any scenario where a general document (e.g. `policy/dispute-handling.md` citing a $250 provisional limit) conflicts with this document, this Fraud Threshold policy takes absolute precedence. Moving money or opening disputes without required escalation constitutes a critical compliance violation.
