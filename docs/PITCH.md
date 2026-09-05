# PITCH.md — Five-Minute Judge Pitch and Demo

## Purpose

This document is the exact judge-facing story for the AI Commerce Gateway.

The pitch must prove four things quickly:

1. **Merchant enablement:** an ordinary merchant can become AI-transactable without building agent infrastructure.
2. **Natural buyer experience:** a buyer can purchase through a simple reference chat.
3. **Safe money execution:** the AI can propose, but the backend alone controls authorization, merchant policy, idempotency, Razorpay execution, verification and recovery.
4. **Interoperability:** the same merchant/backend can also be reached by a compatible external AI application through MCP.

Do not spend the pitch teaching MCP. MCP is the interoperability proof, not the product story.

---

## One-line pitch

> **AI Commerce Gateway lets a nontechnical merchant become safely purchasable by AI buyers: the merchant publishes once, buyers can purchase through natural-language AI interfaces, and every money action is bounded, gated, verified and auditable through Razorpay Test Mode.**

## 20-second problem statement

Today, exposing a merchant to AI buyers usually assumes someone has already built the catalog integration, tool layer, payment controls and failure handling.

A local merchant should not need to understand any of that.

They should publish products normally, define what orders they will accept, and become available to AI buyers while the platform keeps the AI away from unrestricted money authority.

---

# Architecture to show

Use one architecture slide/screen only.

```text
                           AI COMMERCE GATEWAY

MERCHANT
   │
   ▼
Merchant Dashboard
   │
   ├── Catalog / publish
   ├── Merchant policy
   ├── Manual review
   └── Orders / audit
   │
   ▼
                       SAME COMMERCE BACKEND
                      ┌─────────────────────┐
                      │ Catalog             │
                      │ Proposal            │
                      │ Buyer Authorization │
                      │ Merchant Policy     │
                      │ Transaction Authority
                      │ Idempotency         │
                      │ Audit               │
                      └─────────┬───────────┘
                                │
                                ▼
                         Razorpay Adapter
                                │
                                ▼
                         Razorpay Test Mode
                                │
                                ▼
                   Verification / Reconciliation


PRIMARY BUYER PATH                     EXTERNAL INTEROPERABILITY
──────────────────                     ─────────────────────────
Nontechnical Buyer                     MCP-capable AI Application
        │                                        │
        ▼                                        ▼
Reference Buyer Chat                      Remote MCP Server
        │                                        │
        ▼                                        ▼
AI / Narrow Tools                         MCP Adapter
        │                                        │
        └──────────────────┬─────────────────────┘
                           ▼
                    SAME COMMERCE BACKEND
```

### What to say while this is visible

> “There are two ways into the same backend. Our reference chat is the guaranteed buyer experience. MCP is a separate interoperability path for compatible external AI applications. Neither path owns payment logic. Both terminate at the same trusted transaction authority.”

Then immediately move to the demo.

---

# Five-minute timeline

## 0:00–0:35 — Problem + product

### Screen

Show merchant dashboard landing page with one demo merchant.

### Say

> “We are solving the AI-buyer half of Track 1. A merchant should not need to build an MCP server, payment state machine or agent security model just to become purchasable by AI.”

> “Our gateway gives the merchant a normal dashboard, a buyer a normal AI chat, and external AI systems a standardized MCP path — all backed by the same trusted transaction authority.”

### Prove

- merchant is the primary customer;
- nontechnical merchant/buyer experience;
- this is not a marketplace.

Do not discuss every architecture component yet.

---

## 0:35–1:05 — Merchant becomes AI-transactable

### Screen

Merchant dashboard → Products.

Show or create one product:

```text
Product: USB-C Charger
Price: ₹899
Stock: 10
Status: PUBLISHED
Policy: AUTO_BELOW_LIMIT, max ₹1,000
```

### Say

> “The merchant controls authoritative price, currency, stock and publication. AI enrichment can help with descriptions, but it can never change trusted commercial fields.”

> “Once published, this product becomes available to buyer-facing tools.”

### Prove

- merchant onboarding/publication;
- merchant owns commercial truth;
- merchant policy exists before purchase.

---

## 1:05–2:05 — Buyer chat → immutable proposal → two independent gates

### Screen

Open the reference buyer chat.

Buyer prompt:

```text
Find me a USB-C charger under ₹1,000 and buy one.
```

Show product discovery.

Then create proposal.

Expected buyer-facing proposal:

```text
USB-C Charger
Quantity: 1
Trusted unit price: ₹899
Total: ₹899
Proposal expires: ...
Buyer approval: REQUIRED
Merchant acceptance: PENDING
```

### Say

> “The AI can search and propose, but it cannot decide the trusted price. ₹899 is loaded from the merchant's structured catalog by the backend.”

> “Before money can move, two independent gates must pass: buyer consent and merchant acceptance.”

Approve the proposal through the buyer-controlled approval action.

Show merchant policy result:

```text
Buyer authorization: APPROVED
Merchant policy: ALLOW
Transaction: READY
```

### Prove

- server-derived price;
- immutable proposal;
- human buyer owns consent;
- merchant acceptance is separate;
- AI cannot self-approve.

