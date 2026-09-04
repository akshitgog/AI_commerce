# Razorpay & Database Integration Fixes

During the integration testing phase (Phase 1), we encountered five severe backend errors related to Razorpay and PostgreSQL behavior. This document explains how they occurred and how we solved them.

## 1. Razorpay Eventual Consistency (Read-After-Write)

**The Problem:**
Razorpay exhibits eventual consistency. When the buyer completes a test-mode payment in the UI, Razorpay's systems redirect the user immediately back to our platform. However, if our backend immediately queries the `GET /orders/{order_id}/payments` endpoint, Razorpay sometimes returns `count: 0` because their read replicas haven't caught up with the primary database. This led to our backend failing the reconciliation and returning `payment_failed`, even though the payment was actually successful.

**The Solution:**
We implemented a robust polling mechanism with exponential backoff (e.g., waiting 2s, 4s, 6s) inside the `RazorpayLiveAdapter`. When an order is being verified and Razorpay returns zero payments, the adapter delays and retries fetching the payments instead of immediately failing the transaction. We verified this by running the live integration test suite, which passed in ~48 seconds by successfully waiting for Razorpay's eventual consistency to resolve.

## 2. Razorpay API Shape Mismatch

**The Problem:**
We noticed that the `GET /orders/{order_id}/payments` endpoint returns a slightly different JSON structure than the webhook payload or single-payment GET endpoint. Our Pydantic models were strictly typed and failed to parse the list-endpoint structure, causing validation crashes during the polling loop.

**The Solution:**
We adapted the `RazorpayLiveAdapter` and our internal DTOs (Data Transfer Objects) to parse the specific subset of fields returned by the list endpoint safely, allowing the reconciliation loop to succeed.

## 3. PostgreSQL Schema Wipes (`drop_all`)

**The Problem:**
Our test suite was using `Base.metadata.drop_all(engine)` in the `cleanup_db` test fixture. While this works fine for in-memory SQLite (which gets thrown away anyway), running it against a shared local PostgreSQL database was disastrous. `drop_all` wiped out the actual tables but left Alembic's `alembic_version` marker behind. The next time the test suite ran, Alembic thought the database was fully migrated, but the tables were gone, causing `ProgrammingError: relation "transactions" does not exist`.

**The Solution:**
We removed `Base.metadata.drop_all(engine)` from the teardown of the integration tests (`test_transaction_queries.py`, `test_merchant_persistence.py`, `test_reconciliation_integration.py`). We replaced it with PostgreSQL-safe data cleanup:
`session.execute(text("TRUNCATE transactions, payment_attempts RESTART IDENTITY CASCADE"))`.
This deletes the test data but preserves the table schema for the next test.

## 4. SQLAlchemy Foreign Key Seed Ordering (The "Option A" Fix)

**The Problem:**
We encountered `ForeignKeyViolation` errors during test data seeding in PostgreSQL. SQLAlchemy's Unit of Work (UoW) system tries to batch and topologically sort `INSERT` statements to respect Foreign Keys. However, because our database models deliberately omitted ORM `relationship()` definitions (to enforce bounded contexts and CQRS isolation), SQLAlchemy didn't know that a `PaymentAttempt` depended on a `Transaction`. It randomly inserted the `PaymentAttempt` first, causing PostgreSQL to reject it because the parent `Transaction` didn't exist yet. (SQLite ignores FKs by default, which is why it passed in CI).

**The Solution (Option A):**
We explicitly added `session.flush()` inside the test fixtures right after creating the parent `Transaction`, but before creating the child `PaymentAttempt`. This forces SQLAlchemy to execute the `INSERT` for the transaction and establish the primary key in the database before attempting to insert the child record.

## 5. Merchant MCP Testing

**The Problem:**
The Merchant MCP server code existed, but the integration test suite for it was never written because the subagent tasked with it was cancelled.

**The Solution:**
We created a full mock `httpx.MockTransport` test harness in `tests/unit/api/mcp/test_merchant_mcp.py` to test the MCP server over real streamable HTTP. We added comprehensive coverage for:
* **Registry disjointness:** Ensuring the 6 catalog tools are exposed and buyer tools are hidden.
* **Authentication & Roles:** Verifying missing headers or bad tokens result in errors, and `VIEWER` roles cannot mutate.
* **Idempotency & Tokens:** Enforcing `Idempotency-Key` headers on mutations and verifying `publish_product` passes the confirmation token correctly.
