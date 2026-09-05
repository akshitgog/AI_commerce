# AI Commerce Gateway

## From AI-assisted catalog creation to AI-powered checkout — make a Razorpay merchant transactable end to end.

**AI Commerce Gateway** helps a merchant become ready for agentic commerce in two steps:

1. **AI Catalog Assistant** helps the merchant create and enrich an agent-readable product catalog.
2. **AI Buyer** discovers those products, creates a trusted proposal, gets the required approvals, pays through Razorpay, and receives a verified result.

> **Every money action is explainable, bounded and gated.**

The AI can help both sides of commerce.

It can help a merchant build a better catalog and help a buyer find the right product — but it cannot manufacture price, consent, merchant approval, provider truth or payment success.

[Live App](https://ai-commerce-zeta.vercel.app) · [Buyer Experience](https://ai-commerce-zeta.vercel.app/buyer) · [AI Catalog](https://ai-commerce-zeta.vercel.app/merchant/ai-catalog)

---

# The Problem

Agentic commerce has two sides.

### Merchant problem

Most merchants do not have catalogs designed for AI agents.

Product information may be incomplete, inconsistent or difficult for an AI buyer to understand.

### Buyer problem

Even if an AI can discover a product, giving it unrestricted control over checkout and payments is unsafe.

So the real problem is not simply:

> “Can AI recommend a product?”

It is:

> **Can AI help a normal merchant become agent-ready, and can another AI safely transact with that merchant end to end?**

AI Commerce Gateway solves both.

---

# 1. AI-Assisted Merchant Catalog

The commerce journey begins with the merchant.

Instead of requiring the merchant to manually prepare every piece of structured product information, the **AI Catalog Assistant** helps create and enrich product listings.

A merchant can provide basic product information and use AI to assist with fields such as:

```text id="kt0z84"
Product Name
Description
Category
Attributes
Search-friendly metadata
Tags
Buyer-facing explanation
```

This makes the catalog easier for AI buyers to discover and understand.

### Example

A merchant starts with:

```text id="j3fcqa"
65W USB-C Charger
₹899
10 units
```

The AI assistant can help turn it into richer structured information:

```text id="8l46v4"
Name:
65W USB-C Fast Charger

Description:
Compact USB-C charger suitable for phones,
tablets and compatible laptops.

Category:
Electronics > Chargers

Attributes:
- 65W
- USB-C
- Fast charging
- Compact design

Search terms:
charger, USB-C, laptop charger, phone charger
```

The merchant reviews the generated information before using it.

---

# AI Helps With Metadata — Not Financial Authority

The AI Catalog Assistant is deliberately limited.

### AI may suggest

* product names
* descriptions
* categories
* attributes
* tags
* search metadata

### AI cannot control

* authoritative price
* currency
* stock
* merchant identity
* publication authority
* financial policy
* transaction state

These values remain controlled by trusted backend records and the merchant.

```text id="kcepgx"
AI-generated metadata
        │
        ▼
Merchant review
        │
        ▼
Trusted Product Record
        │
        ├── price       ← merchant/backend
        ├── currency    ← merchant/backend
        ├── stock       ← merchant/backend
        ├── version     ← backend
        └── publication ← governed action
```

This prevents prompt injection or AI mistakes from changing commercial truth.

---

# 2. Make the Catalog Agent-Readable

Once the merchant publishes the product, it becomes available through structured commerce operations.

```text id="o900la"
Merchant
   │
   ▼
AI Catalog Assistant
   │
   ▼
Structured Product Draft
   │
   ▼
Merchant Review
   │
   ▼
Published Agent-Readable Catalog
```

That same catalog can then be consumed by:

* our Reference AI Buyer
* external MCP-compatible AI clients

The merchant does not need to rebuild commerce logic for every AI platform.

---

# 3. AI Buyer

A buyer can use natural language:

> **“Find me a USB-C charger under ₹1,000 and buy one.”**

The AI interprets the request and calls narrow commerce operations such as:

```text id="eckwmv"
search_catalog
get_product
create_purchase_proposal
request_authorization
execute_transaction
get_transaction_status
get_transaction_audit
```

The AI can discover and explain.

It cannot directly move money.

---

# End-to-End Commerce Flow

```text id="i8dupt"
MERCHANT SIDE

Merchant
   │
   ▼
AI Catalog Assistant
   │
   ▼
Structured Product
   │
   ▼
Merchant Review / Publish
   │
   ▼
Agent-Readable Catalog


BUYER SIDE

Buyer
   │
   │ "Find me a charger under ₹1,000"
   ▼
AI Buyer
   │
   ▼
Catalog Search
   │
   ▼
Matching Product
   │
   ▼
Trusted Purchase Proposal
   │
   ▼
Buyer Authorization
   │
   ▼
Merchant Policy / Review
   │
   ▼
READY
   │
   ▼
Transaction Authority
   │
   ▼
Razorpay
   │
   ▼
Provider Verification
   │
   ├────────► SUCCEEDED
   │
   └────────► UNKNOWN → RECONCILING
                         │
                         ▼
                    Provider Truth
```

This is the complete journey:

> **AI helps create the storefront, another AI discovers it, and the trusted commerce engine safely completes the purchase.**

---

# 4. Every Money Action Is Bounded

The AI never receives unrestricted financial capabilities.

### AI can

* create descriptive catalog metadata
* search products
* compare products
* explain recommendations
* request a purchase proposal
* request authorization
* request execution
* read transaction status
* read safe audit information

### AI cannot

* create authoritative prices
* change stock through buyer tools
* impersonate another merchant or buyer
* authorize itself
* override merchant policy
* directly mutate transaction state
* call Razorpay directly
* declare a payment successful

---

# 5. Every Money Action Is Gated

Before payment execution:

```text id="3lpqq5"
Authenticated Actor
        ↓
Immutable Proposal
        ↓
Server-Derived Total
        ↓
Buyer Authorization
        ↓
Merchant Acceptance
        ↓
Price / Version / Stock Revalidation
        ↓
Durable Idempotency
        ↓
Valid State Transition
        ↓
Razorpay
        ↓
Verified Provider Truth
```

There are two independent financial gates.

## Buyer gate

The buyer authorizes the exact proposal.

The AI may request that authorization.

**It cannot grant it.**

## Merchant gate

Merchant policy can:

```text id="d0kneq"
AUTO ALLOW
REQUIRE REVIEW
DENY
```

Merchant approval cannot replace buyer consent.

---

# 6. Trusted Purchase Proposal

Trusted money comes from the backend.

```text id="o1gqas"
PurchaseProposal
├── merchant
├── product
├── product version
├── quantity
├── trusted unit amount
├── trusted total
├── currency
├── expiry
└── proposal hash
```

Example:

```text id="y6g7xg"
Merchant price = ₹899
Quantity = 1

Trusted backend:
89900 minor units
INR
```

An LLM cannot simply send:

```text id="pobsx5"
price = ₹1
```

and make that the transaction amount.

---

# 7. Every Money Action Is Explainable

We do not use the AI conversation itself as the financial audit log.

Important actions create structured causal events.

Example:

```text id="dbxl2x"
Actor: BUYER
Action: AUTHORIZATION_APPROVED
Previous State: BUYER_AUTH_REQUIRED
New State: MERCHANT_POLICY_PENDING
Reason: Buyer approved proposal
Correlation ID: ...
Timestamp: ...
```

Merchant decision:

```text id="viuuvj"
Actor: SYSTEM
Action: MERCHANT_POLICY_ALLOWED
Previous State: MERCHANT_POLICY_PENDING
New State: READY
Reason: ₹899 <= merchant auto-approval limit ₹1,000
```

Payment result:

```text id="hm933c"
Actor: PROVIDER_VERIFIER
Action: PAYMENT_VERIFIED
Previous State: VERIFYING
New State: SUCCEEDED
Provider Reference: redacted
```

The audit trail answers:

* who acted?
* what changed?
* why did it change?
* what did the buyer approve?
* what did the merchant allow?
* what did Razorpay confirm?

---

# 8. Razorpay Behind the Transaction Authority

Neither the AI Buyer nor MCP can call Razorpay directly.

```text id="18jtj8"
AI
 │
 ▼
Typed Tools
 │
 ▼
Application Services
 │
 ▼
Transaction Authority
 │
 ▼
Razorpay Adapter
 │
 ▼
Razorpay Test Mode
```

A Razorpay order being created does **not** mean payment succeeded.

```text id="puid73"
READY
  ↓
EXECUTING
  ↓
PAYMENT_PENDING
  ↓
VERIFYING
  │
  ├── verified → SUCCEEDED
  └── rejected → FAILED
```

Only verified provider truth can create final success.

---

# 9. Graceful Failure Handling

We intentionally handle the dangerous case where the provider may have processed a request but our application loses the response.

```text id="wg8pgs"
Backend
   │
   │ request dispatched
   ▼
Razorpay
   │
   │ operation may succeed
   ▼
   X
Network response lost
```

Blindly retrying could create a duplicate provider operation.

Instead:

```text id="pzdol7"
EXECUTING
    ↓
UNKNOWN
    ↓
RECONCILING
    ↓
Query Razorpay
    ↓
Recover provider truth
```

A transaction with an unknown provider outcome blocks a blind new execution attempt until reconciliation.

The system does not let the AI guess what happened.

---

# 10. Idempotency

Agentic systems naturally retry tool calls.

Therefore financial mutations use trusted idempotency metadata.

```text id="ayk1ah"
Request #1
Idempotency-Key: abc123
        ↓
Operation executed


Retry
Idempotency-Key: abc123
        ↓
Same logical result
```

If the same key is reused with different inputs, the request is rejected.

The AI does not decide financial equivalence.

The backend does.

---

# 11. MCP — AI-Agnostic Commerce

The Reference Buyer Chat is our main public experience.

But the commerce engine is not tied to our interface.

We implemented native Model Context Protocol adapters for both:

* Buyer AI clients
* Merchant AI clients

```text id="gln8y1"
Reference AI Buyer ──────┐
                         │
                         ▼
                  Trusted Services
                         ▲
                         │
External AI via MCP ─────┘
```

## Buyer MCP

External compatible AI clients can discover products, create controlled proposals and inspect transaction status through the same governed backend.

## Merchant MCP

Merchant AI clients can assist with catalog management.

Capabilities include controlled draft-update workflows using:

* merchant-bound identity
* role checks
* expected-version locking
* idempotency
* human confirmation for sensitive publication operations

---

# 12. Merchant Publication Remains Human-Controlled

AI can help create and modify product drafts.

It cannot silently publish them.

Publishing or unpublishing requires explicit trusted confirmation generated outside the AI's normal context.

That confirmation is bound to information such as:

```text id="7sphd5"
merchant
merchant user
product
product version
action
expiry
unique token
```

This means an external AI can help operate the catalog without silently making products publicly transactable.

---

# Architecture

```text id="29f0b5"
                       MERCHANT
                          │
                          ▼
                 AI Catalog Assistant
                          │
                          ▼
                   Product Drafts
                          │
                  Human / Policy Gate
                          │
                          ▼
               Agent-Readable Catalog
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
     Reference AI Buyer         External AI / MCP
             │                         │
             └────────────┬────────────┘
                          ▼
                   Buyer Adapter
                          │
                          ▼
                Application Services
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
      Catalog      Buyer Authorization   Merchant Policy
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
                 Transaction Authority
                          │
               ┌──────────┼──────────┐
               ▼          ▼          ▼
          Idempotency   Audit     Recovery
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

## 1. AI-assisted merchant onboarding

```text id="z980o6"
Merchant enters basic product
        ↓
AI enriches product metadata
        ↓
Merchant reviews it
        ↓
Product is published
        ↓
Merchant becomes agent-readable
```

## 2. AI buyer purchase

```text id="x1zos9"
Buyer expresses intent
        ↓
AI discovers product
        ↓
Backend creates trusted proposal
        ↓
Buyer approves
        ↓
Merchant accepts
        ↓
Razorpay checkout
        ↓
Payment verified
```

## 3. Audit proof

```text id="7jgrn7"
Every financial state change
        ↓
actor + reason + transition + evidence
```

## 4. Duplicate protection

```text id="byclrd"
same logical request
        ↓
idempotency
        ↓
no duplicate logical execution
```

## 5. Graceful failure

```text id="legon6"
provider request sent
        ↓
response lost
        ↓
UNKNOWN
        ↓
RECONCILING
        ↓
provider truth
```

## 6. MCP interoperability

```text id="ph5g4g"
External AI
        ↓
same commerce tools
        ↓
same trusted backend
        ↓
same boundaries
```

---

# Testing & Validation

The backend test suite currently includes:

```text id="4z869l"
885 collected

879 passed
6 skipped
```

Coverage includes:

* transaction state machine
* financial money handling
* tenant isolation
* buyer authorization
* merchant policy
* idempotency and replay
* Razorpay adapter
* payment verification
* failure/recovery behavior
* audit events
* Buyer MCP
* Merchant MCP
* MCP interoperability

Dedicated MCP tests include:

```text id="7f59yp"
test_buyer_mcp.py
test_buyer_mcp_interop.py
test_merchant_mcp.py
```

Backend validation:

```powershell id="mfa511"
uv run pytest
uv run ruff check .
uv run mypy
```

Frontend validation:

```powershell id="3jf53x"
cd frontend
npm run lint
npm run build
```

---

# Tech Stack

**Frontend**

* Next.js 16
* React 19
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

**Agent interoperability**

* Model Context Protocol
* Buyer MCP
* Merchant MCP

**Payments**

* Razorpay Test Mode
* Orders
* Checkout
* Signature/Webhook verification
* Provider reconciliation

**Infrastructure**

* PostgreSQL
* Supabase Storage
* Vercel
* Render

---

# Live Demo

### AI Catalog Assistant

[Open Merchant AI Catalog](https://ai-commerce-zeta.vercel.app/merchant/ai-catalog)

Create or enrich a product and make it ready for AI discovery.

### AI Buyer

[Open Buyer Experience](https://ai-commerce-zeta.vercel.app/buyer)

Try:

> **“Find me a USB-C charger under ₹1,000 and buy one.”**

### Main Application

[Open AI Commerce Gateway](https://ai-commerce-zeta.vercel.app)

---

# Why This Matters

Agentic commerce needs more than an AI chatbot.

A merchant first needs to become **AI-readable**.

Then they need to become **AI-transactable**.

AI Commerce Gateway connects both:

```text id="5iimr1"
AI Catalog Assistant
        ↓
Agent-Readable Merchant
        ↓
AI Product Discovery
        ↓
Trusted Proposal
        ↓
Buyer Consent
        ↓
Merchant Acceptance
        ↓
Razorpay Payment
        ↓
Provider Verification
        ↓
Audit + Recovery
```

## The result

**AI helps a merchant create an agent-ready catalog, lets AI buyers discover and transact with that merchant end to end, and keeps every money action bounded, gated, explainable and auditable.**

> **AI can help build the storefront and orchestrate the purchase. The trusted backend remains the financial authority.**
