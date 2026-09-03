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
coverage. Real PostgreSQL migration and connection validation is configured in
`.github/workflows/m0.yml` but is not recorded as passed until that workflow runs successfully.

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
