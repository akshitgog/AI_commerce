# Reference Buyer Chat — Component & State Specification

## Purpose

This document defines reusable UI components and their important states for the Reference Buyer Chat.

These components are presentation components.

They must consume trusted values/state through a replaceable frontend service layer.

They must not implement authoritative commerce or financial logic.

---

# 1. BuyerChatShell

Purpose:

Primary buyer-facing application shell.

Contains:

* lightweight header;
* conversation;
* optional transaction-progress panel;
* message composer.

States:

```text
EMPTY
ACTIVE_CONVERSATION
TRANSACTION_ACTIVE
LOADING
ERROR
```

---

# 2. BuyerMessage

Displays buyer natural-language intent.

Example:

```text
Find me a USB-C charger under ₹1,000.
```

Do not interpret financial authorization from presentation state.

---

# 3. AssistantMessage

Displays conversational AI responses.

Example:

```text
I found a matching product from Demo Electronics.
```

Should support embedded structured components such as ProductResultCard.

---

# 4. CatalogSearchState

States:

```text
IDLE
SEARCHING
RESULTS
EMPTY
ERROR
```

Searching:

```text
Searching Demo Electronics catalog…
```

Empty:

```text
No matching published products found.

Try changing your request.
```

Error:

```text
We couldn't search the catalog right now.

[Try again]
```

---

# 5. ProductResultCard

Required fields:

```text
image
title
merchantName
formattedPrice
availability
shortDescription
```

Actions:

```text
View details
Buy for <trusted formatted price>
```

Example:

```text
65W USB-C Charger

Demo Electronics

₹899
In stock · 10 available

[View details]
[Buy for ₹899]
```

The displayed price comes from backend/mock-service data.

---

# 6. ProposalCard

This should be visually more authoritative than normal conversation content.

Required fields:

```text
product
merchant
quantity
unitPrice
trustedTotal
currency
expiry
authorizationStatus
```

States:

```text
AWAITING_BUYER_AUTHORIZATION
AUTHORIZED
EXPIRED
CANCELLED
STALE
```

Awaiting:

```text
Purchase Proposal

Trusted total
₹899

Buyer approval required

[Cancel]
[Approve ₹899]
```

Authorized:

```text
Purchase Proposal

Trusted total
₹899

✓ Authorized by you
```

Expired:

```text
Proposal expired

[Create new proposal]
```

---

# 7. BuyerAuthorizationCard

States:

```text
REQUIRED
APPROVED
REJECTED
EXPIRED
INVALID
```

Required:

```text
Buyer authorization
○ Approval required
```

Approved:

```text
Buyer authorization
✓ Approved by you
₹899 · Quantity 1
```

This component represents buyer consent only.

It must never represent merchant acceptance.

---

# 8. MerchantAcceptanceCard

States:

```text
PENDING
AUTO_ACCEPTED
REVIEW_REQUIRED
MANUALLY_ACCEPTED
DENIED
EXPIRED
```

Auto accepted:

```text
Merchant acceptance
✓ Automatically accepted

Policy limit: ₹1,000
Purchase: ₹899
```

Review required:

```text
Merchant acceptance
○ Merchant review required
```

Manual acceptance:

```text
Merchant acceptance
✓ Approved by merchant
```

Denied:

```text
Merchant acceptance
× Not accepted
```

This component must remain visually distinct from BuyerAuthorizationCard.

---

# 9. GateProgress

Purpose:

Show transaction eligibility progression.

Example:

```text
Purchase progress

✓ Proposal created
✓ Buyer authorized
✓ Merchant accepted
● Payment
○ Verification
○ Complete
```

Possible stages:

```text
PROPOSAL
BUYER_AUTHORIZATION
MERCHANT_ACCEPTANCE
PAYMENT
VERIFICATION
COMPLETE
```

Do not collapse buyer and merchant gates.

---

# 10. ReadyForPaymentCard

Render only when backend/mock state says the transaction is ready.

Example:

```text
Ready for payment

✓ Buyer authorized
✓ Merchant accepted

Trusted total
₹899

[Continue to secure payment]
```

The component must not independently calculate readiness.

---

# 11. PaymentHandoffCard

Required:

```text
product
merchant
trustedTotal
paymentModeLabel
```

Example:

```text
Secure payment

65W USB-C Charger
Demo Electronics

₹899

Razorpay Test Mode

[Continue to payment]
```

During prototype generation, payment action may be mocked.

Keep provider integration behind service abstractions.

---

# 12. PaymentStatusCard

States:

```text
NOT_STARTED
PROCESSING
PAYMENT_PENDING
VERIFYING
RECOVERING
SUCCEEDED
FAILED
CANCELLED
```

Processing:

```text
Processing payment…
```

Pending:

```text
Payment submitted

Waiting for confirmation.
```

Verifying:

```text
Verifying payment

Confirming provider result.
```

Succeeded:

```text
✓ Payment verified
```

Failed:

```text
Payment unsuccessful
```

---

# 13. RecoveryCard

This component deserves special visual treatment.

States:

```text
UNKNOWN
RECONCILING
RESOLVED
```

UNKNOWN:

```text
Payment status uncertain

We don't yet have a definitive provider result.
```

RECONCILING:

```text
Recovering payment status

We're checking the payment provider directly.

No duplicate payment will be attempted.

◌ Checking…
```

Do not provide:

```text
Pay Again
Retry Payment
```

while UNKNOWN or RECONCILING.

---

# 14. SuccessReceiptCard

Render only for verified final success.

Example:

```text
✓ Payment verified

65W USB-C Charger
Demo Electronics

Total paid
₹899

Transaction
TXN-8F21A

[View transaction]
```

Provider order creation alone must never render this component.

---

# 15. FailureCard

Example:

```text
Payment unsuccessful

No successful payment was recorded.

[View details]
```

Do not imply the buyer was charged unless trusted backend data says so.

---

# 16. ProposalExpiryTimer

Display human-friendly expiry:

```text
Expires in 09:42
```

As expiry approaches, increase visual prominence slightly.

When expired:

```text
Proposal expired
```

The timer is presentation only.

The backend remains authoritative for expiry.

---

# 17. TrustedMoneyDisplay

Use consistently for trusted commercial values.

Example:

```text
Trusted total
₹899
```

Optional helper:

```text
Price derived from merchant catalog
```

Use tabular numerals where practical.

Never calculate authoritative totals from arbitrary client values.

---

# 18. MerchantIdentity

Display:

```text
Demo Electronics
```

May include:

* merchant avatar/logo placeholder;
* merchant name;
* optional verification/demo indicator.

Do not provide arbitrary client-side merchant switching that implies authorization.

---

# 19. TransactionTechnicalDetails

Secondary/expandable component.

Can display:

```text
Transaction ID
Proposal reference
Correlation ID
Platform state
Timestamp
```

Provider references must be redacted where appropriate.

Normal buyer experience should prioritize human-readable state.

---

# 20. BuyerComposer

Example placeholder:

```text
Ask about products…
```

Supports:

* text input;
* send action;
* disabled/loading state.

When a critical authorization modal/action is active, the composer must not visually substitute for that explicit authorization action.

Typing natural language alone must not appear equivalent to pressing the bounded approval control.

---

# 21. Recommended demo component composition

## Search state

```text
BuyerChatShell
├── BuyerMessage
├── AssistantMessage
└── ProductResultCard
```

## Proposal state

```text
BuyerChatShell
├── conversation
├── ProposalCard
├── BuyerAuthorizationCard
└── GateProgress
```

## Ready state

```text
BuyerChatShell
├── ProposalCard
├── BuyerAuthorizationCard
├── MerchantAcceptanceCard
├── GateProgress
└── ReadyForPaymentCard
```

## Payment state

```text
BuyerChatShell
├── GateProgress
└── PaymentStatusCard
```

## Recovery state

```text
BuyerChatShell
├── GateProgress
└── RecoveryCard
```

## Success state

```text
BuyerChatShell
├── GateProgress
└── SuccessReceiptCard
```

---

# 22. Mock transition controls

For a visual prototype only, it is acceptable to provide developer/demo controls that simulate:

```text
search result
proposal creation
buyer approval
merchant auto-accept
merchant review
payment pending
verification
UNKNOWN
RECONCILING
success
failure
expiry
```

These controls must be clearly separated from normal buyer UX.

They exist only so designers/developers can inspect every UI state.

They are not production transaction controls.

---

# 23. Accessibility

All interactive components should include:

* keyboard access;
* visible focus;
* accessible labels;
* appropriate live-region announcements for status changes;
* sufficient contrast;
* status text/icons in addition to color.

Payment and recovery status changes should be understandable without relying on color.

---

# 24. Final component rule

Every component must preserve this authority chain:

```text
AI
discovers / explains / proposes

Human Buyer
authorizes

Merchant
accepts / denies / reviews

Trusted Backend
determines readiness / executes / verifies / reconciles

Frontend
renders the resulting trusted state
```

The frontend must never silently collapse these responsibilities.
