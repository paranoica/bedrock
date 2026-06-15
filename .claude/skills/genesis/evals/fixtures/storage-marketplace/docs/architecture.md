# Architecture — Storage Marketplace

## Components
- API — REST backend.

## Invariants
<!-- @anchor arch:payment-idempotency -->
- Payment idempotency — a renter charge is idempotent per (booking_id, period).
