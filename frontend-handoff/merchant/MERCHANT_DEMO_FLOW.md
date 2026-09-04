# Merchant Control Center — Demo Flow

## Purpose
Define the exact merchant-facing journey used alongside the Reference Buyer Chat during the judge demo.

## Fixture
Merchant: Demo Electronics
Hero product: 65W USB-C Charger — ₹899 — stock 10
Policy: AUTO_BELOW_LIMIT — maximum ₹1,000
Optional second product: Premium Mechanical Keyboard — ₹1,299

## Flow 1 — Merchant readiness
Open Overview. Show the merchant is in Test Mode and commerce is operational. Published Products and Needs Attention should be immediately visible.

## Flow 2 — Product publication
Open Products → 65W USB-C Charger. Show image, SKU USB-C-65W-001, ₹899 INR, stock 10, and publication status. If demonstrating creation, save product details/images, then publish. Buyer discovery must conceptually depend on published state.

## Flow 3 — Merchant policy
Open Policy. Select/show AUTO_BELOW_LIMIT with maximum ₹1,000. Explain in plain language that eligible purchases at or below the limit can be accepted automatically. Save through the normal merchant action.

## Flow 4 — Happy-path transaction
After the buyer creates and authorizes the ₹899 proposal, show the merchant-side transaction. Buyer Authorization must read Approved. Merchant Decision should independently show Automatically accepted because ₹899 is within the ₹1,000 policy limit.

Transaction Detail should show:
Proposal ✓
Buyer Authorization ✓
Merchant Acceptance ✓
Payment → Verification → Final Outcome

## Flow 5 — Manual review / policy boundary
Use the ₹1,299 Premium Mechanical Keyboard fixture when demonstrating a purchase that is not eligible for the ₹1,000 auto-accept limit. If canonical backend behavior routes it to review, show Review Queue with trusted total ₹1,299, buyer authorization, expiry, reason, and Approve/Deny controls. Never combine buyer approval with merchant approval.

## Flow 6 — Payment progression
After payment handoff, merchant Transactions should move through Processing / Payment Pending / Verifying according to backend state. Do not mark Succeeded merely because a provider order exists.

## Flow 7 — Recovery hero moment
Open a transaction whose provider response became uncertain after dispatch. Show Recovering prominently.

Message:
Payment status is temporarily uncertain. The system is checking the payment provider for the authoritative result. No duplicate payment will be attempted.

The audit timeline should show provider dispatch, uncertainty, reconciliation start, provider lookup/evidence, and eventual resolved state.

## Flow 8 — Verified completion
After reconciliation/verification, update to Succeeded only when provider truth confirms success. Show final amount, transaction reference, and causal audit history.

## Judge-visible proof
The merchant flow should prove:
Published merchant catalog → merchant policy → independent merchant acceptance → transaction state → provider verification/recovery → structured audit.

The merchant UI must make the safety model understandable without exposing implementation complexity.
