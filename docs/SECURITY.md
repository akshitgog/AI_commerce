# Security and transaction safety

## Objective

An AI client may reason about commerce but cannot manufacture identity, consent, merchant acceptance, price, provider truth or final payment state.

## Authentication and tenant authorization

- Merchant dashboard actions require an authenticated merchant member and role check.
- Human buyer approval requires an authenticated buyer-controlled surface.
- MCP clients act for a bound buyer identity; body parameters cannot switch that identity.
- Every merchant-scoped query checks ownership, including indirect product, proposal, transaction and audit lookups.
- The second merchant fixture exists specifically to test denial of cross-tenant access.

## Two independent financial gates

### Buyer authorization

Answers: may this buyer purchase this proposal under these explicit limits?

It is bound to proposal hash, merchant, product, quantity, maximum amount, currency and expiry. The AI may request approval but cannot grant it.

### Merchant policy and acceptance

Answers: will the merchant accept this order under current policy?

The policy may automatically allow, deny or require authenticated merchant review. Merchant acceptance never substitutes for buyer consent.

## Required execution gates

```text
Authenticated actor
→ immutable proposal with server-derived total
→ buyer authorization
→ merchant policy/manual acceptance
→ current price/version/stock revalidation
→ durable idempotency and valid state transition
→ provider order/checkout initiation
→ verified provider truth
```

## Prompt-injection boundary

Catalog descriptions, AI metadata and natural-language intent are untrusted strings. They can assist search and explanation but cannot populate trusted price, quantity, merchant identity, authorization, policy decision, provider fields or state.

Structured financial inputs are loaded from server records and passed directly to deterministic application logic. No prompt output is executed as code or interpreted as an approval.

## Replay and duplicate protection

- Require scoped idempotency keys for logical creation/execution.
- Persist request fingerprints and completed outcomes.
- Reject key reuse with a different fingerprint.
- Lock or atomically transition the transaction before provider dispatch.
- Enforce uniqueness in the database.
- Deduplicate provider events by verified provider event identity.

## Provider security

- Test Mode keys and webhook secrets remain server-side.
- Browser and MCP responses receive only the minimum checkout-safe/public data required by the chosen integration.
- Verify supported checkout response and webhook signatures before trusting them.
- Map provider events only through stored references.
- Query provider truth when state is uncertain or conflicting.
- Never treat a provider order ID as payment success.

## Secrets, logs and audit

- Do not log credentials, full webhook secrets, full payment instrument data or sensitive personal data.
- Redact provider payloads before retaining evidence.
- Keep operational logs separate from append-only financial events.
- Audit metadata uses a strict allowlist and remains useful without raw conversation retention.
- Test evidence uses Test Mode IDs with appropriate redaction.

## Abuse and failure behavior

- Expired, mismatched or revoked authorization fails closed before provider contact.
- Stale price/version or insufficient stock requires a new proposal.
- Unknown provider outcome blocks a new creation attempt until reconciliation.
- Invalid state transitions return deterministic errors and emit security/operational telemetry as appropriate.
- Provider or AI failure cannot silently upgrade a transaction to success.

## V1 limitations

This is a Test Mode demonstration, not a production PCI, privacy, fraud or regulatory certification. Real-money rollout, production key management, formal threat assessment and data-retention policy require separate work.
