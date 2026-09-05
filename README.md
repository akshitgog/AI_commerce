# AI Commerce Gateway

## Make a merchant transactable by an AI buyer — end to end.

**AI Commerce Gateway** lets an AI buyer discover a merchant's products, create a trusted purchase proposal, obtain buyer approval, pass merchant policy, pay through Razorpay, verify the payment, and produce a complete audit trail.

> **Every money action is explainable, bounded, and gated.**

The AI can understand intent and call narrow commerce tools.

**It cannot control price, approve itself, bypass merchant policy, call Razorpay directly, or declare a payment successful.**

[Live Demo](https://ai-commerce-zeta.vercel.app) · [Buyer Experience](https://ai-commerce-zeta.vercel.app/buyer) · [Merchant Catalog](https://ai-commerce-zeta.vercel.app/merchant/ai-catalog)

---

# The Problem

Making an AI recommend a product is easy.

Making a merchant safely **transactable by an AI buyer** is much harder.

Consider:

> **“Find me a USB-C charger under ₹1,000 and buy one.”**

An AI can understand that request.

But who decides:

* the real product price?
* whether the buyer actually approved ₹899?
* whether the merchant accepts the transaction?
* whether the same AI retry creates another payment?
* whether Razorpay actually received or completed the payment?
* what happens if the network dies after the payment request is sent?
* who caused each financial state change?

That is what AI Commerce Gateway solves.

---

# End-to-End AI Purchase

```text
Buyer
  │
  │ "Find me a charger under ₹1,000 and buy one"
  ▼
Reference AI Buyer
  │
  │ search_catalog
  ▼
Merchant's Published Catalog
  │
  ▼
AI selects a matching product
  │
  │ create_purchase_proposal
  ▼
Server-Derived Purchase Proposal
  │
  │ ₹899 calculated from trusted catalog
  ▼
Buyer Authorization
  │
  ▼
Merchant Policy
  │
  ├── allowed automatically
  ├── requires merchant review
  └── denied
  │
  ▼
READY
  │
  ▼
Trusted Transaction Authority
  │
  ├── revalidates proposal
  ├── revalidates price/version/stock
  ├── verifies buyer authorization
  ├── verifies merchant acceptance
  └── enforces idempotency
  │
  ▼
Razorpay
  │
  ▼
Payment Verification
  │
  ▼
SUCCEEDED
```

The important part is that the **LLM is never the transaction authority**.

---

# 1. Bounded

The AI receives only narrow commerce tools.

```text
search_catalog
get_product
create_purchase_proposal
request_authorization
execute_transaction
get_transaction_status
get_transaction_audit
```

It does **not** receive tools such as:

```text
charge_card(amount)
set_transaction_state(SUCCEEDED)
approve_purchase()
override_merchant_policy()
```

Trusted financial decisions remain in deterministic backend services.

### AI can

* understand buyer intent
* search products
* explain results
* create a proposal request
* request authorization
* request transaction execution
* read safe transaction status
* read the audit trail

### AI cannot

* set authoritative price
* set authoritative total
* approve its own purchase
* accept on behalf of the merchant
* mutate transaction state directly
* call Razorpay directly
* access payment credentials
* mark payment successful

---

# 2. Gated

A purchase cannot move directly from:

```text
"I want this"
```

to:

```text
charge ₹899
```

There are independent gates.

```text
                Purchase Proposal
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
      Buyer Authorization   Merchant Acceptance
                                │
                       ┌────────┼────────┐
                       ▼        ▼        ▼
                     AUTO     REVIEW    DENY
                       │        │
                       └───┬────┘
                           ▼
                          READY
```

## Gate 1 — Buyer authorization

The buyer must approve the exact proposed purchase.

The AI **cannot authorize itself**.

## Gate 2 — Merchant acceptance

The merchant defines how transactions are accepted.

For example:

```text
AUTO_BELOW_LIMIT
max amount = ₹1,000
```

A ₹899 transaction may proceed automatically.

A ₹1,499 transaction can instead enter:

```text
MERCHANT_REVIEW_REQUIRED
```

The buyer's approval does not replace merchant approval.

Merchant policy does not replace buyer consent.

---

# 3. Explainable

Every consequential action produces a structured transaction event.

We don't use the AI chat transcript as the financial audit log.

Example:

```text
Actor: BUYER
Action: AUTHORIZATION_APPROVED
Reason: Buyer confirmed purchase proposal
Previous State: BUYER_AUTH_REQUIRED
New State: MERCHANT_POLICY_PENDING
Correlation ID: cor_...
Timestamp: ...
```

Later:

```text
Actor: SYSTEM
Action: MERCHANT_POLICY_ALLOWED
Reason: Amount ₹899 <= merchant auto-approval limit ₹1,000
Previous State: MERCHANT_POLICY_PENDING
New State: READY
Correlation ID: cor_...
```

And during payment:

```text
Actor: RAZORPAY_VERIFIER
Action: PAYMENT_VERIFIED
Reason: Provider payment evidence successfully verified
Previous State: VERIFYING
New State: SUCCEEDED
Provider Reference: redacted
Correlation ID: cor_...
```

This gives us a **causal audit trail**, not simply:

> “AI says the payment worked.”

---

# Trusted Purchase Proposal

The AI never supplies the trusted transaction total.

The backend creates an immutable commercial snapshot:

```text
PurchaseProposal
├── merchant
├── product
├── product version
├── quantity
├── trusted unit amount
├── trusted total amount
├── currency
├── expiry
└── proposal hash
```

For example:

```text
Merchant catalog price: ₹899
Quantity: 1

Trusted backend total:
89900 minor units
INR
```

If an AI attempts to send:

```json
{
  "product_id": "charger_65w",
  "quantity": 1,
  "total": 100
}
```

the client-supplied total does not become financial authority.

The transaction amount is derived from trusted merchant state.

---

# Payment Safety

Creating a Razorpay order is **not payment success**.

Our transaction lifecycle separates execution from verification.

```text
READY
  │
  ▼
EXECUTING
  │
  ▼
PAYMENT_PENDING
  │
  ▼
VERIFYING
  │
  ├── verified ─────► SUCCEEDED
  │
  └── rejected ─────► FAILED
```

`SUCCEEDED` requires verified provider truth.

The AI cannot force that state.

The frontend cannot force that state.

Razorpay order creation alone cannot force that state.

---

# Graceful Failure — Unknown Payment Outcome

This is the failure case we intentionally handle.

Imagine:

```text
Transaction Authority
       │
       │ create Razorpay order
       ▼
    Razorpay
       │
       │ order actually created
       ▼

       X

Network response is lost
```

The dangerous solution would be:

```text
"Request timed out. Try payment again."
```

That could create a duplicate provider operation.

AI Commerce Gateway does **not** blindly retry.

Instead:

```text
EXECUTING
    │
    │ provider response lost
    ▼
 UNKNOWN
    │
    ▼
RECONCILING
    │
    │ lookup provider truth
    ▼
 Razorpay
    │
    ├── operation exists
    │       │
    │       ▼
    │  PAYMENT_PENDING / VERIFYING
    │
    └── operation failed/not found
            │
            ▼
       safe final resolution
```

The system asks Razorpay what actually happened before deciding what to do next.

This protects the transaction from duplicate financial effects.

---

# Idempotency

AI agents retry.

Networks retry.

Users double-click.

Payment systems therefore cannot treat every repeated request as a new transaction.

Mutating operations use trusted idempotency metadata.

```text
First execution
Idempotency-Key: idem_abc123
        │
        ▼
Provider operation created


Retry
Idempotency-Key: idem_abc123
        │
        ▼
Same logical operation returned
```

The LLM does not decide whether two payment attempts are financially equivalent.

Idempotency is enforced by the trusted backend.

---

# Agent-Readable Merchant

The merchant controls the authoritative catalog:

```text
Product
├── name
├── description
├── price
├── currency
├── stock
├── version
├── publication state
└── images
```

AI can assist with descriptive metadata.

But AI-generated metadata cannot modify authoritative:

```text
price
currency
stock
publication state
```

Once published, the merchant becomes discoverable by AI buyers through structured commerce operations.

---

# MCP — The Same Merchant Can Work With Other AI Clients

The built-in Reference Buyer Chat is our primary end-to-end demo.

But the commerce engine is **not tied to our chatbot**.

We also implemented Model Context Protocol adapters for buyer and merchant operations.

```text
             Reference Buyer Chat
                     │
                     ▼
                Buyer Adapter
                     │
                     │
                     ▼
             Trusted Backend
                     ▲
                     │
                     │
                 MCP Adapter
                     ▲
                     │
             External AI Client
```

An MCP-compatible AI can use the same commerce capabilities without bypassing the trusted transaction boundary.

## Buyer MCP

External AI clients can use controlled buyer capabilities such as:

```text
search_catalog
get_product
create_purchase_proposal
request_authorization
execute_transaction
get_transaction_status
get_transaction_audit
```

## Merchant MCP

Authorized merchant AI clients can perform controlled store-management actions, including product draft operations.

Mutation tools use safeguards such as:

* expected-version checks
* role validation
* idempotency keys
* confirmation requirements for sensitive operations

For high-impact actions such as publication, authority cannot simply be invented by the AI.

MCP is therefore an **interoperability layer**, not a payment engine.

---

# Trust Architecture

```text
┌───────────────────────┐
│        BUYER          │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  Reference AI Buyer   │
│                       │
│  UNTRUSTED FOR MONEY  │
└───────────┬───────────┘
            │
            │ Narrow typed tools
            ▼
┌─────────────────────────────┐
│       Buyer Adapter         │
└──────────────┬──────────────┘
               │
               ▼
┌───────────────────────────────────────────┐
│          TRUSTED APPLICATION LAYER        │
│                                           │
│ Catalog                                   │
│ Purchase Proposals                        │
│ Buyer Authorization                       │
│ Merchant Policy                           │
│ Transaction State Machine                 │
│ Idempotency                               │
│ Audit                                     │
└────────────────────┬──────────────────────┘
                     │
                     ▼
             Transaction Authority
                     │
                     ▼
               Razorpay Adapter
                     │
                     ▼
              Razorpay Test Mode
                     │
                     ▼
          Verification / Reconciliation
```

---

# What We Demonstrate

### Happy path

```text
Merchant publishes ₹899 charger
        ↓
Buyer asks AI for charger under ₹1,000
        ↓
AI searches merchant catalog
        ↓
Backend creates ₹899 proposal
        ↓
Buyer explicitly approves
        ↓
Merchant AUTO_BELOW_LIMIT policy accepts
        ↓
Transaction becomes READY
        ↓
Trusted backend executes Razorpay flow
        ↓
Provider evidence verified
        ↓
SUCCEEDED
        ↓
Complete audit trail
```

### Safety proof

We also demonstrate:

```text
same execute request
        ↓
idempotency protection
        ↓
no duplicate logical payment execution
```

### Failure proof

```text
provider request dispatched
        ↓
response lost
        ↓
UNKNOWN
        ↓
RECONCILING
        ↓
provider lookup
        ↓
safe recovery
```

### Interoperability proof

```text
External MCP-capable AI
        ↓
search_catalog
        ↓
same merchant catalog
        ↓
same trusted backend
        ↓
same financial boundaries
```

---

# Tech Stack

**Frontend**

* Next.js
* React
* TypeScript
* Tailwind CSS
* shadcn/ui

**Backend**

* Python
* FastAPI
* SQLAlchemy
* Alembic
* Pydantic

**AI**

* Fireworks AI
* OpenAI-compatible tool calling

**Agent Interoperability**

* Model Context Protocol
* Buyer MCP adapter
* Merchant MCP adapter

**Payments**

* Razorpay Orders
* Checkout verification
* Webhook/signature verification
* Provider lookup/reconciliation

**Infrastructure**

* PostgreSQL
* Supabase Storage
* Vercel
* Render

---

# Live Demo

### AI Buyer

[Try the Buyer Experience](https://ai-commerce-zeta.vercel.app/buyer)

Example:

> **Find me a USB-C charger under ₹1,000 and buy one.**

### Merchant

[Open the Merchant Catalog](https://ai-commerce-zeta.vercel.app/merchant/ai-catalog)

### Application

[Open AI Commerce Gateway](https://ai-commerce-zeta.vercel.app)

### API

[Health Check](https://ai-commerce-zeta.vercel.app/api/health/live)

---

# Why This Is Agentic Commerce

This project is not about connecting an LLM to a `charge()` function.

It is about making a real merchant **transactable by AI buyers** while preserving the controls normally expected from financial infrastructure.

```text
AI understands intent
        ↓
Backend owns truth
        ↓
Buyer grants consent
        ↓
Merchant grants acceptance
        ↓
Transaction authority controls execution
        ↓
Razorpay moves money
        ↓
Provider truth determines success
        ↓
Audit explains what happened
```

## AI can orchestrate commerce.

## It cannot become the financial authority.

That is the core of **AI Commerce Gateway**.
