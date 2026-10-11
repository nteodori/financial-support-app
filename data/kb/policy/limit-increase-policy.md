# Policy: Credit Limit Adjustments & Underwriting Controls

This policy governs all modifications to commercial card revolving credit lines and charge ceilings.

## Autonomous Limit Adjustments (Strictly Regulated)
Tier 2 Support Agents may directly execute `adjust_limit(account_id, new_limit)` ONLY when ALL of the following criteria are met:
1. Account age is greater than 180 days.
2. Account KYC status is `verified`.
3. Account has ZERO active risk flags.
4. Current balance is less than 50% of the existing credit limit.
5. The requested increase is no more than 10% above the current limit.

## Mandatory Escalation to Underwriting
Under ANY of the following conditions, agents must NOT adjust the limit and MUST call `escalate(reason=..., queue="underwriting")`:
- The requested limit exceeds $50,000.
- The increase is greater than 10% of the current limit.
- The account age is less than 180 days.
- The account has any active risk flag (`recent_chargeback`, `rapid_spend_velocity`, etc.).
- The account has had a late payment in the preceding 90 days.
