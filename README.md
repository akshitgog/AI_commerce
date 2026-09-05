# AI Commerce Gateway

## Making a Razorpay merchant transactable by an AI buyer — end to end.

**AI Commerce Gateway** is an agentic commerce infrastructure layer that allows AI buyers to discover a merchant's products, create a purchase proposal, obtain authorization, satisfy merchant policy, execute payment through Razorpay, verify the result, and produce a complete audit trail.

The key idea is simple:

> **Any AI can orchestrate commerce. The AI never becomes the financial authority.**

[Live App](https://ai-commerce-zeta.vercel.app) · [Buyer Experience](https://ai-commerce-zeta.vercel.app/buyer) · [Merchant AI Catalog](https://ai-commerce-zeta.vercel.app/merchant/ai-catalog) · [API Health](https://ai-commerce-zeta.vercel.app/api/health/live)

---

## The Problem

AI agents are becoming capable of searching, reasoning and calling tools.

But making a merchant actually **transactable by an AI buyer** requires much more than giving an LLM a payment API.

A real agentic purchase must answer:

* How does an AI discover a merchant's products?
* Where does the trusted price come from?
* How does the buyer approve the exact purchase?
* Can the merchant automatically accept or manually review it?
* How do we stop the AI from changing financial state?
* How are duplicate payment attempts prevented?
* What happens when a payment request times out after being sent?
* How do we verify whether money actually moved?
* Can external AI agents transact through the same system?
* Can every money-related action be explained afterwards?

**AI Commerce Gateway is our answer to that problem.**

---

# End-to-End Agentic Commerce

A buyer can simply say:

> **“Find me a USB-C charger under ₹1,000 and buy one.”**

The request becomes a controlled transaction:

```text
Buyer
  │
  ▼
AI Buyer
  │
  │ search_catalog
  ▼
Agent-Readable Merchant Catalog
  │
  ▼
Immutable Purchase Proposal
  │
  │ server derives trusted price
  ▼
Buyer Authorization
  │
  ▼
Merchant Policy / Manual Review
  │
  ▼
Transaction Authority
  │
  │ revalidates commercial + authorization state
  ▼
Razorpay
  │
  ▼
Payment Verification
  │
  ├── verified ──────────────► SUCCEEDED
  │
  └── uncertain ─────────────► UNKNOWN
                                  │
                                  ▼
                             RECONCILING
                                  │
                                  ▼
                           Provider Lookup
                                  │
                                  ▼
                             Final State

Every consequential action
            │
            ▼
      Structured Audit Trail
```

The AI participates throughout the buying experience without receiving unrestricted control over money.

---

# 1. Make the Merchant Agent-Readable

The merchant creates and publishes products through the merchant experience.

The backend maintains authoritative:

```text
Product
├── product ID
├── name
├── description
├── price
├── currency
├── stock
├── publication state
├── version
└── images
```

AI can assist merchants with descriptive catalog metadata, but it cannot become authoritative for price, currency, stock or publication state.

The published catalog can then be consumed by the reference AI buyer or compatible external AI clients.

---

# 2. AI Buyer

The Reference Buyer Chat provides the primary end-to-end experience.

Instead of navigating a traditional storefront, a buyer can express intent naturally:

```text
"Find me a charger under ₹1,000."

"Show me the best match."

"Buy one."
```

The LLM translates that intent into a small set of typed commerce operations.

Examples include:

```text
search_catalog
get_product
create_purchase_proposal
request_authorization
execute_transaction
get_transaction_status
get_transaction_audit
```

These are intentionally narrow tools.

The AI can **discover, explain, propose and orchestrate**.

It cannot independently authorize or settle a transaction.

---

# 3. Trusted Purchase Proposal

The AI never decides the authoritative transaction amount.

When a purchase is proposed, the backend creates a server-derived commercial snapshot:

```text
PurchaseProposal
├── merchant
├── product
├── product version
├── quantity
├── trusted unit amount
├── trusted total
├── currency
├── expiry
└── proposal identity/hash
```

This means an AI cannot turn:

```text
₹899 product
```

into:

```text
₹1 transaction
```

by supplying a manipulated price.

Trusted commercial values come from the merchant-controlled backend.

---

# 4. Buyer Authorization + Merchant Acceptance

A transaction requires independent authority.

```text
                 Purchase Proposal
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
       Buyer Authorization   Merchant Policy
                                  │
                           ┌──────┼──────┐
                           ▼      ▼      ▼
                         AUTO   REVIEW  DENY
                           │      │
                           └──┬───┘
                              ▼
                            READY
```

The AI cannot approve itself.

Merchant acceptance cannot replace buyer consent.

Merchant policies can automatically accept eligible transactions or send exceptions to a human review queue.

Only after the required gates are satisfied can execution proceed.

---

# 5. Transaction Authority

The most important component is the trusted **Transaction Authority**.

```text
AI / MCP
    │
    ▼
Buyer Adapter
    │
    ▼
Application Services
    │
    ▼
Transaction Authority
    │
    ├── validates proposal
    ├── validates buyer authorization
    ├── validates merchant decision
    ├── revalidates trusted commercial state
    ├── enforces transaction lifecycle
    ├── enforces idempotency
    └── records causal events
              │
              ▼
        Razorpay Adapter
```

Neither the LLM nor MCP can directly call Razorpay.

The backend remains the financial authority.

---

# 6. Razorpay Payment Execution

Razorpay is integrated behind the trusted transaction boundary.

A provider order being created is **not** treated as payment success.

The system verifies provider evidence before recording a successful transaction.

```text
READY
  │
  ▼
EXECUTING
  │
  ├──────────────► UNKNOWN
  │                    │
  ▼                    ▼
PAYMENT_PENDING    RECONCILING
  │                    │
  ▼                    │
VERIFYING ◄─────────────┘
  │
  ├────────► SUCCEEDED
  │
  └────────► FAILED
```

This prevents an AI, frontend response or provider-order creation from incorrectly declaring that money moved.

---

# 7. Idempotency & Duplicate Payment Protection

Agentic systems naturally retry tool calls.

That makes idempotency especially important.

Mutating commerce operations are protected by trusted idempotency semantics so retries of the same logical operation cannot silently become multiple physical payment attempts.

The AI does not control the financial idempotency mechanism.

This is particularly important when an agent, network or payment provider retries after a timeout.

---

# 8. Graceful Recovery from Unknown Outcomes

One of the hardest payment cases is:

```text
Request sent to provider
        │
        ▼
Provider may have processed it
        │
        X
Application loses response
```

Blind retrying is dangerous because another payment/order may be created.

AI Commerce Gateway therefore models uncertainty explicitly:

```text
EXECUTING
    │
    ▼
 UNKNOWN
    │
    ▼
RECONCILING
    │
    ▼
Provider Lookup
    │
    ├── payment exists ──► continue verification
    │
    └── failed/not found ─► safe resolution
```

The system asks the provider for truth rather than allowing the AI to guess.

---

# 9. Structured Financial Audit Trail

A chat transcript is not an audit log.

Every consequential transaction action creates structured causal evidence containing information such as:

```text
Actor
Action
Reason
Previous State
New State
Correlation ID
Timestamp
Redacted Provider Reference
Metadata
```

This makes it possible to answer:

> Who caused this transaction to move?

> Why was it approved?

> Did the buyer authorize it?

> Did merchant policy accept it?

> What did Razorpay report?

> How was an uncertain outcome recovered?

The transaction can therefore be reconstructed independently of the AI conversation.

---

# 10. Native MCP — Any Compatible AI Can Use the Same Commerce Engine

The public demo uses our Reference Buyer Chat, but the commerce engine is not tied to that interface.

We built native **Model Context Protocol (MCP)** adapters for both buyer and merchant experiences.

```text
Reference Buyer Chat
        │
        ▼
   Buyer Adapter
        │
        ┐
        │
        ▼
Trusted Commerce Services
        ▲
        │
        ┘
External MCP AI
        │
        ▼
    MCP Adapter
```

The same backend remains authoritative regardless of which AI is connected.

### Buyer MCP

Compatible external AI clients can access narrow buyer operations such as catalog discovery, controlled proposal creation, transaction status and audit operations without receiving direct payment authority.

### Merchant MCP

The Merchant MCP toolkit allows an authorized external AI to assist with store-management operations.

For example, merchant tools can support operations such as:

```text
/update
```

for safely modifying product drafts.

Updates use expected-version locking so an AI cannot silently overwrite newer merchant changes.

---

# 11. Human Authority Cannot Be Bypassed Through MCP

MCP is an interoperability layer — **not a trust bypass**.

High-impact operations remain gated.

For example, sensitive operations such as publishing a product require a trusted `confirmation_token` generated outside the AI's ordinary tool context.

Therefore:

```text
External AI
     │
     │ publish_product
     ▼
Confirmation required
     │
     X  AI cannot manufacture authority
     │
     ▼
Trusted Backend
```

An external AI cannot gain additional financial or merchant authority simply because it connects through MCP.

---

# 12. MCP Idempotency and Safety

Mutating MCP operations enforce transport-level idempotency keys.

The MCP adapter translates untrusted AI intent into typed backend commands while the application layer retains authority.

The MCP boundary is designed to prevent:

* bypassing role-based access controls;
* manipulating transaction state directly;
* overriding trusted prices;
* bypassing buyer consent;
* bypassing merchant authority;
* directly invoking payment providers.

The MCP buyer and merchant adapters are covered by dedicated test suites, including:

```text
test_buyer_mcp.py
test_merchant_mcp.py
```

The public deployment currently demonstrates the Reference Buyer Chat, while the MCP implementation is maintained and tested in the codebase as the interoperability path for compatible external AI clients.

---

# Architecture

```text
                        ┌──────────────────────┐
                        │       Merchant       │
                        └──────────┬───────────┘
                                   │
                                   ▼
                         Merchant Dashboard
                                   │
                                   ▼
                         Agent-Readable Catalog
                                   │
             ┌─────────────────────┴─────────────────────┐
             │                                           │
             ▼                                           ▼
    Reference Buyer Chat                         External AI Client
             │                                           │
             ▼                                           ▼
       Buyer Adapter                                MCP Adapter
             │                                           │
             └─────────────────────┬─────────────────────┘
                                   ▼
                        Application Services
                                   │
                 ┌─────────────────┼─────────────────┐
                 ▼                 ▼                 ▼
              Catalog          Authorization     Merchant Policy
                 │                 │                 │
                 └─────────────────┼─────────────────┘
                                   ▼
                         Transaction Authority
                                   │
                     ┌─────────────┼─────────────┐
                     ▼             ▼             ▼
                Idempotency     Audit Log     Recovery
                                   │
                                   ▼
                            Razorpay Adapter
                                   │
                                   ▼
                         Razorpay Test Mode
                                   │
                                   ▼
                         Verification / Lookup
```

---

# Trust Boundaries

| AI can                          | AI cannot                         |
| ------------------------------- | --------------------------------- |
| Understand buyer intent         | Set authoritative price           |
| Search catalog                  | Approve its own purchase          |
| Explain products                | Override buyer consent            |
| Create controlled proposals     | Override merchant policy          |
| Request authorization           | Directly change transaction state |
| Request transaction execution   | Call Razorpay directly            |
| Read safe transaction status    | Declare payment successful        |
| Read redacted audit information | Access provider credentials       |
| Use MCP commerce tools          | Bypass human confirmation         |

This boundary is the core of the project.

---

# Tech Stack

### Frontend

* Next.js 16
* React 19
* TypeScript
* Tailwind CSS
* shadcn/ui

### Backend

* Python 3.12+
* FastAPI
* SQLAlchemy
* Alembic
* Pydantic

### AI

* Fireworks AI
* OpenAI-compatible inference API

### Agent Interoperability

* Model Context Protocol
* Buyer MCP adapter
* Merchant MCP adapter
* Typed commerce tools

### Payments

* Razorpay
* Orders
* Checkout
* Signature verification
* Webhook verification
* Provider reconciliation

### Data / Storage

* PostgreSQL
* Supabase Storage

### Deployment

* Vercel — frontend
* Render — backend

---

# Live Demo

### Buyer

[Open Buyer Experience](https://ai-commerce-zeta.vercel.app/buyer)

Try:

> **“Find me a USB-C charger under ₹1,000.”**

Then follow the proposal → authorization → merchant policy → Razorpay payment → verification flow.

### Merchant

[Open Merchant AI Catalog](https://ai-commerce-zeta.vercel.app/merchant/ai-catalog)

The merchant can manage products, control commercial data and participate in governed AI commerce.

### API

[Check API Health](https://ai-commerce-zeta.vercel.app/api/health/live)

---

# Why This Matters

The interesting problem in agentic commerce is not:

> **Can an LLM call a checkout API?**

It can.

The harder problem is:

> **How can a merchant become transactable by AI buyers without making the AI the financial authority?**

AI Commerce Gateway demonstrates one answer:

```text
Agent-readable merchant
        +
Natural-language buyer
        +
Explicit buyer consent
        +
Merchant-controlled acceptance
        +
Trusted transaction authority
        +
Razorpay execution
        +
Provider verification
        +
Idempotency & recovery
        +
Structured audit trail
        +
MCP interoperability
```

## The result

**A merchant that can be discovered and transacted with by AI buyers end to end, while every money action remains bounded, gated, explainable and auditable.**
