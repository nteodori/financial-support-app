# Runbook: Suspicious Wire Transfers & Urgent Recalls

This runbook specifies actions for reported fraudulent or erroneous wire transfers.

## Execution Steps
1. **Gather Transfer Details**:
   - Call `get_account(account_id)` and verify wire status from transaction records.
2. **Determine Settlement State**:
   - If transfer was initiated within the last 15 minutes and is still pending batch release, cancel the transfer.
   - If the wire has settled via Fedwire, it cannot be canceled locally.
3. **Mandatory Fraud Escalation**:
   - Call `escalate(reason="Urgent Fedwire recall request - possible wire fraud", queue="fraud")`.
   - Never issue provisional credit or unilateral manual adjustments for wire disputes.
4. **Advise Customer**:
   - Inform customer that the recall request has been submitted to the correspondent network and the fraud unit is engaged.
