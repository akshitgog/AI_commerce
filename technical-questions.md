# technical-questions.md — Technical Knowledge Base

Use this file for questions that emerge during implementation.

Do not invent answers.

---

## Q: What exact Razorpay Test Mode condition should map to platform `SUCCEEDED`?

Status: OPEN
Branch-raised: <fill when investigated>
Last-updated-by: <developer/agent>

Context:
Creating a Razorpay order is not equivalent to a successful payment. The implementation must identify the provider truth required before setting the platform transaction to `SUCCEEDED`.

Current Answer:
Not yet verified against an implementation/provider spike.

Evidence:
None yet.

Decision:
Do not mark platform transactions `SUCCEEDED` until the provider spike establishes and tests the required condition.

Confidence:
LOW

Last updated:
<date>

Related modules:
Razorpay adapter, transaction authority, webhook verification, reconciliation.
