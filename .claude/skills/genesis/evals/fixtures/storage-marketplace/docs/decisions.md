# Decisions — Storage Marketplace

> Source of truth (highest wins): this file → architecture.md → glossary.md → open-questions.md.

<!-- @anchor decision:auth-model refs:term:account -->
### D-001 — Auth: email/password and Google OAuth
- Context: two roles (owner, renter); low-friction signup wanted.
- Decision: email/password and Google OAuth at MVP. Phone login is out.
- Consequences: OAuth callback; account linking by verified email.

<!-- @anchor decision:money-custody refs:term:booking,term:payout,term:escrow,term:commission,decision:payment-provider -->
### D-002 — Money: platform escrow with monthly payout to owner
- Context: monthly rent; platform takes commission.
- Decision: renter pays platform escrow; platform pays out the owner monthly minus commission.
- Consequences: balance and payout subsystem; provider undecided (see open-questions).
