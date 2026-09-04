# AI Commerce Gateway — Shared UI Reference

## Product framing
The AI Commerce Gateway makes a participating merchant transactable by an AI buyer while keeping financial authority in trusted backend services.

The frontend has two first-class surfaces:
1. Merchant Control Center — operational dashboard for catalog, policy, reviews, transactions, and audit.
2. Reference Buyer Chat — buyer-facing conversational commerce demo.

The product is not a marketplace, Amazon clone, generic chatbot, or MCP-first customer experience. MCP is a separate interoperability path and must not appear in normal buyer screens.

## Authority model
- AI discovers, explains, proposes, and invokes narrow tools.
- Human buyer authorizes a bounded proposal.
- Merchant independently accepts, denies, or reviews according to policy.
- Trusted backend derives money, determines readiness, executes, verifies, reconciles, and records audit.
- Frontend renders trusted state; it does not create authoritative financial truth.

Never visually collapse buyer authorization and merchant acceptance into one approval. Never treat provider order creation or checkout initiation as payment success.

## Shared demo fixture
Merchant: Demo Electronics
Product: 65W USB-C Charger
SKU: USB-C-65W-001
Price: ₹899 INR
Stock: 10
Published: true
Policy: AUTO_BELOW_LIMIT, maximum ₹1,000

Optional policy-review fixture:
Premium Mechanical Keyboard — ₹1,299 INR.

## Canonical human-readable states
- Awaiting buyer approval
- Awaiting merchant approval
- Ready
- Processing payment
- Payment pending
- Verifying
- Recovering
- Succeeded
- Failed
- Cancelled
- Expired

UNKNOWN and RECONCILING should be presented to ordinary users as Recovering, with technical state available only in details.

## Core visual principle
The recurring visual motif is trust progression:
Intent → Proposal → Buyer Authorized → Merchant Accepted → Payment → Provider Verified.

The application should feel like a fintech transaction control system with a conversational commerce layer.
