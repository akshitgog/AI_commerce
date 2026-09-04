# Merchant Control Center — Component & State Specification

## Purpose
Define reusable merchant UI components and their important states. Components consume trusted service/mock data and do not own financial business logic.

## 1. MerchantAppShell
Contains sidebar, top bar, page content, Test Mode indicator, merchant identity.
States: READY, LOADING, ERROR.

## 2. OperationsMetricCard
Variants: Published Products, Awaiting Review, Processing, Recovering. Keep compact and action-oriented.

## 3. NeedsAttentionPanel
States: EMPTY, REVIEW_REQUIRED, RECOVERY_ACTIVE, MULTIPLE. Link directly to the relevant queue/transaction.

## 4. ProductTable
Columns: Product, SKU, Price, Stock, Status, Version, Updated, Actions.
States: LOADING, READY, EMPTY, ERROR.

## 5. ProductStatusBadge
States: DRAFT, PUBLISHED, UNPUBLISHED. Publication status must be obvious without color alone.

## 6. ProductEditor
Sections: Information, Description, Category, Images, Attributes, Pricing, Inventory, Publication.
States: CREATE, EDIT, SAVING, SAVED, VALIDATION_ERROR.
Frontend must not let AI-generated assistance silently mutate trusted commercial fields.

## 7. ProductImageManager
Supports 1–3 images: preview, upload state, reorder, alt text, primary image, remove.
States: EMPTY, UPLOADING, READY, ERROR.

## 8. MerchantPolicySelector
Policies: MANUAL_ALL, AUTO_BELOW_LIMIT, DENY_ALL.
States: CLEAN, DIRTY, SAVING, SAVED, ERROR.
AUTO_BELOW_LIMIT includes a formatted maximum amount input/display.

## 9. ReviewQueueTable/Card
Required data: product, quantity, buyer reference, trusted total, buyer authorization, expiry, review reason, merchant decision.
States: REVIEW_REQUIRED, APPROVING, DENYING, RESOLVED, EXPIRED.

## 10. BuyerAuthorizationBadge
States: REQUIRED, APPROVED, REJECTED, EXPIRED, INVALID.
This component never represents merchant acceptance.

## 11. MerchantDecisionBadge
States: PENDING, AUTO_ACCEPTED, REVIEW_REQUIRED, MANUALLY_ACCEPTED, DENIED, EXPIRED.
Keep visually distinct from buyer authorization.

## 12. TransactionTable
Columns: Transaction, Product, Amount, Buyer Auth, Merchant Decision, Payment, Updated.
States: LOADING, READY, EMPTY, ERROR.

## 13. TransactionStatusBadge
Human labels: Awaiting Buyer, Awaiting Merchant, Ready, Processing, Payment Pending, Verifying, Recovering, Succeeded, Failed, Cancelled, Expired.
Technical state may be shown in expandable details.

## 14. TransactionLifecycle
Stages:
Proposal → Buyer Authorization → Merchant Acceptance → Payment → Verification → Final Outcome.
Never collapse the two authorization gates or payment initiation/verification.

## 15. ProposalSummaryCard
Displays product/version, quantity, trusted unit price, trusted total, currency, proposal reference/hash/expiry as appropriate. Money is display-only trusted data.

## 16. PaymentSummaryCard
States: NOT_STARTED, PROCESSING, PAYMENT_PENDING, VERIFYING, RECOVERING, SUCCEEDED, FAILED, CANCELLED.
Provider order creation is not success.

## 17. RecoveryPanel
States: UNKNOWN, RECONCILING, RESOLVED.
UNKNOWN: definitive provider result not yet known.
RECONCILING: provider truth is being checked.
No Pay Again/Retry Payment action while unresolved.

## 18. AuditTimeline
Event fields: timestamp, actor, action, reason, previous state, new state, correlation ID, redacted provider reference.
States: LOADING, READY, EMPTY, ERROR. Raw JSON hidden by default.

## 19. MerchantDecisionControls
Actions: Approve, Deny, View details. Render only when backend state allows a merchant decision. Disable during submission and prevent accidental duplicate actions in UI, while backend remains authoritative.

## 20. Demo inspection controls
Development-only controls may simulate pending review, provider uncertainty, reconciliation, success, failure, and expiry. Keep them clearly separate from merchant UX and never present them as production controls.

## Final rule
Merchant frontend may manage catalog/policy inputs and explicit merchant decisions, but trusted transaction authority, price derivation, readiness, provider execution, idempotency, verification, reconciliation, and final financial state remain backend responsibilities.
