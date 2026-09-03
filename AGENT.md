# AGENT.md — AI Commerce Gateway Development Memory Controller

## 1. Role

You are a development agent working on the **AI Commerce Gateway** project for Razorpay Track 1 — AI Growth & Agentic Commerce, AI-buyer branch.

Your job is not only to write code.

You must continuously maintain the project's development memory through these living files:

- `flow.md`
- `progress.md`
- `technical-questions.md`
- `decisions.md`

These files describe the project **as it actually evolves during implementation**.

Do not assume the architecture, transaction lifecycle, provider integration, MCP contract, UI flow, or security model is permanently fixed just because it appears in a design document.

The repository may be modified by multiple human developers and AI coding agents. The purpose of this file is to ensure that every meaningful change leaves behind a truthful record.

---

## 2. Project Objective

The project aims to:

> Make a participating merchant safely transactable by an AI buyer end to end using Razorpay Test Mode.

The intended high-level flow is:

```text
Merchant Dashboard
    ↓
Merchant publishes product
    ↓
Agent-readable catalog
    ↓
MCP-capable AI buyer
    ↓
Purchase proposal
    ↓
Human buyer authorization
    ↓
Merchant policy / manual acceptance
    ↓
Trusted backend revalidation
    ↓
Transaction Authority
    ↓
Razorpay Test Mode
    ↓
Verification / reconciliation
    ↓
Final state + structured audit timeline
```

This is a starting architecture, not an excuse to ignore the implemented code.

When code and documentation disagree, inspect the implementation and record the discrepancy.

---

## 3. Mandatory Startup Procedure

Before doing meaningful development work:

1. Read `AGENT.md`.
2. Read `flow.md`.
3. Read `progress.md`.
4. Read `technical-questions.md`.
5. Read `decisions.md`.
6. Read relevant canonical specification files:
   - `README.md`
   - `PRD.md`
   - `ARCHITECTURE.md`
   - `DATA_MODEL.md`
   - `API.md`
   - `SECURITY.md`
   - `EVALUATION.md`
   - `IMPLEMENTATION_PLAN.md`
   - `TESTED.md`
7. Inspect the current Git branch:
   ```bash
   git branch --show-current
   ```
8. Inspect the working tree:
   ```bash
   git status --short
   ```
9. Inspect recent history:
   ```bash
   git log --oneline -5
   ```
10. Inspect the relevant existing code before editing it.
11. Determine whether the requested task changes:
    - product scope;
    - architecture;
    - module responsibility;
    - data model;
    - transaction states;
    - MCP or HTTP interfaces;
    - authentication;
    - authorization;
    - merchant policy;
    - idempotency;
    - provider behavior;
    - reconciliation;
    - audit semantics;
    - tests/evidence;
    - deployment.

Never implement a significant change based only on the latest prompt without understanding current code and project memory.

---

## 4. The Four Living Files

# `flow.md` — CURRENT SYSTEM STATE

`flow.md` answers:

> "How does the implemented system work right now?"

It is not a PRD, wishlist, roadmap, or pitch document.

It must describe the **actual accepted implementation**.

Track:

- repository/module structure;
- application layers;
- merchant onboarding flow;
- catalog creation/publication flow;
- MCP flow;
- buyer identity flow;
- proposal flow;
- buyer authorization;
- merchant policy/manual review;
- transaction lifecycle;
- Razorpay integration;
- webhook flow;
- idempotency flow;
- reconciliation flow;
- audit flow;
- persistence;
- background workers;
- dashboard behavior;
- test/evidence status;
- deployment/runtime dependencies.

### Critical rule

Do not put future plans into `flow.md` as if they already exist.

If implementation changes the accepted architecture:

1. update the code;
2. validate it;
3. merge or confirm acceptance;
4. update `flow.md`;
5. record the change in `progress.md`;
6. update `technical-questions.md` if understanding changed;
7. update `decisions.md` if an architectural/product decision was made.

---

# `progress.md` — DEVELOPMENT HISTORY

`progress.md` answers:

> "What changed, when, why, on which branch, and what evidence shows it worked?"

It is append-only.

Every meaningful entry MUST use this format:

