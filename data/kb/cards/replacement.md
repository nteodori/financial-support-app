# Card Replacement Policy & Procedures

When a customer reports a card lost, stolen, damaged, or compromised, support agents have authority to issue a replacement card.

## Replacement Workflows
- **Lost or Stolen**: Agent must immediately block the existing card to prevent further charges, then trigger `replace_card(card_id, reason="lost_stolen")`.
- **Damaged**: Physical card chip or magnetic stripe failure. Agent triggers `replace_card(card_id, reason="damaged")`. The existing card remains active for virtual wallet use until the new card is activated.
- **Compromised**: Fraudulent transactions detected. Block card immediately, reissue new virtual credentials immediately, and dispatch physical card via expedited courier.

## Shipping Options & Timelines
- Standard Ground: 3–5 business days (no fee).
- Expedited Overnight: Next business day (complimentary for Growth and Enterprise tiers; $25 fee for Starter tier unless waived by Tier 2 agent for fraud cases).
