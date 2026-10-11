# Policy: Support Agent Refund Authority & Limits

This policy defines the financial bounds within which Tier 2 Support Agents may unilaterally issue refunds to commercial accounts.

## Authorized Discretionary Refunds
- **Permitted Limits**: Tier 2 Support Agents may directly execute `issue_refund(account_id, amount, reason)` up to **$50.00** per customer incident for validated billing glitches, system outage concessions, or accidental service fees.
- **Account Status**: The account must have zero active risk flags, account age > 30 days, and KYC status `verified`.

## Prohibited Autonomous Refunds (Mandatory Escalation)
Support agents must NOT call `issue_refund` autonomously and MUST escalate via `escalate(reason, queue="finance")` if:
1. The requested refund amount is greater than $50.00.
2. The account has any risk flags (`recent_chargeback`, `rapid_spend_velocity`, etc.).
3. The refund is requested as a settlement for a merchant charge dispute rather than an internal billing fee error (merchant disputes must follow `policy/dispute-handling.md`).
4. The cumulative refunds on the account in the preceding 30 days exceed $100.00.
