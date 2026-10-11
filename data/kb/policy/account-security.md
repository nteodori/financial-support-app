# Policy: Account Security & Credential Protection

Meridian Pay enforces strict account authentication protocols to prevent account takeovers (ATO).

## Security Incidents & Credential Compromise
- If a customer reports unauthorized portal access or compromised credentials:
  1. Revoke active API tokens and browser sessions.
  2. Require step-up identity verification before password reset.
  3. Review all virtual cards created in the prior 48 hours.
- If fraudulent transactions have already cleared following account compromise, escalate immediately to `fraud` queue.

## Two-Factor Authentication (2FA) Resets
- Agents cannot disable 2FA over chat without verifying customer via out-of-band SMS or biometric challenge.
- If user has lost phone access and backup codes, request notarized identity documentation and escalate to `security` queue.
