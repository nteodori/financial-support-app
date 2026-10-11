# Runbook: Handling Unrecognized Charges and Dispute Inquiries

This runbook guides agents through the sequence of required steps when a customer reports an unrecognized merchant charge.

## Standard Triage Sequence
1. **Retrieve Account Context**:
   - Always call `get_account(account_id)` first. Check `age_days`, `kyc_status`, and `risk_flags`.
2. **Retrieve Transaction Details**:
   - Call `list_transactions(account_id, days=30)` to identify the exact transaction ID, dollar amount, merchant name, and settlement date.
3. **Inspect Prior Disputes**:
   - Call `get_dispute_history(account_id)` to check for repeated merchant disputes or pattern abuse.
4. **Evaluate Fraud & Compliance Rules**:
   - Consult `policy/fraud-thresholds.md`.
   - If account age is < 90 days AND transaction amount > $100.00: You MUST call `escalate(reason="Unrecognized charge > $100 on account < 90 days", queue="fraud")`. Do NOT file autonomous disputes.
   - If risk flags exist AND transaction amount > $50.00: You MUST call `escalate(reason="Charge dispute with active risk flags", queue="fraud")`.
   - If transaction is routine (account age >= 90 days, no risk flags, amount <= $250): Call `open_dispute(transaction_id, reason="unrecognized_merchant")`.
5. **Formulate Reply**:
   - Provide clear next steps and timeline to the customer.
