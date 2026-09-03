# Actual test and evidence ledger

## Current result

The documentation package has been reviewed for cross-document consistency. No implementation, automated test output, deployed MCP server or Razorpay Test Mode transaction evidence was available in this documentation workspace at the time of writing.

Therefore all runtime scenarios are **NOT RUN**. This status is intentionally conservative.

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
| J02 MCP discovery and proposal | NOT RUN | — | — |
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

## Judge smoke-test procedure

1. Start the documented backend, database, dashboard and MCP server.
2. Sign in as the demo merchant.
3. Create and publish a product below the configured automatic merchant-acceptance limit.
4. Connect the documented MCP client.
5. Ask it to find the product and create a proposal for one unit.
6. Approve the exact proposal through the buyer-controlled approval surface.
7. Execute and complete Razorpay Test Mode checkout.
8. Confirm the platform shows `PAYMENT_PENDING` before verified completion and `SUCCEEDED` only afterward.
9. Repeat execution with the same idempotency key and confirm the same provider order.
10. Open the audit timeline and identify buyer consent, merchant policy, revalidation, provider action and verification.

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
NOT RUN: 14
BLOCKED: 0
```

Update totals only from the scenario table after a reproducible run.
