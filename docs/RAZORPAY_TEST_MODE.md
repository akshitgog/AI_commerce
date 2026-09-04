# Razorpay Test Mode truth record

## B4 scope and status

B4 implements server-side order creation and safe Standard Checkout initiation. The concrete
adapter, mock-transport integration tests and real Test Mode order check pass. Credentials were
loaded transiently from the developer-provided local CSV and were not copied, printed or committed.

## Official contract used

Razorpay's current Standard Checkout documentation requires a server-created order. The create
request uses integer currency subunits, currency and an optional receipt of at most 40 characters.
The documented initial response contains an `order_*` ID, `status: created`, `amount_paid: 0`, the
full `amount_due` and `attempts: 0`.

The order ID is passed to Standard Checkout with the public key ID, amount and currency. The key
secret never reaches the browser. A checkout success callback returns order ID, payment ID and
signature, but the signature must be verified server-side. Razorpay separately instructs merchants
to verify that successful payment status is `captured`.

Primary references:

- <https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/>
- <https://razorpay.com/docs/api/orders/create/>
- <https://razorpay.com/docs/payments/dashboard/test-live-modes/>

## Implemented B4 mapping

```text
READY
  → persist EXECUTING + attempt + idempotency claim
  → exactly one POST /v1/orders (no automatic retry)
  → validate order identity, amount, currency, receipt and initial counters
  → persist provider order evidence
  → PAYMENT_PENDING
  → return safe Standard Checkout options
```

`created` never maps to platform `SUCCEEDED`. The B4 observation deliberately has no payment or
capture state and is not marked as verified payment authenticity.

Provider timeouts, transport failures, rejected responses and malformed/mismatched success bodies
do not trigger an adapter retry. Once called through the B3 execution service, any exception after
the pre-dispatch commit follows the existing conservative `UNKNOWN` path.

## Deferred to B5/B6

- B5: checkout signature verification, webhooks, order/payment lookup translation and the exact
  verified `captured` gate for `SUCCEEDED`.
- B6: timeout-after-dispatch reconciliation and resolution from provider lookup truth.

## Reproducible real-provider check

Set ignored local Test Mode credentials, then run:

```powershell
uv run pytest tests/integration/test_razorpay_test_mode.py -m provider -s
```

Expected evidence is a redacted `...XXXXXX` order suffix, an initial `created` state, no payment ID,
no payment/capture state, and matching checkout order ID. Do not retain credentials, raw HTTP
authorization or a full provider identifier in repository evidence.

## Recorded B4 provider evidence

```text
Run ID: B4-RZP-20260904-01
Date/time: 2026-09-04 16:18 IST
Mode: Razorpay TEST
Command: uv run pytest tests/integration/test_razorpay_test_mode.py -m provider -s -q
Result: PASS
Order reference: ...JzsC44
Order state: created
Payment ID/state: none
Capture state: none
Checkout order correlation: matched
```

The complete credentialed suite subsequently passed 373 tests with four PostgreSQL-only skips and
97% package coverage. This order-only evidence does not mark J05 payment completion as passed.
