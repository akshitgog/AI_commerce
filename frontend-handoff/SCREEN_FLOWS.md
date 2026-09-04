# Screen flows

## Merchant onboarding and publication

| Screen | Primary action | Important information | Result | Failure/recovery |
|---|---|---|---|---|
| Products | Create Product | Merchant, SKU, title | Draft editor | Inline validation |
| Product editor | Upload 1–3 images | Preview, alt text, order | Image metadata saved | Per-image retry/remove |
| Product editor | Set price and stock | Explicit INR and stock | Versioned draft | Stale-version conflict |
| Product detail | Publish | Readiness summary | Buyer-discoverable product | Explain missing/invalid fields |

```text
Dashboard → Products → Create Product → Upload Images → Set Price/Stock → Publish
→ available to buyer-facing catalog
```

## Merchant policy

| Screen | Primary action | Important information | Result | Failure/recovery |
|---|---|---|---|---|
| Policy | Select mode | Current version and explanation | Form adapts | Keep prior saved policy |
| Policy | Save | Threshold only for AUTO_BELOW_LIMIT | New policy version | Validation/conflict message |

## Buyer purchase

| Screen/state | Primary action | Important information | Result | Failure/recovery |
|---|---|---|---|---|
| Buyer Chat | Express intent | Query and selected merchant | Catalog results | Helpful empty/error state |
| Product card | Propose purchase | Trusted price, stock, merchant | Proposal card | Product changed/unavailable |
| Proposal | Approve exact amount | Quantity, total, expiry | Buyer authorized | Expired/stale proposal |
| Gate progress | Wait/review | Buyer and merchant gates separately | Ready | Merchant denial/manual review |
| Payment handoff | Continue securely | Trusted amount and transaction | Payment pending | Abandoned/uncertain outcome |
| Verification | View status | Provider phase and platform state | Success/failure | Recovering with safe refresh |

## Merchant manual review

```text
Review Queue → Proposal → inspect trusted total and buyer authorization
→ Approve or Deny → transaction progresses or terminates accordingly
```

Never combine the buyer-authorization badge with the merchant-decision control.

## Recovery

```text
Processing → provider result uncertain → Recovering → reconciliation/provider lookup
→ Payment pending | Succeeded | Failed
```

Show that no user action is required unless the backend explicitly requests it. Disable duplicate
payment initiation while recovery is active.

## Audit

```text
Transactions → Transaction Detail → Audit timeline → inspect decisions, reasons and redacted refs
```

Provide readable event summaries with an expandable technical section. Errors should preserve the
correlation ID for support.