```text
## Entry NNN — <short title>

Date/time:       <YYYY-MM-DD HH:MM IST>
Git branch:      <exact branch name>
Commit:          <short hash if available>
Author/Agent:    <developer or agent identifier>
Workstream:      merchant | catalog | auth | transaction | provider | mcp | dashboard | infra | tests | docs
Change:          <one-line summary>
Files/modules:   <changed files/modules>

### What Changed
<detailed description>

### Reason
<why the change was made>

### Technical Impact
<affected flows, modules, contracts or invariants>

### Validation
<exact tests/commands/manual checks performed>

### Evidence
<test output, screenshot, trace, provider ID reference, or none>

### Result
SUCCESS / PARTIAL / FAILURE

### Problems / Limitations
<remaining issues>

### Next Step
<next concrete action>
```

Track:

- implementation work;
- schema changes;
- API changes;
- MCP changes;
- transaction-state changes;
- auth/policy changes;
- Razorpay adapter changes;
- webhook changes;
- failure injection;
- tests;
- bugs;
- experiments;
- failed approaches;
- reversions;
- important refactors;
- documentation corrections.

Do not log trivial formatting-only edits.

Never invent the branch name.

---

# `technical-questions.md` — EVOLVING TECHNICAL KNOWLEDGE

This file answers:

> "What technical questions arose, what evidence do we have, and what remains unknown?"

Questions should emerge from actual implementation, provider behavior, tests, debugging, or review.

Use:

```text
## Q: <question>

Status: OPEN / ANSWERED / SUPERSEDED
Branch-raised: <exact branch>
Last-updated-by: <developer or agent>

Context:
<why this matters>

Current Answer:
<what evidence currently supports>

Evidence:
<code, test, Razorpay behavior, trace, docs, experiment>

Decision:
<what implementation currently does>

Confidence:
HIGH / MEDIUM / LOW

Last updated:
<YYYY-MM-DD>

Related modules:
<files/modules>
```

Examples of valid questions:

- What exact Razorpay Test Mode provider state is sufficient for platform `SUCCEEDED`?
- Can a timeout occur after provider-order creation but before the response is received?
- Which fields are required to safely reconcile an unknown provider outcome?
- Should a changed product version always invalidate authorization?
- How should duplicate MCP calls map to idempotency keys?
- Which audit events must be atomic with transaction-state changes?
- Can merchant manual review expire independently of buyer authorization?

Rules:

- Do not invent answers.
- If uncertain, mark `OPEN`.
- Separate hypothesis from verified behavior.
- If later evidence changes the answer, update the current answer and record the old understanding in `progress.md`.

---

# `decisions.md` — IMPORTANT PROJECT DECISIONS

This file answers:

> "Which important choices did we intentionally make, and why?"

Use it for decisions that affect future development.

Examples:

- PostgreSQL instead of SQLite for durable concurrency tests.
- One MCP client in v1 instead of multiple client integrations.
- Buyer consent and merchant acceptance remain independent gates.
- AI enrichment cannot modify price, stock, currency, or publication state.
- `UNKNOWN` blocks blind retry.
- Public UI shows simplified transaction labels while backend keeps canonical internal states.

Each decision MUST use:

```text
## D-NNN — <decision title>

Status: ACTIVE / SUPERSEDED / REJECTED
Date: <YYYY-MM-DD>
Branch: <branch where decision was made>
Owner: <developer / team / agent>

### Decision
<what was decided>

### Why
<reasoning>

### Alternatives Considered
- <alternative>
- <alternative>

### Consequences
<what this changes>

### Evidence / Trigger
<test, provider behavior, review finding, or requirement>

### Supersedes
<decision ID or none>
```

Do not use `decisions.md` for temporary implementation notes.

---

## 5. Canonical Specification vs Living State

The project has two kinds of documentation.

### Canonical specification

Examples:

```text
README.md
PRD.md
ARCHITECTURE.md
DATA_MODEL.md
API.md
SECURITY.md
EVALUATION.md
IMPLEMENTATION_PLAN.md
```

These describe intended behavior.

### Living implementation memory

```text
flow.md
progress.md
technical-questions.md
decisions.md
TESTED.md
```

These describe what actually happened during implementation.

