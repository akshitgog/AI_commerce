# AI Commerce Gateway — Frontend Acceptance Checklist

## Shared product integrity
- [ ] Merchant Control Center and Reference Buyer Chat share one coherent visual system.
- [ ] Product does not look like a marketplace or Amazon clone.
- [ ] Normal buyer UI contains no MCP terminology.
- [ ] AI never appears to control authoritative price, stock, currency, payment success, or merchant acceptance.
- [ ] Money displayed to users comes from service/mock data rather than authoritative client-side calculation.
- [ ] Buyer authorization and merchant acceptance are always separate concepts.
- [ ] Payment initiation/order creation is never rendered as verified success.
- [ ] Recovering is visually distinct from Failed.
- [ ] No duplicate-payment action is offered while recovery is active.

## Merchant surface
- [ ] Navigation includes Overview, Products, Policy, Review Queue, Transactions, Audit, Settings.
- [ ] Product management supports image, title, SKU, category, price, currency, stock, publication status, and version.
- [ ] Product editor supports 1–3 images and clearly treats price/stock/publication as merchant-controlled fields.
- [ ] Policy screen exposes MANUAL_ALL, AUTO_BELOW_LIMIT, and DENY_ALL in plain language.
- [ ] Review Queue shows trusted total, buyer authorization, expiry, review reason, and separate merchant decision controls.
- [ ] Transactions are scannable and expose buyer, merchant, payment, and recovery state.
- [ ] Transaction Detail separates Proposal, Buyer Authorization, Merchant Decision, Payment, and Recovery.
- [ ] Audit is a structured causal timeline rather than raw logs.

## Buyer surface
- [ ] Buyer can express natural-language intent.
- [ ] Product result shows merchant, image, trusted price, and availability.
- [ ] Choosing Buy creates/displays a proposal rather than immediately paying.
- [ ] Proposal displays trusted total, quantity, merchant, and expiry.
- [ ] Human buyer has an explicit bounded approval action.
- [ ] Merchant acceptance is shown after/separately from buyer authorization.
- [ ] Payment becomes available only after both gates are satisfied.
- [ ] Payment Pending and Verifying states exist.
- [ ] Verified success appears only after provider verification.
- [ ] Recovery state explains reconciliation and prevents blind retry.

## Demo quality
- [ ] ₹899 charger happy path is visually coherent end-to-end.
- [ ] ₹1,299 keyboard can demonstrate merchant policy/manual review behavior.
- [ ] Recovery path is easy for a judge to understand without reading backend code.
- [ ] Desktop demo works without horizontal overflow or clipped primary actions.
- [ ] Mock provider references are clearly fictional and never presented as real Razorpay evidence.
