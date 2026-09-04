# Actual test and evidence ledger

## Current result

The Milestone 0 foundation has local automated-test evidence. The feature scenarios below remain
**NOT RUN** because merchant, buyer-chat, MCP and Razorpay behavior is intentionally not implemented
in M0. This status is intentionally conservative.

## Milestone 0 validation

On 2026-09-04, `uv run ruff check .`, `uv run mypy`,
`uv run pytest --cov=ai_commerce_gateway` and
`uv run alembic upgrade head --sql` passed locally. The test run passed 20 tests, skipped the
PostgreSQL connection test because `TEST_DATABASE_URL` was not configured, and reported 98% line
coverage. GitHub Actions run `33817667540` then passed the PostgreSQL-backed M0 gate at commit
`1640869`, including dependency sync, Ruff, mypy, migration upgrade, tests with the 90% coverage
gate, migration downgrade and a second upgrade.

## B4 adapter validation

On 2026-09-04, the concrete Razorpay adapter passed strict mock-transport and B3 transaction-seam
tests for request mapping, Test Mode/live-mode isolation, response correlation, one-call/no-retry
behavior, secret redaction, checkout options and order-not-success semantics. With the supplied Test
Mode credentials loaded transiently, the full suite passed 373 tests with 97% coverage and skipped
four PostgreSQL-dependent tests.

The real provider test `tests/integration/test_razorpay_test_mode.py` passed and created an initial
`created` order ending `...JzsC44`, with no payment or capture truth. No J05 or other project
scenario status changes: an order-only Test Mode call is not verified payment-completion evidence.

## YAML configuration validation

On 2026-09-04, the transaction lane passed 382 tests with 96% coverage after adopting typed YAML;
five live credential/PostgreSQL tests skipped. Ten configuration tests executed default/local and
explicit deployment loading, deep merge, precedence, secret redaction, invalid types, unknown
fields/shapes and missing-file failure. Ruff, mypy and offline Alembic validation passed. This does
not change any J01–J16 status.

## B5 provider verification validation

On 2026-09-04, the provider verification phase passed 439 tests with 95% coverage, five
credential/PostgreSQL tests skipped. Ruff, mypy and offline Alembic validation passed. Frozen
M0 enums, DTOs, ORM models and migration have zero diff from the B4 lane head.

57 new B5 tests exercise: checkout HMAC signature verification and four tampering cases; raw-body
webhook HMAC verification with distinct webhook secret; durable webhook deduplication and
payload-hash reuse rejection; supported and ignored webhook event dispatch; captured/authorized/
failed payment lookup mapping; order lookup with paid/created/mismatch states; money-mismatch
rejection without state corruption; two-step causal state transition (PAYMENT_PENDING → VERIFYING
→ SUCCEEDED); terminal state downgrade prevention; out-of-order webhook ordering (failed then
captured, authorized after success); orphan and ignored webhook recording; interrupted webhook
resumption on duplicate; replay safety requiring valid signature; sanitized API error envelopes;
contract shape tests for frozen webhook command and callback routes; and real Test Mode order
creation and lookup.

Real provider run `B5-RZP-20260904-01` created and looked up a redacted order ending `...qM0YHJ`
in `created` state with matching INR 1.00 amount. No captured Test Mode payment or live webhook
delivery was exercised because those require an interactive checkout session and a separately
configured webhook secret. J05 and J11 therefore remain `NOT RUN`.

## Allowed statuses

- `PASS`: executed, matched expected behavior and evidence is linked.
- `FAIL`: executed and did not match expected behavior.
- `NOT RUN`: not executed against an implementation.
- `BLOCKED`: execution prevented by a recorded prerequisite outside the test itself.

## Run metadata template

```text
Run ID:
Date/time (UTC):
Commit:
Environment:
Database/version:
MCP client/version:
Razorpay mode: TEST
Test command:
Evidence directory/link:
Known limitations:
```

Never record credentials, webhook secrets, payment instrument data or unredacted personal information.

## Scenario ledger

| ID | Status | Actual result | Evidence |
|---|---|---|---|
| J01 Merchant publication | NOT RUN | — | — |
| J02 Reference buyer-chat discovery and proposal | NOT RUN | — | — |
| J03 Missing buyer authorization | NOT RUN | — | — |
| J04 Merchant manual-review gate | NOT RUN | — | — |
| J05 Verified Test Mode payment | NOT RUN | — | — |
| J06 Authorization limit/scope | NOT RUN | — | — |
| J07 Price/version/stock drift | NOT RUN | — | — |
| J08 Retry, concurrency and restart | NOT RUN | — | — |
| J09 Unknown-outcome reconciliation | NOT RUN | — | — |
| J10 Failed or abandoned checkout | NOT RUN | — | — |
| J11 Webhook verification/deduplication | NOT RUN | — | — |
| J12 Catalog prompt injection | NOT RUN | — | — |
| J13 Tenant isolation | NOT RUN | — | — |
| J14 Audit reconstruction | NOT RUN | — | — |
| J15 External MCP interoperability | NOT RUN | — | — |

## Judge smoke-test procedure

1. Start the documented backend, database, dashboard and MCP server.
2. Sign in as the demo merchant.
3. Create and publish a product below the configured automatic merchant-acceptance limit.
4. Open the reference buyer chat.
5. Ask it to find the product and create a proposal for one unit.
6. Approve the exact proposal through the buyer-controlled approval surface.
7. Execute and complete Razorpay Test Mode checkout.
8. Confirm the platform shows `PAYMENT_PENDING` before verified completion and `SUCCEEDED` only afterward.
9. Repeat execution with the same idempotency key and confirm the same provider order.
10. Open the audit timeline and identify buyer consent, merchant policy, revalidation, provider action and verification.

Run the external MCP interoperability scenario separately: connect the documented compatible client, discover the same product and create a proposal, then prove it reached the same backend services.

## Graceful-failure procedure

Enable the documented test-only timeout-after-dispatch fault. Execute an otherwise ready transaction. Expected state sequence:

```text
READY → EXECUTING → UNKNOWN → RECONCILING
     → PAYMENT_PENDING | SUCCEEDED | FAILED
```

Verify that the platform queries provider truth before allowing any new provider-order creation. Record the actual provider references, state events and database count with sensitive values redacted.

## Summary

```text
PASS: 0
FAIL: 0
NOT RUN: 15
BLOCKED: 0
```

Update totals only from the scenario table after a reproducible run.