If implementation intentionally changes the specification:

1. record the reason in `decisions.md`;
2. record the code change in `progress.md`;
3. update canonical docs if the decision is accepted;
4. update `flow.md` after accepted implementation;
5. update tests/evidence.

Never silently allow specs and code to drift.

---

## 6. TESTED.md Rule

`TESTED.md` is the evidence ledger.

Do not mark a scenario `PASS` because:

- code looks correct;
- unit tests for a different path pass;
- architecture says it should work;
- a mock succeeded when the scenario requires Razorpay Test Mode;
- the UI looks correct.

A scenario can be `PASS` only after it was actually executed with inspectable evidence.

Allowed states:

- `PASS`
- `FAIL`
- `NOT RUN`
- `BLOCKED`

When implementation work affects an evaluation scenario:

1. run the relevant scenario;
2. capture evidence;
3. update `TESTED.md`;
4. link/mention that evidence in the corresponding `progress.md` entry.

---

## 7. Core Project Invariants

Treat these as high-risk invariants.

Do not weaken them without an explicit decision.

### Money

- Money is stored in integer minor units.
- Currency is explicit.
- AI/client-supplied totals are never authoritative.
- Price comes from server-side merchant-owned product data.

### AI

The AI may:

- search;
- explain;
- propose;
- request authorization;
- invoke narrow tools.

The AI may not:

- approve itself;
- fabricate buyer consent;
- change trusted price;
- override merchant policy;
- set provider state;
- call Razorpay directly;
- force transaction success.

### Buyer authorization

Buyer authorization must remain bounded by the relevant scope such as:

- buyer;
- proposal hash;
- merchant;
- product;
- quantity;
- amount;
- currency;
- expiry.

### Merchant acceptance

Merchant policy is independent from buyer consent.

Merchant approval cannot replace buyer authorization.

### Idempotency

Repeated, concurrent, or replayed execution must not create duplicate physical provider orders.

Durable database uniqueness is the final correctness guard.

### State machine

State changes must follow valid transitions.

Do not collapse provider-order creation into payment success.

### Unknown provider outcomes

A provider timeout after dispatch must not trigger blind retry.

Use:

```text
UNKNOWN → RECONCILING → provider truth
```

before allowing another creation attempt.

### Audit

Consequential financial actions must emit structured audit events.

Operational logs are not a substitute for the financial audit trail.

### Tenant isolation

Merchant A must not read or mutate Merchant B's:

- products;
- policies;
- proposals;
- transactions;
- audit events.

---

## 8. Internal State vs UI Status

The backend may use detailed canonical states.

The normal merchant/buyer UI should use simplified labels.

Recommended mapping:

```text
PROPOSED / BUYER_AUTH_REQUIRED
→ Awaiting buyer approval

MERCHANT_POLICY_PENDING / MERCHANT_REVIEW_REQUIRED
→ Awaiting merchant approval

READY
→ Ready

EXECUTING / VERIFYING
→ Processing payment

PAYMENT_PENDING
→ Payment pending

UNKNOWN / RECONCILING
→ Recovering

SUCCEEDED
→ Succeeded

FAILED
→ Failed

CANCELLED
→ Cancelled

EXPIRED
→ Expired
```

Do not simplify the internal state machine merely to match the UI.

---

## 9. Branch Rules

Recommended branch prefixes:

```text
merchant/<feature>
catalog/<feature>
auth/<feature>
transaction/<feature>
provider/<feature>
mcp/<feature>
dashboard/<feature>
tests/<feature>
infra/<feature>
fix/<description>
docs/<description>
```

Examples:

```text
provider/razorpay-spike
transaction/idempotency
auth/buyer-approval
mcp/catalog-tools
dashboard/audit-timeline
tests/timeout-reconciliation
```

Every `progress.md` entry must contain the exact active branch.

Run:

```bash
git branch --show-current
```

Never invent it.

---

## 10. Development Change Protocol

### Before

Read project memory and inspect current state.

Run:

```bash
git branch --show-current
git status --short
git log --oneline -5
```

Inspect relevant tests and code.

### During

Prefer the smallest correct change.

Do not redesign unrelated modules.

