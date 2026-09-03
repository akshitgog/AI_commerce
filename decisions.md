# decisions.md — Architectural and Product Decisions

Record durable decisions that future developers and AI agents must understand.

---

## D-001 — Target only the AI-buyer branch of Razorpay Track 1

Status: ACTIVE
Date: <fill>
Branch: <fill>
Owner: Project team

### Decision

V1 focuses on making a merchant transactable by an AI buyer end to end.

Revenue campaigns, upsell/cross-sell engines and campaign orchestration are outside v1.

### Why

The Track 1 prompt uses an OR condition. Narrowing scope allows deeper execution and stronger evidence.

### Alternatives Considered

- Build both merchant growth and AI-buyer transaction flows.
- Build a revenue-growth-only project.

### Consequences

Architecture prioritizes merchant publication, MCP access, transaction authority, Razorpay Test Mode, audit and recovery.

### Evidence / Trigger

Project scope review.

### Supersedes

None.

---

## D-002 — MCP is an adapter, not the payment authority

Status: ACTIVE
Date: <fill>
Branch: <fill>
Owner: Project team

### Decision

MCP tools call the same application services as HTTP/dashboard flows.

### Why

Financial rules must remain deterministic and centralized.

### Alternatives Considered

- Put business logic directly in MCP tools.

### Consequences

The MCP layer remains thin. Authorization, money, policy, transaction state and Razorpay calls remain in backend services.

### Evidence / Trigger

Architecture review.

### Supersedes

None.

---

## D-003 — Keep buyer consent and merchant acceptance as separate gates

Status: ACTIVE
Date: <fill>
Branch: <fill>
Owner: Project team

### Decision

Buyer authorization and merchant policy/manual acceptance are independent.

### Why

They answer different questions: whether the buyer may spend and whether the merchant accepts the order.

### Alternatives Considered

- One generic approval state.

### Consequences

Data model, state machine, audit and UI must preserve both decisions independently.

### Evidence / Trigger

Security and product review.

### Supersedes

None.

---

## D-004 — Use seven bounded workstreams across three execution lanes

Status: ACTIVE
Date: 2026-09-04
Branch: main
Owner: Project team

### Decision

Organize implementation into seven ownership-bounded workstreams and execute them through three initial lanes: `merchant/catalog`, `transaction/core`, and `buyer/agent-interface`. Freeze shared entity, application-service, provider and storage contracts before parallel feature work.

Reference Buyer Chat remains the primary guaranteed buyer demo. Remote MCP remains a separate interoperability proof over the same application services.

### Why

A solo developer using multiple coding agents needs narrow reading scope, explicit non-ownership and stable integration seams to avoid architecture drift, merge conflicts and duplicated financial logic.

### Alternatives Considered

- Assign agents by ad hoc feature without shared ownership documents.
- Split immediately into independent microservices.
- Make the external MCP client the primary demo dependency.

### Consequences

Every agent reads the master plan and only its assigned workstream plus linked canonical contracts. Cross-workstream contract changes require integrator review. Parallel development begins only after the foundation/contracts gate.

### Evidence / Trigger

Architecture/documentation planning review and the requirement to support three simultaneous coding lanes safely.

### Supersedes

None.

---

## D-005 — Use a typed Python modular-monolith foundation

Status: ACTIVE
Date: 2026-09-04
Branch: main
Owner: Project team

### Decision

Use Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL/psycopg, Alembic, pytest, Ruff and mypy. Keep shared DTOs and service/provider/storage ports in a dependency-light `contracts` package.

### Why

This stack supports a small modular monolith, explicit validation, durable relational constraints and fast contract testing without introducing service-distribution overhead.

### Alternatives Considered

- TypeScript/Node backend.
- Multiple deployable microservices from Milestone 0.
- Untyped dictionaries as cross-workstream contracts.

### Consequences

Feature workstreams implement the frozen Protocol interfaces. PostgreSQL remains the correctness target, while migration round-trips and DDL compilation can be validated without external infrastructure.

### Evidence / Trigger

Milestone 0 implementation and passing lint, type, contract, schema and migration tests.

### Supersedes

None.
