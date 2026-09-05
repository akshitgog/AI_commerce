# technical-questions.md — Technical Knowledge Base

Use this file for questions that emerge during implementation.

Do not invent answers.

---

## Q: What exact Razorpay Test Mode condition should map to platform `SUCCEEDED`?

Status: RESOLVED
Branch-raised: phase/b4-razorpay-adapter
Last-updated-by: Codex Agent B

Context:
Creating a Razorpay order is not equivalent to a successful payment. The implementation must identify the provider truth required before setting the platform transaction to `SUCCEEDED`.

Current Answer:
B5 implemented the strict five-condition success gate. Platform `SUCCEEDED` requires all of:
(1) valid checkout HMAC-SHA256 or webhook HMAC authenticity; (2) provider payment and order IDs
correlated to the stored attempt; (3) payment state `captured` with `captured: true` from an
independent lookup; (4) order state `paid` with zero amount due from an independent lookup; and
(5) provider amount and currency matching the immutable transaction. The two-step transition
(PAYMENT_PENDING → VERIFYING → SUCCEEDED) ensures that neither order creation, authorization,
failure, a valid signature alone, nor a mismatched amount can produce SUCCEEDED.

Evidence:
Razorpay Standard Checkout integration and Test/Live Mode documentation reviewed on 2026-09-04;
B4 adapter tests prove that `created` yields only `PAYMENT_PENDING`. Real Test Mode run
`B4-RZP-20260904-01` passed with redacted order suffix `...JzsC44` and no payment/capture truth.
B5 integration tests prove the two-step transition and that each insufficient condition blocks
success. Real Test Mode run `B5-RZP-20260904-01` created and looked up a redacted order ending
`...qM0YHJ`. See `docs/RAZORPAY_TEST_MODE.md`.

Decision:
Resolved in B5 by D-010.

Confidence:
HIGH

Last updated:
2026-09-04

Related modules:
Razorpay adapter, transaction authority, webhook verification, reconciliation.

---

## Q: Should demo product images use public URLs or expiring signed URLs?

Status: OPEN
Branch-raised: main
Last-updated-by: Codex architecture/documentation agent

Context:
Reference Buyer Chat and buyer-safe catalog/MCP responses need displayable image metadata, while object storage access must remain tenant-safe and simple for the demo.

Current Answer:
Not yet selected. The storage abstraction supports either policy; the buyer contract exposes only a safe URL and metadata.

Evidence:
Architecture planning only; no storage implementation or deployed behavior exists.

Decision:
Freeze the URL policy before workstreams 01, 02, 05 and 06 implement the image contract.

Confidence:
LOW

Last updated:
2026-09-04

Related modules:
Catalog service, ProductImage, storage adapter, merchant dashboard, reference buyer chat, MCP catalog responses.

---

## Q: How should MCP mutating calls obtain stable actor-bound idempotency keys?

Status: ANSWERED
Branch-raised: main
Last-updated-by: Codex architecture/documentation agent

Context:
Buyer and merchant MCP retries must map to durable backend idempotency without permitting an
external client to substitute identity/tenant or accidentally reuse a key across different
requests.

Current Answer:
The client supplies a stable `Idempotency-Key` through authenticated MCP transport metadata, not a
business tool argument. The adapter derives actor and, for merchant MCP, the single active merchant
from server context, then injects the key into the frozen command. The canonical service scopes the
record by actor and operation and persists a request fingerprint and logical result.

Evidence:
Human-approved two-sided MCP architecture decision D-007 and aligned API/security/workstream
contracts. Implementation and restart/concurrency evidence remain not run until A7/C4/C7.

Decision:
Use required transport metadata for all MCP mutations. Never accept identity, tenant, roles or the
idempotency key in merchant business tool schemas. Same key/same fingerprint replays the original
logical result; same key/different fingerprint is rejected.

Confidence:
HIGH for the interface decision; implementation evidence pending.

Last updated:
2026-09-04

Related modules:
Remote buyer/merchant MCP adapters, authenticated actor context, catalog/transaction services,
IdempotencyRecord.
