# Workstream 07 — Testing, Evidence & Demo

## Mission

Prove cross-system correctness, adversarial safety, recovery and the five-minute submission journey with honest, reproducible evidence.

## Why this workstream exists

Module tests cannot prove interface seams, concurrency, restart safety or real Razorpay/MCP interoperability. This workstream validates the integrated system; it does not absorb feature-owned testing.

## Ownership

Cross-module integration, E2E, concurrency/restart, Razorpay evidence, buyer and merchant MCP interoperability, tenant isolation, prompt-injection, timeout/reconciliation, audit reconstruction, `TESTED.md`, `evidence/` artifacts and pitch/demo validation.

## Explicit non-ownership

Feature implementation, replacing unit/module tests, redefining expected behavior, changing contracts to make tests pass, or declaring unexecuted scenarios successful.

## Inputs / dependencies

Frozen contracts and test framework at M0; deployable components from 01–06; scenario definitions from `EVALUATION.md`; real Test Mode and MCP client where required.

## Outputs / exposed contracts

Cross-system harness, fixtures (including second merchant and timeout-after-dispatch), reproducible commands, evidence artifacts, scenario ledger and rehearsed demo script.

## Relevant domain entities

Reads/asserts every canonical record, especially uniqueness, attempts, webhooks and audit events. Owns only test fixtures/artifacts, not production tables.

## Relevant database tables

May inspect every canonical table for assertions using safe test-only access. Owns no production table or migration.

## Relevant API/application services

Exercises all public HTTP/buyer/MCP flows and selected safe DB/provider inspection hooks for evidence.

## Relevant UI surfaces

Merchant dashboard, reference buyer chat (primary demo), Razorpay Test Mode checkout, audit timeline; external MCP client is a separate interoperability proof.

## Directory ownership

Cross-system test/evidence/demo directories and `docs/TESTED.md`. Feature test directories remain with their owners.

## Shared contracts consumed

All frozen entities/services/provider/storage contracts, stable errors, canonical states, scenario IDs and evidence/redaction rules.

## Shared contracts exposed

Test fixture/harness interfaces only. Tests do not redefine production contracts.

## Security/trust rules

Redact secrets/PII/payment data; isolate Test Mode; verify tenant denial and prompt injection; preserve evidence hashes/metadata where useful; never use chat logs as sole financial proof.

## Required implementation tasks

1. Map EVALUATION scenario IDs to fixtures, steps and assertions.
2. Build cross-module/E2E harness and deterministic seed data.
3. Build concurrency/restart/duplicate and timeout/reconciliation tests.
4. Run real Razorpay and separate external buyer/merchant MCP cases where required.
5. Capture redacted evidence and update `TESTED.md` from actual results.
6. Validate/rehearse the five-minute primary chat demo plus separate buyer and merchant MCP proofs.

## Phase and integration role

This workstream does not wait until all feature code is complete, but it also does not replace phase
tests. It audits phase evidence at lane milestones, maintains cross-lane fixtures, and runs assembled
scenarios only when their real dependencies exist.

- Review A/B/C phase evidence for gaps before lane integration.
- Run catalog-to-transaction checks after A3 and B2 integrate.
- Run transaction-to-provider reliability checks after B3–B6 integrate.
- Run primary Reference Buyer Chat E2E after C2/C3/C5 connect to real services.
- Run MCP interoperability separately after C4/C6.
- Run merchant MCP scenario J16 only after approved A7 and C7 integrations.
- Record `TESTED.md` results only from reproducible assembled runs.

A second-agent audit may identify findings but must send fixes back to the owning phase/lane. This
workstream must not patch feature code merely to make an E2E test pass.

## Required tests

All scenarios in `EVALUATION.md`: publication, buyer chat journey, buyer and merchant MCP interoperability, human publication confirmation, gates, verified payment, drift, retry/concurrency/restart, unknown recovery, failed checkout, webhook verification/deduplication, prompt injection, tenant isolation and audit reconstruction.

## Evidence required

Run ID, UTC time, commit, environment, DB/provider/client versions, command, redacted logs/screenshots/traces/database assertions and known limitations.

## Integration points

Every workstream; coordinate failures with the owning feature lane rather than patching across boundaries.

## Completion criteria

M7 is met, ledger totals match scenario rows, every `PASS` is reproducible and the reference-chat demo is independent of external MCP availability.

## Known non-goals

Fabricated/demo-only state, unit tests owned by features, production load certification, live-money testing and MCP-first demo design.

## Things this agent must never do

Mark visual inspection or mocks as provider proof, fabricate Razorpay evidence, alter trusted rules to pass, expose secrets, claim unrun tests, or make MCP the primary guaranteed demo path.

## Questions/escalation triggers

Escalate ambiguous acceptance criteria, environment/provider blockers, non-reproducible results, scenario-contract contradictions or evidence that challenges a canonical invariant.

See `../../MASTER_DEVELOPMENT_PLAN.md`, `../../PHASE_EXECUTION.md`, `../../EVALUATION.md`,
`../../TESTED.md`, `../../ARCHITECTURE.md` and `../../SECURITY.md`.
