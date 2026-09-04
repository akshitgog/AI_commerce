# Phase execution protocol

## Purpose

The three feature branches are long-lived ownership lanes, not permission for one agent to build an
entire lane in a single run. Every lane advances through one small phase at a time. Each phase has a
separate branch, bounded scope, tests, review, evidence and explicit approval before it enters its
lane.

`ARCHITECTURE.md`, frozen contracts and the relevant workstream remain authoritative. This protocol
controls how work is delivered; it does not change system ownership or financial semantics.

## Branch topology

```text
main
├── feature/merchant-catalog
│   └── phase/aN-<bounded-name>
├── feature/transaction-core
│   └── phase/bN-<bounded-name>
└── feature/buyer-agent
    └── phase/cN-<bounded-name>
```

Only the current phase branch for each lane should normally exist. Do not create every future phase
branch in advance.

Branch rules:

1. Create a phase branch from its current lane branch, never from another lane.
2. Implement only that phase.
3. Open/review the phase against its lane, not directly against `main`.
4. Merge an approved phase into its lane.
5. Integrate a lane into `main` only at a documented integration milestone after cross-lane checks.
6. Never merge a later phase to compensate for an incomplete earlier phase.

## Phase lifecycle

```text
NOT_STARTED
    ↓
IMPLEMENTING
    ↓
READY_FOR_REVIEW
    ├── findings → CHANGES_REQUESTED → IMPLEMENTING
    └── accepted → APPROVED → MERGED
```

These labels describe evidence-backed state. Creating a branch does not make a phase
`IMPLEMENTING`; completing code does not make it `APPROVED`.

## Mandatory phase gate

```text
implement bounded scope
        ↓
unit tests
        ↓
contract tests for exposed/consumed seams
        ↓
lint + typecheck
        ↓
targeted integration/persistence/provider tests as applicable
        ↓
agent self-review
        ↓
independent second-agent or integrator audit
        ↓
human approval
        ↓
commit/PR merged into lane
        ↓
stop; do not begin the next phase
```

Coverage percentage alone is not an exit criterion. The tests must exercise the risk introduced by
the phase. Workstream 07 validates assembled behavior but never replaces tests owned by a phase.

## Required phase prompt

Every implementation prompt must state:

```text
You are implementing ONLY Phase <ID and name>.
Do not implement later phases.

Before coding:
- read AGENT.md and docs/PHASE_EXECUTION.md
- read M0 frozen/provisional contracts
- read the relevant workstream brief and linked canonical docs
- inspect the current lane and phase branches
- list contracts consumed and exposed

Implementation scope:
- <bounded deliverables>

Required tests:
- <risk-specific unit/contract/integration tests>

Exit criteria:
- <observable completion conditions>

Forbidden:
- changing frozen contracts without escalation
- crossing workstream ownership
- implementing future phases
- claiming unrun evidence

At completion:
1. run required tests, Ruff and mypy
2. show files changed and tests added
3. show contract/schema/migration impact
4. show known limitations
5. perform a self-review
6. set READY_FOR_REVIEW only if every exit criterion is met
7. do not begin the next phase
```

## Evidence record

Record this in the phase PR/task summary; do not create a new permanent document for every phase.

```text
Phase:
Lane branch:
Phase branch:
Base commit:
Head commit:
Status:

Implementation:
- ...

Contracts consumed/exposed:
- ...

Tests added:
- ...

Validation:
ruff:
mypy:
unit:
contract:
targeted integration/provider:

Self-review findings:
- ...

Independent audit findings:
- ...

Known limitations:
- ...

Human approval:
```

`TESTED.md` remains the evidence ledger for reproducible project scenarios. A phase record does not
turn an E2E or provider scenario into `PASS`.

## Cross-lane integration

Lane phases may use frozen-contract mocks while dependencies are unavailable. Before a lane reaches
an integration milestone, replace relevant mocks with contract tests against the real seam. The
integrator checks shared-contract drift, migration collisions, API compatibility and required
cross-lane scenarios before merging a lane to `main`.

If an implementation discovers that a frozen contract must change, stop the phase and use the
contract-change process in `SHARED_CONTRACTS.md`. A phase branch never silently repairs another
lane's contract.
