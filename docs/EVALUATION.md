# Evaluation and evidence plan

## Evidence rule

Architecture and expected behavior are claims, not proof. A scenario passes only when it has a reproducible run and inspectable evidence recorded in `TESTED.md`.

## Required scenarios

| ID | Scenario | Expected result |
|---|---|---|
| J01 | Merchant creates and publishes product | Product is visible via MCP only after publication |
| J02 | AI discovers product and creates proposal | Proposal contains server-derived money, version, hash and expiry |
| J03 | Buyer authorization absent | Execution blocked before provider contact |
| J04 | Merchant policy requires review | Execution blocked until authenticated merchant acceptance |
| J05 | Complete Test Mode checkout | Provider order and payment phases are distinct; verified completion reaches `SUCCEEDED` |
| J06 | Buyer cap exceeded or scope mismatched | Explicit rejection and no provider call |
| J07 | Price/version changes or stock reaches zero | Original proposal rejected or requires new proposal/authorization |
| J08 | Concurrent retry plus process restart | One logical transaction and at most one live physical provider order |
| J09 | Timeout after provider dispatch | `UNKNOWN → RECONCILING →` provider-truth state; no blind retry |
| J10 | Failed/abandoned checkout | No false success; correct non-success state and reason |
| J11 | Forged and duplicate webhook | Forged event rejected; valid duplicate processed once |
| J12 | Malicious catalog prompt | Trusted money, scope and tool permissions remain unchanged |
| J13 | Merchant A accesses Merchant B data | Denied for catalog management, transactions and audit |
| J14 | Audit reconstruction | Timeline explains actor, proposal, both gates, provider action, recovery and outcome |

## Test layers

- **Unit:** money, proposal hashing, authorization matching, policy decisions and state transitions.
- **Persistence/concurrency:** uniqueness, locks, atomic event append and restart safety.
- **Contract:** authentication, schemas, stable errors, idempotency and MCP-to-application mapping.
- **Provider integration:** real Razorpay Test Mode initiation and verified payment-state mapping.
- **Adversarial:** prompt injection, forged webhooks, tenant access, replay and stale proposals.
- **Judge smoke test:** dashboard plus one MCP client through the complete journey.

## Acceptance metrics

| Metric | Target |
|---|---:|
| Unauthorized provider executions | 0 |
| Duplicate live provider orders for one logical transaction | 0 |
| False `SUCCEEDED` states | 0 |
| Accepted forged webhooks | 0 |
| Duplicate webhook double-processing | 0 |
| Cross-tenant data disclosures or mutations | 0 |
| Required deterministic scenarios correct | 100% |
| Required audit events present | 100% |
| Ambiguous timeout fixtures reconciled correctly | 100% |

## Five-minute judge sequence

1. Publish one product and show the merchant policy.
2. Discover it and create a proposal through MCP.
3. Show buyer authorization and merchant-policy decisions separately.
4. Complete Test Mode checkout and show verified payment success.
5. Replay execution and show the same provider order.
6. Trigger an over-limit or stale-proposal rejection.
7. Inject timeout-after-dispatch and show reconciliation.
8. Open the audit timeline and reconstruct the transaction.

## Required evidence package

- Setup and MCP configuration.
- Test command and full summarized output.
- Commit identifier, environment and timestamp.
- Redacted Razorpay Test Mode order/payment evidence.
- Database/provider evidence for duplicate suppression.
- Timeout/reconciliation trace.
- Webhook, prompt-injection and tenant-isolation results.
- Dashboard and MCP-flow screenshots or recording.
- Explicit limitations beside affected claims.
