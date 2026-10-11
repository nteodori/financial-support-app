# Runbook: Compromised Card & Unauthorized Activity

Follow this procedure whenever a customer states their card has been cloned, stolen, or used without authorization.

## Execution Sequence
1. **Fetch Context**:
   - Call `get_account(account_id)` to identify active cards and risk status.
2. **Immediate Threat Neutralization**:
   - Call `replace_card(card_id, reason="compromised")` to deactivate the compromised card credentials and initiate reissuance.
3. **Transaction Inspection**:
   - Call `list_transactions(account_id, days=14)` to locate all unauthorized transactions.
4. **Dispute Resolution**:
   - For all identified unauthorized transactions, check fraud escalation thresholds.
   - If amounts exceed policy limits or risk flags are active, call `escalate(reason="Compromised card with high-dollar fraud", queue="fraud")`.
   - For permitted routine amounts on mature accounts, call `open_dispute(transaction_id, reason="card_compromised")`.
5. **Customer Confirmation**:
   - Confirm that the compromised card was deactivated, outline digital wallet re-provisioning, and provide delivery estimate for replacement card.
