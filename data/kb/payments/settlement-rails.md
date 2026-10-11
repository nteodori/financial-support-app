# Payment Settlement Rails and Clearing Windows

Understanding transaction lifecycles is critical for addressing customer inquiries regarding pending vs settled charges.

## Payment Rails
1. **Card Network Purchases**:
   - Authorization: Instant hold placed on funds.
   - Settlement / Clearing: 24 to 48 hours for merchant batch capture.
   - Dispute Window: Must be initiated within 60 calendar days of settlement date.

2. **ACH Direct Debit / Credit**:
   - Standard ACH: 3 to 5 business days for settlement.
   - Same-Day ACH: Cutoff at 1:00 PM EST; settles by 5:00 PM local time.
   - Return Codes: Common returns include R01 (Insufficient Funds) and R08 (Payment Stopped).

3. **Domestic & International Wires**:
   - Domestic Fedwire: Final and irrevocable once processed. Same-day settlement if submitted by 4:00 PM EST.
   - International SWIFT: 1 to 3 business days, subject to intermediary correspondent banking fees and sanctions screening.
