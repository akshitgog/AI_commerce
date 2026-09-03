# Canonical documentation index

This folder is the authoritative specification for the v1 project. If another note, diagram or pitch conflicts with these files, this package wins until an explicit decision updates it.

## Reading order

1. [README.md](README.md) — product boundary and complete story.
2. [PRD.md](PRD.md) — actors, journeys, requirements and definition of done.
3. [ARCHITECTURE.md](ARCHITECTURE.md) — trust boundaries, components and lifecycle.
4. [DATA_MODEL.md](DATA_MODEL.md) — records, relationships and invariants.
5. [API.md](API.md) — HTTP and MCP contracts.
6. [SECURITY.md](SECURITY.md) — identity, authorization, policies and payment safety.
7. [EVALUATION.md](EVALUATION.md) — acceptance scenarios and evidence requirements.
8. [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — build sequence and cut order.
9. [TESTED.md](TESTED.md) — actual execution ledger; planned behavior is never recorded as passed.

## Locked v1 decisions

- Target: **Razorpay Track 1 — AI Growth & Agentic Commerce, AI-buyer branch**.
- Primary customer: the merchant; the human buyer owns purchase consent.
- Main demo: one merchant end to end; a second fixture exists only for tenant-isolation tests.
- Buyer access: one MCP-capable client; other channels are future adapters.
- Payment provider: Razorpay Test Mode only.
- Success: verified payment/capture state, never provider-order creation alone.
- Execution authority: trusted backend, never the LLM or MCP adapter.
- Deployment: modular monolith with durable relational storage.
