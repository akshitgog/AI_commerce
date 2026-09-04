# Canonical documentation index

This folder is the authoritative specification for the v1 project. If another note, diagram or pitch conflicts with these files, this package wins until an explicit decision updates it.

## Reading order

1. [MASTER_DEVELOPMENT_PLAN.md](MASTER_DEVELOPMENT_PLAN.md) — workstream boundaries, frozen contracts, dependencies and integration gates.
2. [README.md](README.md) — product boundary and complete story.
3. [PRD.md](PRD.md) — actors, journeys, requirements and definition of done.
4. [ARCHITECTURE.md](ARCHITECTURE.md) — authoritative trust boundaries, interfaces and lifecycle.
5. [DATA_MODEL.md](DATA_MODEL.md) — records, relationships and invariants.
6. [SHARED_CONTRACTS.md](SHARED_CONTRACTS.md) — concise frozen/provisional contract register.
7. [API.md](API.md) — HTTP, application-service and MCP contracts.
8. [SECURITY.md](SECURITY.md) — identity, authorization, policies and payment safety.
9. [EVALUATION.md](EVALUATION.md) — acceptance scenarios and evidence requirements.
10. [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — product integration sequence and cut order.
11. [PHASE_EXECUTION.md](PHASE_EXECUTION.md) — phase branches, status lifecycle, review gate and evidence template.
12. [workstreams/](workstreams/) — bounded ownership briefs and lane phase maps; read only the assigned workstream.
13. [DEVELOPMENT.md](DEVELOPMENT.md) — implemented repository layout, setup and foundation validation.
14. [RAZORPAY_TEST_MODE.md](RAZORPAY_TEST_MODE.md) — B4 provider contract, evidence status and reproducible Test Mode check.
15. [TESTED.md](TESTED.md) — actual execution ledger; planned behavior is never recorded as passed.

## Locked v1 decisions

- Target: **Razorpay Track 1 — AI Growth & Agentic Commerce, AI-buyer branch**.
- Primary customer: the merchant; the human buyer owns purchase consent.
- Main demo: one merchant end to end; a second fixture exists only for tenant-isolation tests.
- Primary buyer demo: Reference Buyer Chat.
- External interoperability proof: one MCP-capable client through a remote MCP server.
- Payment provider: Razorpay Test Mode only.
- Success: verified payment/capture state, never provider-order creation alone.
- Execution authority: trusted backend, never the LLM or MCP adapter.
- Deployment: modular monolith with durable relational storage.

Reference chat and MCP must converge on the same application services. MCP never contains independent financial logic and external MCP availability never gates the primary demo.
