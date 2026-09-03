# Workstream 04 — Razorpay & Recovery

## Mission

Isolate Razorpay Test Mode integration and turn uncertain provider interactions into verified, recoverable evidence without duplicate orders.

## Why this workstream exists

Provider order, payment, capture and platform transaction states are different facts. This boundary prevents provider mechanics from leaking into the transaction authority.

## Ownership

Razorpay adapter; order creation; checkout initiation/verification; webhook signature verification/deduplication; provider lookup; `PaymentAttempt`; `ProviderWebhook`; `UNKNOWN`/`RECONCILING` mechanics; timeout-after-dispatch fixture; provider evidence/state translation.

## Explicit non-ownership

Buyer/merchant authorization, authoritative totals, policy, platform transition rules, chat/MCP tools, catalog or dashboard.

## Inputs / dependencies

Provider abstraction and transition commands from 03; secrets/config/DB/worker primitives from 06; verified Razorpay Test Mode behavior from the spike.

## Outputs / exposed contracts

`provider.create_order`, `provider.verify_checkout`, `provider.handle_webhook`, `provider.lookup_order`, `provider.lookup_payment`, plus redacted provider evidence for transaction decisions.

## Relevant domain entities

Owns `PaymentAttempt` and `ProviderWebhook`; references `Transaction` and emits evidence consumed by `TransactionEvent` through 03.

## Relevant database tables

`PaymentAttempt` and `ProviderWebhook`, including provider-event uniqueness and transaction/attempt relationships coordinated with 03 and 06.

## Relevant API/application services

Checkout initiation details, `/webhooks/razorpay`, `/checkout/razorpay/verify`, safe reconcile lookup and internal provider adapter APIs.

## Relevant UI surfaces

No business UI ownership. Supplies checkout and redacted phase data.

## Directory ownership

Provider adapter, webhook/callback endpoints, reconciliation worker/service, provider persistence and tests.

## Shared contracts consumed

Provider abstraction, transaction commands, payment-attempt uniqueness, stable errors, correlation/audit conventions.

## Shared contracts exposed

Normalized provider outcomes with evidence; never raw provider authority over platform state.

## Security/trust rules

Keep credentials server-side; verify signatures using exact raw/input rules; deduplicate webhooks; redact sensitive references; independently query provider truth on uncertainty; separate order/payment/capture states.

## Required implementation tasks

1. Run/document Test Mode spike for order, checkout, signatures, webhooks, capture and lookup.
2. Implement adapter and normalized evidence objects.
3. Persist attempts before/around dispatch per frozen transaction algorithm.
4. Implement callback verification and deduplication.
5. Implement timeout fixture and reconciliation lookup flow.

## Required tests

Order creation not success, valid/invalid signatures, duplicate/out-of-order webhook, provider translation, timeout after dispatch, unknown no blind retry, lookup resolution, one live order under concurrency/restart, redaction and failure/abandoned checkout.

## Evidence required

Actual Test Mode request/response identifiers redacted, webhook/callback proof, DB attempt counts, transition timeline and repeatable commands. Never substitute mocks where the scenario requires Razorpay.

## Integration points

03 transaction authority, 06 DB/config/worker, 01 checkout/status display and 07 evidence harness.

## Completion criteria

M3–M5 provider behavior is repeatably proven, and `SUCCEEDED` is impossible without the documented verified condition.

## Known non-goals

Live money, refunds, subscriptions, multiple providers, smart routing and generalized payment-gateway features.

## Things this agent must never do

Approve buyer/merchant gates, compute totals, set platform state outside transaction commands, treat an order as payment, blind-retry unknown dispatch or fabricate provider evidence.

## Questions/escalation triggers

Escalate any undocumented Test Mode behavior, success/capture ambiguity, lookup inconsistency, signature-field change or need for a second provider attempt.

See `../../MASTER_DEVELOPMENT_PLAN.md`, `../../ARCHITECTURE.md`, `../../API.md`, `../../DATA_MODEL.md`, `../../SECURITY.md` and `../../EVALUATION.md`.
