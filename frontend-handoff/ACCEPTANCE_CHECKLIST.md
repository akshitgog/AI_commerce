# Frontend acceptance checklist

## Product correctness

- [ ] Product is an AI Commerce Gateway, not a marketplace or analytics product.
- [ ] Merchant Dashboard and Reference Buyer Chat are clearly distinct.
- [ ] Normal buyer UX contains no MCP terminology.

## Merchant dashboard

- [ ] Navigation includes Overview, Products, Policy, Review Queue, Transactions, Audit and Settings.
- [ ] Overview prioritizes operational readiness/actions over vanity metrics.

## Catalog/products

- [ ] Product UI includes image, SKU, category, price/currency, stock, status and version.
- [ ] Create/edit and Publish/Unpublish interactions exist.
- [ ] One to three product images are supported with preview and alt text.
- [ ] AI suggestions cannot silently alter authoritative fields.

## Policy

- [ ] Only `MANUAL_ALL`, `AUTO_BELOW_LIMIT` and `DENY_ALL` are presented.
- [ ] Threshold input appears only for `AUTO_BELOW_LIMIT`.

## Review queue

- [ ] Trusted amount, authorization, expiry and review reason are visible.
- [ ] Approve and Deny are merchant decisions, not buyer authorization actions.

## Transactions and detail

- [ ] Tables use human-friendly status labels while preserving technical detail on demand.
- [ ] Detail separates proposal, buyer authorization, merchant decision and provider phase.
- [ ] Provider-order creation is never presented as success.

## Audit

- [ ] Audit is a structured causal timeline rather than raw logs.
- [ ] Actor, action, reason, time, status change and correlation ID are represented.
- [ ] Provider references are redacted and mock references are clearly fictional.

## Buyer chat

- [ ] Intent search, product cards, proposal, approval, progress and outcome form one journey.
- [ ] Proposal cards clearly label trusted price/total and expiry.
- [ ] Typing “buy it” does not appear to authorize payment.

## Financial trust boundaries

- [ ] Buyer authorization and merchant acceptance are visually separate.
- [ ] No authoritative money, authorization, acceptance or success decision occurs client-side.
- [ ] UI components do not call Razorpay directly.
- [ ] UI renders backend-provided trusted values and state.

## Recovery

- [ ] `UNKNOWN`/`RECONCILING` have a first-class Recovering presentation.
- [ ] Recovering does not look like an ordinary failure.
- [ ] Duplicate payment initiation is unavailable during recovery.

## Responsive design and accessibility

- [ ] Core flows work on mobile, tablet and desktop without horizontal-action loss.
- [ ] Keyboard navigation, visible focus, labels, status announcements and AA contrast are present.
- [ ] Status meaning is never conveyed by color alone.

## Code quality and backend integration readiness

- [ ] Components, types and mock data are centralized and reusable.
- [ ] A mock service layer can be replaced by the FastAPI backend.
- [ ] No undocumented backend endpoints or business rules were invented.
- [ ] Loading, empty, validation, error and stale-data states are handled.

## Demo readiness

- [ ] Merchant publication through buyer discovery is navigable.
- [ ] Buyer approval and merchant manual-review variants can be demonstrated.
- [ ] Pending, recovering, succeeded and failed transactions can be demonstrated.
- [ ] The UI is polished, cohesive and credible to fintech engineers and judges.