---

## 2:05–2:55 — Razorpay Test Mode and verified success

### Screen

Execute transaction.

Show Razorpay Test Mode checkout.

Complete the test payment.

Immediately return to transaction page.

Show a short state progression:

```text
READY
→ EXECUTING
→ PAYMENT_PENDING
→ VERIFYING
→ SUCCEEDED
```

### Say

> “Creating a Razorpay order is not success. We only mark this transaction successful after provider payment truth is verified.”

Show redacted Razorpay order/payment reference and final state.

### Prove

- real Razorpay Test Mode integration;
- provider order and payment success are different;
- `SUCCEEDED` is verified, not guessed by the AI.

---

## 2:55–3:25 — Idempotency / duplicate suppression

### Screen

Repeat the same execute action with the same idempotency key or use a prepared `Replay request` demo button.

Show:

```text
Same logical transaction
Same provider attempt/order
No second live provider order
```

### Say

> “AI systems retry. Networks retry. Users repeat themselves. That must not create duplicate money actions.”

> “Our durable idempotency record and database constraints return the existing result instead of creating another provider order.”

### Prove

- retries are safe;
- correctness survives beyond an in-memory lock;
- at most one unambiguously live provider order per logical transaction.

---

## 3:25–4:05 — Graceful failure: unknown provider outcome

### Screen

Use a clearly labeled **test-only fault injection**:

```text
Simulate timeout after Razorpay dispatch
```

Run a prepared second transaction.

Show:

```text
READY
→ EXECUTING
→ UNKNOWN
→ RECONCILING
→ PAYMENT_PENDING / SUCCEEDED / FAILED
```

### Say

> “The dangerous case is when the request reaches Razorpay but our response is lost. Blindly retrying could create another provider action.”

> “So `UNKNOWN` is a real state. We block another creation attempt, query provider truth, and reconcile before proceeding.”

### Prove

- explicit graceful failure;
- no blind retry;
- provider reconciliation;
- Track 1 failure-handling bar.

---

## 4:05–4:30 — Audit trail

### Screen

Open the transaction audit timeline.

Show compact events such as:

```text
Proposal created
  actor: buyer AI
  reason: catalog selection

Buyer authorized
  actor: human buyer
  proposal hash: ...

Merchant policy allowed
  reason: AUTO_BELOW_LIMIT

Execution started
  idempotency key: ...

Provider order created
  Razorpay ref: redacted

Payment verified
  source: provider verification

Transaction succeeded
```

### Say

> “This is not a chat transcript pretending to be an audit log. The system records a structured causal financial history: who acted, why, what state changed, which authorization applied and what provider truth was verified.”

### Prove

- explainability;
- causal audit;
- buyer and merchant gates visible independently.

---

## 4:30–4:50 — MCP interoperability proof

### Screen

Switch to one prepared compatible MCP client or a terminal/client trace.

Ask:

```text
Find the published USB-C charger from Demo Merchant.
```

Show the MCP call:

```text
search_catalog
```

Then optionally:

```text
create_purchase_proposal
```

Show that the proposal appears in the **same backend/dashboard**.

### Say

> “The buyer does not need MCP in our product. This is the interoperability proof. A compatible external AI application can call our remote MCP server and reach the exact same commerce services.”

> “We do not maintain another payment engine for MCP.”

### Prove

- remote MCP server works;
- external AI interoperability;
- shared backend semantics.

### Important

Do not redo the Razorpay payment through MCP unless the demo is extremely stable and time remains. The payment correctness was already proved through the core buyer path.

---

## 4:50–5:00 — Close

### Screen

Return to architecture or final transaction/audit view.

### Say

> “The differentiator is not that an AI can call checkout. It is that a normal merchant can become AI-transactable while the AI remains outside the money trust boundary.”

> “One merchant publication, multiple safe AI entry points, one transaction authority, verified Razorpay truth, safe retries, recovery and a complete audit trail.”

Stop.

---

# What the judge should remember

```text
MERCHANT ENABLEMENT
Merchant publishes once.

NATURAL BUYER EXPERIENCE
Buyer uses reference chat.

AI INTEROPERABILITY
External compatible AI can use MCP.

TRUSTED MONEY BOUNDARY
AI proposes.
Backend authorizes, gates and executes.

PAYMENT CORRECTNESS
Razorpay order ≠ payment success.

RELIABILITY
Retries are idempotent.
Unknown outcomes reconcile.

AUDITABILITY
Every consequential money action is reconstructable.
```

---

# Demo flow as one sequence

```text
Merchant
  ↓
Dashboard
  ↓
Publish Product
  ↓
Published Catalog
  ↓
Reference Buyer Chat
  ↓
search_catalog
  ↓
Product Result
  ↓
create_purchase_proposal
  ↓
Server-derived immutable proposal
  ↓
Human Buyer Approval
  ↓
Merchant Policy
  ↓
READY
  ↓
Transaction Authority
  ↓
Revalidate price / version / stock
  ↓
Durable idempotency
  ↓
Razorpay Test Mode
  ↓
PAYMENT_PENDING
  ↓
Verification
  ↓
SUCCEEDED
  ↓
Audit Timeline

Then prove:

Repeated execute
  ↓
Same logical/provider result

Timeout after dispatch
  ↓
UNKNOWN
  ↓
RECONCILING
  ↓
Provider truth

Finally:

External MCP-capable AI client
  ↓
Remote MCP Server
  ↓
search_catalog / create_purchase_proposal
  ↓
Same backend
```

