# Security and transaction safety

## Objective

An AI client may reason about commerce but cannot manufacture identity, consent, merchant acceptance, price, provider truth or final payment state.

## Authentication and tenant authorization

- Merchant dashboard actions require an authenticated merchant member and role check.
- Human buyer approval requires an authenticated buyer-controlled surface.
- Buyer MCP clients act for a bound buyer identity; tool parameters cannot switch that identity.
- Merchant MCP clients use a separate audience and endpoint bound server-side to exactly one active
  merchant. Tool parameters cannot supply merchant identity, actor identity or roles.
- Merchant MCP discovery grants reads to merchant members and catalog mutations only to `ADMIN` or
  `EDITOR`; it exposes no buyer financial or provider operations.
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

Merchant MCP catalog mutations also require transport-level idempotency metadata. The adapter
injects it into the canonical command only after authentication; the service rejects a reused key
with a different fingerprint.

## Merchant MCP publication confirmation

Draft creation and update never publish implicitly. Publishing and unpublishing require a signed
confirmation issued only through the dashboard after explicit human confirmation or step-up
authentication; merchant MCP credentials cannot call the issuer.

The five-minute HS256 token uses a dedicated server-side secret and binds issuer, audience
`merchant-mcp-publication`, merchant user, merchant, product, expected version, action, issued and
expiry times, and unique token ID. Before invoking the catalog service, the merchant adapter verifies
the signature, expiry, audience, actor, tenant, product, version and action. The token is never logged
and is stripped before constructing the frozen publication command.

Publication increments product version, so the token cannot authorize a later state change. A replay
with the original idempotency key returns the stored logical result; a changed fingerprint is
rejected.

## Provider security

- Test Mode keys and webhook secrets remain server-side.
- Browser and MCP responses receive only the minimum checkout-safe/public data required by the chosen integration.
- Verify checkout signatures from the stored server order ID plus submitted payment ID.
- Verify webhook HMAC over exact raw request bytes with the distinct webhook secret before parsing.
- Deduplicate only by the verified `X-Razorpay-Event-Id`; reject one event ID reused with another payload hash.
- Map provider events only through stored references.
- Independently query both payment and order before accepting captured-payment success.
- Require correlated references, payment `captured`, order `paid` and exact amount/currency match.
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
