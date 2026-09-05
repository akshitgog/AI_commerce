# Testing & Validation

AI Commerce Gateway is backed by an automated test suite focused on the parts that matter most for agentic commerce: **financial boundaries, transaction correctness, idempotency, tenant isolation, Razorpay verification, and MCP safety.**

## Latest Backend Test Run

```text
============================= test session starts =============================
platform win32 -- Python 3.13.13, pytest-8.4.2
plugins: anyio-4.15.0, cov-6.3.0
collected 885 items

tests/integration/test_transaction_execution.py ...........s.
tests/unit/api/mcp/test_buyer_mcp.py ..........
tests/unit/api/mcp/test_buyer_mcp_interop.py ...
tests/unit/api/mcp/test_merchant_mcp.py ....
tests/unit/test_a7_idempotency.py ............
tests/unit/test_money_hardening.py ...............................
tests/unit/test_razorpay_adapter.py ....................................
tests/unit/test_transaction_state_machine.py ...........................
...

================= 879 passed, 6 skipped in 30.28s ==================
```

The suite covers:

* transaction-state transitions and invalid-transition rejection
* integer minor-unit money handling
* buyer and merchant authorization boundaries
* durable idempotency and replay protection
* Razorpay adapter behavior and payment verification
* provider failure and transaction recovery paths
* buyer and merchant MCP adapters
* tenant and role isolation
* audit/event behavior

## MCP Safety Validation

The Buyer and Merchant MCP adapters have dedicated tests verifying that external AI clients remain behind the same trusted commerce boundary.

The tests verify that:

1. Untrusted AI input is converted into typed application commands.
2. Buyer and merchant identity cannot be switched through ordinary tool parameters.
3. Role and tenant restrictions are enforced.
4. AI clients cannot directly manipulate financial state.
5. Mutating MCP operations require trusted idempotency metadata.
6. Sensitive operations remain gated by backend authorization and confirmation rules.

MCP provides interoperability with external AI clients; it does not bypass the transaction authority.

## Financial Safety Tests

Important adversarial cases include:

```text
AI-supplied price
        ↓
Rejected / ignored as financial authority

Duplicate execution request
        ↓
Same idempotency key
        ↓
No duplicate logical execution

Same idempotency key + changed request
        ↓
Rejected

Illegal transaction transition
        ↓
Deterministic error

Unverified provider result
        ↓
Cannot become SUCCEEDED

Cross-merchant request
        ↓
Access denied
```

These tests support the central rule of the project:

> **The AI can request commerce actions, but the backend decides whether they are financially valid.**

## Static Validation

Backend quality checks:

```powershell
uv run pytest
uv run ruff check .
uv run mypy
```

* **pytest** validates domain, application, provider, MCP, and integration behavior.
* **mypy** performs static type checking across the Python codebase.
* **ruff** enforces linting and code-quality rules.

## Frontend Validation

From `frontend/`:

```powershell
npm run lint
npm run build
```

These checks validate the Next.js frontend and ensure the production build completes successfully.

## Manual End-to-End Acceptance Flow

The final system is also validated through the actual commerce journey:

```text
Merchant creates/publishes product
        ↓
AI buyer discovers product
        ↓
Backend creates trusted proposal
        ↓
Buyer authorizes purchase
        ↓
Merchant policy / review gate
        ↓
Transaction becomes executable
        ↓
Razorpay Test Mode payment
        ↓
Provider verification
        ↓
Final transaction state
        ↓
Structured audit trail
```

We also validate the failure path where a provider outcome becomes uncertain and the transaction must be reconciled rather than blindly retried.

## What the Tests Demonstrate

The goal of the test suite is not simply high test count.

It provides evidence that the important agentic-commerce boundaries hold:

* AI cannot manufacture trusted price.
* AI cannot manufacture buyer consent.
* AI cannot manufacture merchant acceptance.
* AI cannot directly mark payment successful.
* retries do not silently become duplicate transactions.
* provider truth is verified before success.
* cross-tenant access is denied.
* consequential transaction changes remain auditable.

**879 passing tests support the same principle demonstrated in the live product: AI can orchestrate the purchase, but trusted backend services retain financial authority.**