Do not weaken a transaction invariant merely to make a demo pass.

Keep Razorpay-specific code inside the provider adapter.

Keep MCP thin.

Keep trusted money/policy/state logic in application/domain services.

### After

Ask:

```text
Did architecture change?
Did a contract change?
Did the data model change?
Did a security invariant change?
Did transaction semantics change?
Did Razorpay behavior teach us something?
Did a test/evidence result change?
Did we make a decision future agents must know?
```

Then update the correct living files.

---

## 11. Documentation Update Matrix

### Code changed, architecture unchanged

Update:

```text
progress.md
```

Possibly:

```text
TESTED.md
technical-questions.md
```

### Architecture changed

Update after accepted implementation:

```text
flow.md
progress.md
decisions.md
```

Then update canonical spec if appropriate.

### Technical discovery without code change

Update:

```text
technical-questions.md
progress.md
```

### Important intentional decision

Update:

```text
decisions.md
progress.md
```

### Failed experiment

Update:

```text
progress.md
technical-questions.md
```

Do not hide failed attempts.

### Test/evidence completed

Update:

```text
TESTED.md
progress.md
```

---

## 12. Razorpay Integration Integrity

Do not assume provider behavior.

During the provider spike, record:

- request type;
- returned order identifier;
- payment identifier;
- checkout behavior;
- signature verification inputs;
- webhook behavior;
- capture behavior;
- provider lookup behavior;
- timeout behavior;
- what exact provider truth maps to platform `SUCCEEDED`.

If Razorpay Test Mode behavior differs from current documentation:

1. record a technical question;
2. gather evidence;
3. make a decision;
4. update architecture/spec if needed.

Do not fake provider evidence.

---

## 13. MCP Integrity

MCP is an adapter.

The MCP layer should not independently implement:

- money calculation;
- authorization;
- merchant policy;
- state transitions;
- Razorpay calls;
- reconciliation.

Canonical MCP tools may include:

```text
search_catalog
get_product
create_purchase_proposal
request_authorization
execute_transaction
get_transaction_status
get_transaction_audit
```

If tool semantics change, update:

- code;
- `API.md`;
- `flow.md` after acceptance;
- `progress.md`;
- relevant tests.

---

## 14. Audit Requirements

Every consequential financial event should be able to answer:

- who acted;
- which buyer;
- which merchant;
- which proposal;
- which authorization;
- which merchant policy/decision;
- previous state;
- new state;
- reason;
- provider reference if applicable;
- correlation ID;
- timestamp.

Never rely on raw chat history as the only financial record.

---

## 15. Completion Checklist

Before declaring a meaningful task complete:

```text
[ ] Read AGENT.md
[ ] Read flow.md
[ ] Read progress.md
[ ] Read technical-questions.md
[ ] Read decisions.md
[ ] Inspected relevant canonical specs
[ ] Ran git branch --show-current
[ ] Ran git status --short
[ ] Inspected existing code/tests
[ ] Implemented the requested change
[ ] Ran relevant validation/tests
[ ] Inspected actual output
[ ] Updated progress.md
[ ] Updated technical-questions.md if knowledge changed
[ ] Updated decisions.md if a durable decision changed
[ ] Updated flow.md only for accepted implementation state
[ ] Updated TESTED.md only with real executed evidence
[ ] Recorded unresolved issues honestly
[ ] Did not fabricate Razorpay behavior or test evidence
```

---

## 16. Quick Reference

```text
AGENT.md
    |
    +-- flow.md
    |     CURRENT IMPLEMENTED SYSTEM
    |
    +-- progress.md
    |     WHAT CHANGED / WHEN / WHY / BRANCH / VALIDATION
    |
    +-- technical-questions.md
    |     WHAT WE KNOW / DON'T KNOW
    |
    +-- decisions.md
    |     IMPORTANT INTENTIONAL CHOICES
    |
    +-- TESTED.md
          WHAT HAS ACTUALLY BEEN PROVEN
```

The guiding rule is:

> Code shows what exists. Tests show what works. `flow.md` explains the current system. `progress.md` preserves history. `technical-questions.md` preserves uncertainty and learning. `decisions.md` preserves intent. `TESTED.md` preserves proof.
