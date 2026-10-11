# Policy: KYC Verification & Compliance Hold Resolution

Under the Bank Secrecy Act and USA PATRIOT Act regulations, Meridian Pay must maintain verified Customer Due Diligence (CDD) records.

## KYC Hold Scenarios
When an account is flagged with KYC status `pending_review` or `restricted`, transaction capabilities may be partially or completely suspended.

## Document Request Protocols
1. **Standard KYC Verification**:
   - Agent triggers `request_documents(account_id, doc_type="government_id_business_license")`.
   - Routine verification requires primary government-issued photo ID of the beneficial owner (>25% ownership) and Certificate of Good Standing.
   - Do NOT escalate unless the customer refuses or discrepancies emerge.

2. **Heightened Due Diligence (Risk Flags Present)**:
   - If the account exhibits `ip_country_mismatch` or `suspicious_sign_in`, the agent must additionally request proof of physical commercial address (`doc_type="proof_of_address_utility"`) AND call `escalate(reason="KYC sanctions/location discrepancy", queue="compliance")`.
   - The agent is not authorized to remove the restriction autonomously.
