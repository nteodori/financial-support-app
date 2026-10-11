# Policy: Wire Transfer Cancellation & Recall

Commercial wire transfers through Meridian Pay utilize the Federal Reserve Fedwire Funds Service.

## Pre-Release vs Post-Release Windows
1. **Pre-Release Window (< 15 Minutes)**:
   - If a wire is in `pending_approval` or `queued_for_settlement` status, support agents may cancel the transfer directly upon customer authorization.
   
2. **Post-Release (Settled Fedwire)**:
   - Once Fedwire confirmation is issued, the transfer is legally final.
   - Support agents CANNOT reverse a settled wire transfer.
   - For suspected wire fraud or misdirected funds, the agent must immediately initiate a SWIFT/Fedwire Recall Request and call `escalate(reason="Urgent wire recall", queue="fraud")`.
   - Never issue provisional funds or credit for disputed wires without executive approval.
