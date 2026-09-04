# technical-questions.md — Technical Knowledge Base

Use this file for questions that emerge during implementation.

Do not invent answers.

---

## Q: What exact Razorpay Test Mode condition should map to platform `SUCCEEDED`?

Status: OPEN
Branch-raised: phase/b4-razorpay-adapter
Last-updated-by: Codex Agent B

Context:
Creating a Razorpay order is not equivalent to a successful payment. The implementation must identify the provider truth required before setting the platform transaction to `SUCCEEDED`.

Current Answer:
Official Razorpay documentation identifies `captured` as the successful payment status and requires
server-side verification of the Checkout signature. The current candidate platform gate is thus a
payment tied to the stored server-side order whose Checkout signature is valid and whose provider
lookup/webhook evidence confirms `captured`. A created order, attempted order or merely authorized
payment is insufficient. B4 exercised real order creation, but the candidate success gate still
requires the B5 payment/signature flow.

Evidence:
Razorpay Standard Checkout integration and Test/Live Mode documentation reviewed on 2026-09-04;
B4 adapter tests prove that `created` yields only `PAYMENT_PENDING`. Real Test Mode run
`B4-RZP-20260904-01` passed with redacted order suffix `...JzsC44` and no payment/capture truth. See
`docs/RAZORPAY_TEST_MODE.md`.

Decision:
B4 cannot mark success. Keep this question OPEN until B5 validates signature plus captured-provider
truth against Test Mode and records redacted evidence.

Confidence:
MEDIUM

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

## Q: How should MCP mutating calls obtain stable buyer-bound idempotency keys?

Status: OPEN
Branch-raised: main
Last-updated-by: Codex architecture/documentation agent

Context:
MCP retries must map to durable backend idempotency without permitting an external client to substitute buyer identity or accidentally reuse a key across different requests.

Current Answer:
Not yet defined. Actor identity must come from the authenticated server context, and the key remains scoped by actor and operation with a request fingerprint.

Evidence:
Existing API, architecture and security contracts; no MCP implementation evidence yet.

Decision:
Freeze key propagation/derivation before implementing `execute_transaction` through MCP.

Confidence:
MEDIUM

Last updated:
2026-09-04

Related modules:
Remote MCP adapter, buyer identity, transaction authority, IdempotencyRecord.