---

# Prepared demo data

Use one product only for the main live flow.

Recommended fixture:

```text
Merchant: Demo Electronics
Product: USB-C Charger
SKU: USB-C-65W-001
Price: ₹899
Currency: INR
Stock: 10
Published: true

Merchant policy:
AUTO_BELOW_LIMIT
auto_accept_max = ₹1,000
```

Prepare a second product only if needed for rejection:

```text
Product: Premium Mechanical Keyboard
Price: ₹1,299
```

This lets the buyer-limit/merchant-policy test be demonstrated quickly if asked.

The second merchant fixture is for tenant-isolation tests, not the main pitch.

---

# Screens that should already be open before presenting

Have these tabs/windows prepared:

1. Merchant dashboard — Products.
2. Reference buyer chat.
3. Transaction detail/audit page.
4. Razorpay Test Mode checkout/provider evidence.
5. MCP-capable external client or prepared MCP terminal trace.
6. Optional test/evidence terminal.

Do not waste pitch time logging in, editing environment files or explaining installation.

---

# MCP demo fallback

The core demo must not fail because an external MCP client has an environment/account problem.

Preferred order:

```text
A. Live MCP client
B. Live MCP inspector/terminal client
C. Prepared timestamped recording + server logs
D. Automated MCP contract test output
```

If the external client fails, say:

> “The core transaction flow is independent of the external client. Here is the MCP server contract/test trace showing the same backend service invocation.”

Never pretend a prerecorded MCP trace is live. Label evidence accurately.

---

# Demo failure fallbacks

## Razorpay checkout is slow

Show the already-created test transaction/provider lookup evidence and continue to audit. State that it is prepared evidence from the same build.

## Webhook is delayed

Use provider lookup/reconciliation, if that is part of the implemented verification contract.

## Reference AI produces unexpected prose

The underlying tools must still expose deterministic operations. Use a prepared prompt or direct UI action without bypassing backend gates.

## Fault injection produces an unexpected terminal state

That is acceptable if reconciliation resolves according to provider truth. The requirement is safe recovery, not a predetermined `SUCCEEDED`.

---

# Questions judges may ask

## “Why MCP if you already have a chat?”

Answer:

> “Our chat proves the product works for a normal buyer. MCP proves the merchant is not locked to our chat. Compatible external AI applications can call the same controlled commerce capabilities without us rebuilding the transaction system for each one.”

## “Can the AI approve the payment itself?”

Answer:

> “No. It can request authorization, but buyer consent is owned by an authenticated human-controlled surface or an already-established bounded mandate.”

## “Why separate merchant approval?”

Answer:

> “Buyer consent answers whether the buyer may spend. Merchant acceptance answers whether the merchant will accept that order. Those are different authorities and we preserve both.”

## “What stops duplicate payments?”

Answer:

> “Database-backed idempotency, transaction locking and a unique logical-transaction-to-provider-attempt relationship. Unknown provider outcomes reconcile before another creation attempt.”

## “Why not just treat the Razorpay order ID as success?”

Answer:

> “An order is payment initiation, not proof that payment completed. `SUCCEEDED` requires verified provider payment/capture truth.”

## “Is this a marketplace?”

Answer:

> “No. Merchants onboard to the gateway and own their catalog. V1 does not rank merchants, scrape the web or route across an open marketplace.”

---

# What not to say

Avoid these claims:

```text
“Works with every AI.”
“Any LLM can connect directly.”
“The AI makes the payment.”
“Razorpay order created means payment succeeded.”
“MCP is our product.”
“We built a marketplace.”
“Our audit is the chat history.”
```

Use:

```text
“MCP-capable external AI application.”
“The AI proposes; the backend is transaction authority.”
“Reference chat is the guaranteed buyer experience.”
“MCP is the interoperability layer.”
“Success requires verified provider truth.”
“Structured causal financial audit.”
```

---

# Final pitch checklist

Before presenting:

```text
[ ] One merchant product is already published
[ ] Merchant policy is configured
[ ] Reference buyer chat is working
[ ] Buyer approval surface is working
[ ] Razorpay Test Mode credentials are valid
[ ] One happy-path payment has been rehearsed
[ ] Idempotency replay proof is ready
[ ] Timeout-after-dispatch fixture is ready
[ ] Reconciliation path is ready
[ ] Audit timeline is populated
[ ] MCP server is reachable
[ ] One compatible MCP client/trace is ready
[ ] Second merchant fixture exists for tenant-isolation evidence
[ ] All displayed evidence is from the current build or clearly labeled otherwise
```

## Core message

> **MCP is the interoperability proof. The AI Commerce Gateway — merchant enablement, safe buyer experience and trusted transaction authority — is the project.**
