# Reference Buyer Chat — Demo Flow

## Purpose

This document defines the exact buyer-facing demonstration journey for the AI Commerce Gateway.

The UI generator should make these states visually connected so the judge can understand the entire purchase without needing API knowledge.

---

# Demo fixture

Merchant:

```text
Demo Electronics
```

Product:

```text
65W USB-C Charger
SKU: USB-C-65W-001

Price: ₹899 INR
Stock: 10
Status: Published
```

Merchant policy:

```text
AUTO_BELOW_LIMIT

Automatically accept eligible purchases
up to ₹1,000 INR.
```

Buyer:

```text
Demo Buyer
```

All IDs and provider references used in frontend mock data are fictional demo values.

---

# Happy-path demo

## State 1 — Empty buyer chat

Display:

```text
Reference Buyer Chat

Shop from Demo Electronics using natural language.

Try:
Find me a USB-C charger under ₹1,000.
```

---

## State 2 — Buyer intent

Buyer sends:

```text
Find me a USB-C charger under ₹1,000.
```

Briefly show:

```text
Searching Demo Electronics catalog…
```

---

## State 3 — Product discovered

Assistant:

```text
I found a matching product.
```

Show:

```text
65W USB-C Charger

Demo Electronics

₹899

In stock
10 available

[View details]
[Buy for ₹899]
```

The product must look like a catalog result, not a purchase that has already been approved.

---

## State 4 — Buyer chooses product

Buyer presses:

```text
Buy for ₹899
```

This must NOT initiate payment.

It requests/prepares the purchase proposal.

---

## State 5 — Purchase proposal

Display a strong proposal card:

```text
Purchase Proposal

65W USB-C Charger
Demo Electronics

Quantity                         1
Unit price                    ₹899
─────────────────────────────────
Trusted total                ₹899

Price derived from current merchant catalog.

Proposal expires in 10:00.

Buyer approval required.

[Cancel]
[Approve ₹899]
```

At this point:

```text
Buyer Authorization
REQUIRED

Merchant Acceptance
NOT YET FINALIZED

Payment
NOT STARTED
```

---

## State 6 — Buyer authorizes

Buyer presses:

```text
Approve ₹899
```

Update progress:

```text
✓ Proposal created
✓ Buyer authorized ₹899
○ Merchant acceptance
○ Payment
○ Verification
```

The approval must clearly belong to the human buyer.

---

## State 7 — Merchant policy evaluation

For the hero demo:

```text
Purchase total: ₹899
Merchant automatic limit: ₹1,000
```

Therefore display:

```text
Merchant acceptance

✓ Automatically accepted

Demo Electronics accepts eligible purchases
up to ₹1,000.

This purchase: ₹899.
```

Progress:

```text
✓ Proposal created
✓ Buyer authorized ₹899
✓ Merchant accepted
○ Payment
○ Verification
```

---

## State 8 — Ready

Display:

```text
Ready for payment

Buyer authorization
✓ Approved

Merchant acceptance
✓ Accepted

Trusted total
₹899

[Continue to secure payment]
```

This is the first point where payment execution may proceed.

---

## State 9 — Razorpay Test Mode handoff

Display:

```text
Secure payment

65W USB-C Charger
₹899

You'll continue to Razorpay Test Mode.

[Continue to payment]
```

During a visual-only prototype, this may use a clearly mocked payment interaction.

During real integration, payment behavior must come from the backend/provider integration.

---

## State 10 — Payment submitted

After checkout:

```text
Payment submitted

Your payment was submitted.

We're waiting for confirmation.

✓ Checkout completed
● Payment pending
○ Verification
○ Final result
```

DO NOT show success here.

---

## State 11 — Verification

Display:

```text
Verifying payment

We're confirming the payment provider's
authoritative result.

✓ Checkout completed
✓ Payment submitted
● Verification
○ Final result
```

---

## State 12 — Verified success

Only after verified provider truth:

```text
✓ Payment verified

Purchase completed successfully.

65W USB-C Charger
Demo Electronics

Total paid
₹899

Transaction
TXN-8F21A
```

Progress:

```text
✓ Proposal
✓ Buyer authorization
✓ Merchant acceptance
✓ Payment
✓ Verification
✓ Complete
```

---

# Demo scenario 2 — Merchant review

Use the second product:

```text
Premium Mechanical Keyboard

₹1,299
```

Merchant automatic acceptance threshold:

```text
₹1,000
```

Buyer asks:

```text
I'd like to buy the mechanical keyboard.
```

Create proposal:

```text
Trusted total
₹1,299
```

Buyer authorizes:

```text
✓ Buyer authorized ₹1,299
```

But merchant policy must remain separate.

Depending on the canonical backend policy behavior configured for this fixture, show the appropriate merchant decision.

If manual review is required:

```text
Merchant acceptance

○ Review required

This purchase requires merchant review.

Buyer authorization
✓ Approved

Merchant acceptance
○ Pending
```

Do not allow payment while merchant acceptance is unresolved.

---

# Demo scenario 3 — Recovery

This is the key reliability demo.

Begin from a transaction that was already authorized and accepted.

Sequence:

```text
Payment dispatched
        ↓
provider response unavailable/uncertain
        ↓
Recovering
        ↓
reconciliation
        ↓
provider truth
        ↓
final state
```

Buyer UI:

```text
Recovering payment status

We haven't received a definitive payment result yet.

We're checking the payment provider directly.

No duplicate payment will be attempted.
```

Progress:

```text
✓ Proposal
✓ Buyer authorization
✓ Merchant acceptance
✓ Payment submitted
◌ Recovering
○ Final result
```

There must be NO:

```text
Pay Again
Retry Payment
Create Another Payment
```

during this state.

After reconciliation, transition to the backend-provided outcome.

Example success:

```text
✓ Payment verified

The payment provider confirmed the transaction.

₹899
65W USB-C Charger
```

---

# Demo scenario 4 — Expired/stale proposal

Show:

```text
Proposal expired

This proposal can no longer be authorized or executed.

The product's price, availability or proposal
expiry may have changed.

[Create new proposal]
```

The old buyer authorization must not appear reusable.

---

# Demo scenario 5 — Payment failure

Show:

```text
Payment unsuccessful

The provider confirmed that the payment did
not complete successfully.

No successful payment was recorded.

[View transaction]
```

A new attempt should only become available when backend state explicitly permits it.

---

# Judge-visible concepts

The happy path must visually prove:

```text
AI found the product
        ↓
backend produced trusted proposal
        ↓
human buyer explicitly authorized
        ↓
merchant independently accepted
        ↓
payment became eligible
        ↓
provider interaction occurred
        ↓
provider truth was verified
        ↓
final state was shown
```

The recovery path must visually prove:

```text
uncertain provider response
        ≠
automatic retry

uncertain provider response
        ↓
UNKNOWN / RECONCILING
        ↓
provider lookup
        ↓
authoritative outcome
```

---

# Critical demo rule

Never compress:

```text
Buyer Authorization
+
Merchant Acceptance
```

into one `Approved` step.

Never compress:

```text
Payment initiated
+
Payment verified
```

into one `Paid` step.

Those separations are central to the product demonstration.
