# AI Commerce Gateway

> An AI-native commerce gateway that makes merchants transactable by AI buyers while keeping every money action explainable, bounded, and gated.

AI Commerce Gateway is a full-stack agentic-commerce system designed around one principle:

> **AI may discover, reason, recommend, propose, and request actions — but trusted backend systems retain financial authority.**

The system combines:

* AI-powered buyer assistant
* AI-assisted merchant catalog creation
* Trusted AI-readable catalog
* Bounded buyer authorization
* Independent merchant policy enforcement
* Razorpay Test Mode payment execution
* Idempotent transaction handling
* Structured audit trails
* Graceful failure and reconciliation handling
* MCP interoperability for external AI clients

A representative buyer request is:

> “Find me a good 65W charger under ₹2,000 and buy one.”

The AI can discover products, compare them, select a suitable option, prepare a purchase proposal, and request transaction execution.

It cannot:

* authorize itself
* invent authoritative prices
* bypass merchant approval
* directly call Razorpay
* manipulate transaction state
* mark a payment successful

---

# Why AI Commerce Gateway?

Traditional e-commerce requires buyers to manually perform most of the journey:

```text
Search
  |
  v
Filter
  |
  v
Open Product
  |
  v
Compare
  |
  v
Add to Cart
  |
  v
Checkout
  |
  v
Track Payment
```

AI Commerce Gateway changes the interaction model:

```text
Buyer Intent
    |
    v
AI Discovery
    |
    v
AI Product Selection
    |
    v
Trusted Purchase Proposal
    |
    v
Bounded Buyer Authorization
    |
    v
Merchant Policy Gate
    |
    v
AI-Initiated Execution Request
    |
    v
Trusted Transaction Core
    |
    v
Razorpay Test Mode
    |
    v
Provider Verification
    |
    v
Final Transaction State
    |
    v
Structured Audit Trail
```

The buyer primarily provides:

1. Intent
2. Financial authorization when required

The AI handles the orchestration around those actions.

---

# Core Safety Principle

Every money action is designed to be:

## Explainable

The system records structured causal events showing:

* what was requested
* which product was selected
* authoritative amount and currency
* buyer authorization
* merchant decision
* execution request
* provider interaction
* payment verification
* final transaction state

## Bounded

Buyer authorization applies only to a defined purchase scope, such as:

* merchant
* product
* quantity
* amount
* currency
* proposal
* authorization lifetime

The AI cannot silently increase or alter those values.

## Gated

Provider execution is permitted only after trusted backend checks succeed.

These checks include:

* valid purchase proposal
* buyer authorization
* merchant policy or approval
* trusted catalog state
* valid transaction state
* idempotency protections

---

# System Architecture

```text
+--------------------------------------------------------------------------+
|                              USER LAYER                                  |
+--------------------------------------------------------------------------+

     +----------------------+                 +----------------------+
     |        Buyer         |                 |       Merchant       |
     | Browser / AI Client  |                 |       Browser        |
     +----------+-----------+                 +----------+-----------+
                |                                        |
                |                                        |
                v                                        v

+--------------------------------------------------------------------------+
|                         NEXT.JS FRONTEND                                  |
+--------------------------------------------------------------------------+

     +----------------------+                 +----------------------+
     | Reference Buyer Chat |                 | Merchant Dashboard   |
     |                      |                 |                      |
     | - Natural language   |                 | - AI product setup   |
     | - Recommendations    |                 | - Catalog            |
     | - Purchase approval  |                 | - Policies           |
     | - Status / audit     |                 | - Review queue       |
     +----------+-----------+                 +----------+-----------+
                |                                        |
                +--------------------+-------------------+
                                     |
                                     | REST / API Proxy
                                     v

+--------------------------------------------------------------------------+
|                         FASTAPI BACKEND                                   |
+--------------------------------------------------------------------------+
|                                                                          |
|   +----------------------+          +----------------------+              |
|   |    API Routers       |          |   Auth / Identity    |              |
|   |                      |          |                      |              |
|   | Buyer / Merchant API |<-------->| Trusted ActorContext |              |
|   +----------+-----------+          +----------------------+              |
|              |                                                           |
|              v                                                           |
|   +------------------------------------------------------------------+   |
|   |                    APPLICATION SERVICES                           |   |
|   |                                                                  |   |
|   |  - Catalog services                                              |   |
|   |  - BuyerAdapter                                                  |   |
|   |  - Proposal services                                             |   |
|   |  - Authorization services                                        |   |
|   |  - Merchant policy services                                      |   |
|   |  - Transaction orchestration                                     |   |
|   +-----------+----------------------+-------------------------------+   |
|               |                      |                                   |
|               |                      |                                   |
|               v                      v                                   |
|   +----------------------+   +----------------------+                     |
|   |     Merchant AI      |   |      Buyer AI        |                     |
|   |                      |   |                      |                     |
|   | Product extraction   |   | Intent reasoning     |                     |
|   | Metadata generation  |   | Catalog search       |                     |
|   | Draft preparation    |   | Product selection    |                     |
|   +----------+-----------+   | Tool orchestration   |                     |
|              |               +----------+-----------+                     |
|              |                          |                                 |
|              +------------+-------------+                                 |
|                           |                                               |
|                           v                                               |
|                    +--------------+                                       |
|                    | Fireworks AI |                                       |
|                    | / Qwen Model |                                       |
|                    +--------------+                                       |
|                                                                          |
|   +------------------------------------------------------------------+   |
|   |                       TRUSTED DOMAIN CORE                         |   |
|   |                                                                  |   |
|   |  +----------------+  +----------------+  +--------------------+  |   |
|   |  | Catalog Domain |  | Policy Engine  |  | Transaction Core   |  |   |
|   |  |                |  |                |  |                    |  |   |
|   |  | Products       |  | MANUAL_ALL     |  | State machine      |  |   |
|   |  | Price / stock  |  | AUTO_LIMIT     |  | Idempotency        |  |   |
|   |  | Publication    |  | DENY_ALL       |  | Recovery           |  |   |
|   |  +-------+--------+  +--------+-------+  +---------+----------+  |   |
|   |          |                    |                    |             |   |
|   |          +--------------------+--------------------+             |   |
|   |                               |                                  |   |
|   |                               v                                  |   |
|   |                      +------------------+                        |   |
|   |                      | Structured Audit |                        |   |
|   |                      | / Domain Events  |                        |   |
|   |                      +------------------+                        |   |
|   +------------------------------------------------------------------+   |
|                                                                          |
|                               |                                          |
|                               v                                          |
|                    +-------------------------+                           |
|                    |   Razorpay Adapter      |                           |
|                    |                         |                           |
|                    | - Order creation        |                           |
|                    | - Verification          |                           |
|                    | - Webhook handling      |                           |
|                    | - Reconciliation        |                           |
|                    +------------+------------+                           |
|                                 |                                        |
+---------------------------------+----------------------------------------+
                                  |
                                  v

                         +----------------------+
                         |  Razorpay Test Mode  |
                         +----------------------+


+--------------------------------------------------------------------------+
|                           DATA LAYER                                     |
+--------------------------------------------------------------------------+

                    +---------------------------+
                    | SQLAlchemy Repositories   |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    | PostgreSQL / SQLite       |
                    |                           |
                    | - Merchants               |
                    | - Products                |
                    | - Policies                |
                    | - Transactions            |
                    | - Payment attempts        |
                    | - Idempotency records     |
                    | - Audit events            |
                    +---------------------------+


+--------------------------------------------------------------------------+
|                         MCP INTEROPERABILITY                             |
+--------------------------------------------------------------------------+

        +--------------------------+
        | External AI / MCP Client |
        +------------+-------------+
                     |
                     | MCP Transport
                     v
        +--------------------------+
        | Authenticated MCP Server |
        +------------+-------------+
                     |
                     v
        +--------------------------+
        |       BuyerAdapter       |
        +------------+-------------+
                     |
                     v
        +--------------------------+
        |  Application Services    |
        +------------+-------------+
                     |
                     v
        +--------------------------+
        | Same Trusted Transaction |
        | Core used by Buyer Chat  |
        +--------------------------+
```

---

# Trust Boundary

```text
AI / MCP / Frontend
        |
        | may REQUEST
        v
+-------------------------+
| Trusted Backend         |
|                         |
| - authoritative price   |
| - buyer authorization   |
| - merchant policy       |
| - transaction state     |
| - idempotency           |
| - provider execution    |
| - payment verification  |
+------------+------------+
             |
             v
     Razorpay Test Mode
```

The architectural rule is:

```text
AI decides WHAT TO REQUEST.

Trusted backend decides WHETHER IT IS ALLOWED.

Razorpay determines PROVIDER PAYMENT TRUTH.
```

---

# End-to-End Commerce Flow

```text
Merchant
   |
   v
Describe Product
   |
   v
Merchant AI
   |
   v
Structured Draft
   |
   v
Merchant Review + Publish
   |
   v
Trusted Catalog
   |
   +--------------------------------------------------+
                                                      |
                                                      v
Buyer Intent                                      Buyer AI
"Find and buy..."                                     |
                                                      v
                                              Search Catalog
                                                      |
                                                      v
                                              Select Product
                                                      |
                                                      v
                                           Request Purchase Proposal
                                                      |
                                                      v
                                           Trusted Backend Rebuilds
                                           Authoritative Price / Qty
                                                      |
                                                      v
                                             Buyer Authorization
                                                      |
                                                      v
                                             Merchant Policy Gate
                                                      |
                                                      v
                                         AI Requests Execution
                                                      |
                                                      v
                                          Transaction State Machine
                                                      |
                                                      v
                                            Razorpay Test Mode
                                                      |
                                                      v
                                          Provider Verification
                                                      |
                                                      v
                                          Final Transaction State
                                                      |
                                                      v
                                           Structured Audit Trail
```

---

# Trust Model

The LLM is treated as an untrusted orchestrator, not as financial authority.

## AI may

* understand buyer intent
* search the catalog
* inspect products
* compare products
* recommend products
* prepare or request purchase proposals
* request transaction execution
* retrieve transaction status
* retrieve audit information
* explain trusted transaction information

## AI may not

* establish authoritative price
* authorize the buyer
* approve the merchant
* directly call Razorpay
* arbitrarily mutate financial transaction state
* mark a payment as successful
* bypass merchant or buyer policies

The trusted backend controls financial authority.

---

# Merchant Experience

Merchants manage their commerce capabilities through a dashboard.

Major capabilities include:

* AI-assisted product creation
* manual product management
* catalog publication
* inventory management
* merchant transaction policies
* review queue
* transaction history
* audit inspection

---

# AI-Assisted Catalog Creation

Product onboarding can begin conversationally.

Example:

```text
Merchant:

"I sell a 65W GaN charger for ₹1,699.
I currently have 25 units.
It has two USB-C ports and one USB-A port."
```

The Merchant AI converts that conversation into a structured product draft.

```text
Merchant Description
        |
        v
Merchant AI
        |
        v
Structured Product Draft
        |
        v
Merchant Review
        |
        v
Publish
        |
        v
Trusted Catalog
```

The AI may help generate:

* product name
* description
* category
* features
* attributes
* tags
* search metadata
* AI-readable metadata

However, AI-generated output does not automatically become authoritative.

Price, currency, inventory, and publication state become trusted only through the merchant-controlled publication flow and trusted backend validation.

---

# Reference Buyer

The primary buyer experience is conversational.

Example:

```text
Buyer:

"Find me a good 65W charger under ₹2,000 and buy one."
```

The Buyer AI can perform:

```text
Understand Intent
      |
      v
Search Catalog
      |
      v
Compare Candidates
      |
      v
Select Product
      |
      v
Request Purchase Proposal
      |
      v
Present Exact Purchase
```

The backend constructs the authoritative proposal using trusted catalog data.

Example:

```text
+--------------------------------------+
| Purchase Approval                    |
|                                      |
| VoltCharge GaN 65W                   |
| ABC Electronics                      |
|                                      |
| Quantity: 1                          |
| Amount:   ₹1,699                     |
| Currency: INR                        |
|                                      |
| [Cancel]          [Approve ₹1,699]   |
+--------------------------------------+
```

The human buyer authorizes the exact purchase.

After authorization, the trusted orchestration layer may continue automatically where merchant policy allows.

---

# Buyer Authorization

Buyer approval is intentionally separate from AI reasoning.

The AI may prepare a purchase.

It cannot authorize the purchase itself.

```text
AI prepares purchase
        |
        v
Trusted proposal created
        |
        v
Human buyer approves bounded purchase
        |
        v
Authorization stored by trusted backend
```

The authorization may be bound to:

* product
* merchant
* quantity
* amount
* currency
* proposal
* expiry

If the transaction changes outside the authorized scope, execution must be rejected.

---

# Merchant Policy Engine

Buyer authorization and merchant acceptance are independent.

Supported policy modes include:

## MANUAL_ALL

Every transaction requires merchant review.

## AUTO_BELOW_LIMIT

Transactions within configured merchant limits may be automatically accepted.

## DENY_ALL

Purchases are rejected.

A buyer authorization alone does not create merchant authority.

---

# Transaction Execution

The AI does not directly execute Razorpay actions.

Instead, it may request:

```text
execute_transaction(transaction_id)
```

This should be interpreted as:

> Trusted backend, execute this transaction only if all required conditions are satisfied.

Before provider execution, the trusted backend verifies:

```text
Buyer Authorization
        +
Merchant Authorization
        +
Valid Proposal
        +
Trusted Product State
        +
Valid Transaction State
        +
Idempotency
        |
        v
Provider Execution Allowed
```

---

# Transaction Lifecycle

Transactions follow a controlled state machine.

Typical lifecycle:

```text
PROPOSED
    |
    v
BUYER_AUTH_REQUIRED
    |
    v
MERCHANT_POLICY_PENDING
    |
    +--------------------------+
    |                          |
    v                          v
MERCHANT_REVIEW_REQUIRED      AUTO ACCEPTED
    |                          |
    +------------+-------------+
                 |
                 v
          PAYMENT_PENDING
                 |
                 v
             VERIFYING
                 |
          +------+------+
          |             |
          v             v
      SUCCEEDED       FAILED
```

Recovery-related states may also be used if provider state becomes ambiguous.

The transaction state machine prevents arbitrary financial state transitions.

---

# Razorpay Integration

Payments are executed through Razorpay Test Mode for demonstration and evaluation.

```text
AI
 |
 v
Application Service
 |
 v
Transaction Core
 |
 v
Razorpay Adapter
 |
 v
Razorpay Test Mode
```

The frontend and AI do not directly control the provider.

---

# Provider Order Is Not Payment Success

Creating a Razorpay order does not mean payment succeeded.

```text
Razorpay Order Created

          !=

Transaction SUCCEEDED
```

Final success must be based on trusted provider evidence.

This prevents:

* AI output
* frontend state
* order creation response
* client-controlled data

from becoming payment truth.

---

# Payment Verification

The backend determines final payment state using trusted provider evidence.

Depending on the transaction path, this may include:

* backend signature verification
* provider payment status
* verified webhook events
* reconciliation queries

The provider remains the source of payment truth.

---

# Idempotency

Mutating commerce operations use idempotency protections to reduce duplicate financial effects.

```text
Same Logical Request
        +
Same Idempotency Key
        +
Retries
        |
        v
Same Logical Result
```

This is important because:

* browsers retry
* networks fail
* AI tools may repeat calls
* clients may resubmit requests

The system should avoid blindly producing duplicate provider-side effects.

---

# Graceful Failure Handling

Financial systems must safely handle ambiguous failures.

For example:

```text
Provider Request
      |
      v
Ambiguous Result / Timeout
      |
      v
UNKNOWN
      |
      v
No Blind Duplicate Execution
      |
      v
RECONCILING
      |
      v
Provider Truth Lookup
      |
      v
Recovered Final State
```

Where this recovery path is enabled and exercised, the resulting events can be inspected through the audit trail.

---

# Structured Audit Trail

Financial transitions generate structured causal events.

A successful purchase may contain events corresponding to:

```text
Purchase Prepared
        |
        v
Buyer Authorized
        |
        v
Merchant Accepted
        |
        v
Execution Requested
        |
        v
Provider Interaction
        |
        v
Payment Verification
        |
        v
Purchase Complete
```

The audit trail is based on trusted application and domain events.

Raw AI conversation is not treated as financial authority.

---

# MCP Interoperability

AI Commerce Gateway also exposes commerce capabilities through an MCP server.

This allows compatible external AI clients to use the same trusted commerce infrastructure.

```text
External AI Client
       |
       v
Authenticated MCP Server
       |
       v
BuyerAdapter
       |
       v
Application Services
       |
       v
Trusted Transaction Core
       |
       v
Razorpay Test Mode
```

MCP is a separate interoperability adapter.

It is not a separate payment engine.

Both the Reference Buyer and MCP converge on the same trusted application and transaction services.

---

# MCP Capabilities

MCP may expose narrowly scoped commerce operations such as:

* search catalog
* get product
* create purchase proposal
* get purchase proposal
* request transaction execution
* get transaction status
* get transaction audit

MCP must not expose capabilities equivalent to:

* approve buyer authorization
* approve merchant decision
* change trusted product price
* mark payment successful
* mutate transaction state
* directly create Razorpay orders outside the transaction core

---

# MCP Authorization Model

A typical external AI flow is:

```text
External AI
    |
    v
Search Catalog
    |
    v
Select Product
    |
    v
Create Proposal
    |
    v
Request Execution
    |
    v
AUTHORIZATION_REQUIRED
    |
    v
Human Buyer Approves Through Trusted Channel
    |
    v
External AI Requests Execution Again
    |
    v
Merchant Gate
    |
    v
Transaction Core
    |
    v
Razorpay
```

The external AI does not receive buyer approval authority simply because it uses MCP.

---

# Shared Trusted Core

Reference Buyer and MCP follow the same financial authority model.

```text
Reference Buyer Chat
         |
         v
     BuyerAdapter
         |
         v
Application Services
         ^
         |
         |
Authenticated MCP Server
         ^
         |
 External AI Client
```

Both paths converge before financial logic.

---

# Technology Stack

## Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS
* shadcn/ui
* Lucide icons
* React Context-based application state

## Backend

* Python 3.10+
* FastAPI
* Uvicorn
* SQLAlchemy
* Alembic
* Domain-Driven Design architecture

## Database

Local development:

* SQLite

Demo deployment:

* PostgreSQL
* Supabase-compatible PostgreSQL setup

## AI

* Fireworks AI
* Qwen-family model
* tool-oriented orchestration

## Payments

* Razorpay
* Razorpay Test Mode
* backend payment verification
* webhook handling where configured
* idempotent transaction processing

## Interoperability

* MCP server
* shared BuyerAdapter/application services
* trusted backend authorization boundary

---

# Repository Structure

```text
.
|-- frontend/
|   |-- app/
|   |-- components/
|   |-- lib/
|   `-- ...
|
|-- src/
|   `-- ai_commerce_gateway/
|       |-- api/
|       |-- application/
|       |-- contracts/
|       |-- core/
|       |-- domain/
|       |-- infrastructure/
|       |-- providers/
|       `-- storage/
|
|-- migrations/
|-- tests/
|   |-- unit/
|   |-- contract/
|   `-- integration/
|
|-- docs/
|-- start-backend.bat
|-- start-frontend.bat
`-- README.md
```

The `/docs` directory contains detailed material such as:

* architecture decisions
* security design
* API specifications
* data model
* workstream plans
* audit records
* evaluation scenarios
* testing evidence
* demo documentation

---

# Getting Started

## Prerequisites

Install:

* Node.js 18+
* Python 3.10+
* `uv`
* Git

For the full AI and payment demo, you will also need:

* Fireworks AI API credentials
* Razorpay Test Mode credentials

---

# Local Development

## 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

---

## 2. Configure Environment Variables

Copy the environment template to `.env`.

If the repository currently contains:

```text
.env.example.example
```

use:

```bash
copy .env.example.example .env
```

If it has been normalized to:

```text
.env.example
```

use:

```bash
copy .env.example .env
```

Configure the required values for:

* database
* Fireworks AI
* Razorpay Test Mode
* session/auth signing
* backend/frontend URLs where applicable

Do not commit real secrets.

---

## 3. Start the Backend

On Windows:

```bash
.\start-backend.bat
```

Default backend URL:

```text
http://localhost:8001
```

---

## 4. Start the Frontend

Open another terminal:

```bash
.\start-frontend.bat
```

Default frontend URL:

```text
http://localhost:3000
```

---

# Application Routes

## Buyer

```text
http://localhost:3000/buyer
```

The buyer can:

* express purchase intent conversationally
* receive AI recommendations
* review a generated proposal
* approve a bounded purchase
* follow transaction status
* inspect purchase details and audit information

## Merchant

```text
http://localhost:3000/merchant
```

The merchant can manage:

* AI-assisted product creation
* product catalog
* publication
* merchant policy
* review queue
* transactions
* audit information

---

# Example Demo

## Step 1 — Merchant Creates a Product

Merchant says:

```text
"I'm selling a 65W GaN charger for ₹1,699.
I have 25 units available.
It has two USB-C ports and one USB-A port."
```

Merchant AI prepares a structured product draft.

```text
Merchant Chat
    |
    v
AI Extraction
    |
    v
Product Draft
    |
    v
Merchant Review
    |
    v
Publish
```

---

## Step 2 — Buyer Delegates the Purchase

Buyer says:

```text
"Find me a good 65W charger under ₹2,000 and buy one."
```

---

## Step 3 — Buyer AI Discovers and Selects

```text
Buyer AI
   |
   v
search_catalog(...)
   |
   v
get_product(...)
   |
   v
Compare
   |
   v
Select
   |
   v
create_purchase_proposal(...)
```

---

## Step 4 — Trusted Backend Creates the Proposal

The proposal is based on trusted catalog state.

```text
Product:  65W GaN Charger
Merchant: ABC Electronics
Quantity: 1
Amount:   ₹1,699
Currency: INR
```

The AI does not get to establish this amount.

---

## Step 5 — Buyer Approves

```text
+--------------------------------+
| Purchase Approval              |
|                                |
| 65W GaN Charger                |
| 1 x ₹1,699                     |
|                                |
| [Cancel]   [Approve ₹1,699]    |
+--------------------------------+
```

The authorization applies to the exact bounded purchase.

---

## Step 6 — Merchant Gate

```text
Buyer Authorization
        +
Merchant Policy
        |
        v
READY FOR EXECUTION
```

If manual review is required:

```text
MERCHANT_REVIEW_REQUIRED
```

If denied:

```text
TRANSACTION REJECTED
```

---

## Step 7 — AI Requests Execution

```text
execute_transaction(transaction_id)
```

The AI is requesting execution.

It is not granting permission to execute.

---

## Step 8 — Trusted Backend Checks Everything

```text
Valid Proposal?
      |
Buyer Authorized?
      |
Merchant Authorized?
      |
Product State Valid?
      |
Transaction State Valid?
      |
Idempotency Valid?
      |
      v
YES
      |
      v
Razorpay Adapter
```

---

## Step 9 — Razorpay Test Mode

```text
Trusted Transaction Core
        |
        v
Razorpay Adapter
        |
        v
Razorpay Test Mode
```

---

## Step 10 — Provider Verification

Creating a provider order is not enough.

```text
Provider Order
      |
      v
Payment / Provider Evidence
      |
      v
Backend Verification
      |
      v
Final Transaction State
```

---

## Step 11 — Audit

The complete financial decision chain can be inspected.

```text
Proposal Prepared
      |
      v
Buyer Authorized
      |
      v
Merchant Accepted
      |
      v
Execution Requested
      |
      v
Provider Interaction
      |
      v
Payment Verified
      |
      v
Final State
```

---

# Failure Demo

A strong failure scenario is an ambiguous provider result.

```text
Execution Requested
       |
       v
Provider Request Dispatched
       |
       v
Timeout / Ambiguous Response
       |
       v
UNKNOWN
       |
       v
No Blind Retry
       |
       v
RECONCILING
       |
       v
Provider Status Lookup
       |
       v
Recovered Final State
```

The important properties are:

* no false success
* no blind duplicate execution
* safe intermediate status
* reconciliation
* provider truth
* structured audit trail
* understandable user-facing explanation

---

# Testing

The repository includes tests across multiple layers.

Relevant areas include:

* domain logic
* catalog behavior
* merchant policy
* transaction state machine
* buyer authorization
* buyer application services
* repository behavior
* API validation
* tenant isolation
* idempotency
* provider integration
* AI tool boundaries
* MCP
* end-to-end scenarios where configured

A test result must be interpreted based on the exact commit and environment in which it was run.

Important distinction:

```text
Unit Tested
     !=
Integration Tested
     !=
Local E2E Verified
     !=
Deployed E2E Verified
```

Likewise:

```text
Mock Razorpay Test
     !=
Actual Razorpay Test Mode
```

and:

```text
Direct Python MCP Function Test
     !=
Actual MCP Transport E2E
```

---

# Demo Readiness Target

The intended project target is:

```text
LOCAL E2E VERIFIED
        +
MCP E2E VERIFIED
        +
DEMO DEPLOYMENT READY
        +
DEPLOYED E2E VERIFIED
```

This is intentionally different from claiming enterprise production readiness.

---

# Demo Deployment

The application is intended to support a public demo deployment.

A simple deployment architecture is sufficient:

```text
                    Internet
                       |
                       v
             +-------------------+
             | Next.js Frontend  |
             +---------+---------+
                       |
                       | HTTPS
                       v
             +-------------------+
             | FastAPI Backend   |
             |                   |
             | Merchant AI       |
             | Buyer AI          |
             | BuyerAdapter      |
             | Transaction Core  |
             | Razorpay Adapter  |
             | MCP Server        |
             +---------+---------+
                       |
                       v
             +-------------------+
             | Managed PostgreSQL|
             +-------------------+

Backend outbound:

        +------------------+
        | Fireworks AI     |
        +------------------+

        +------------------+
        | Razorpay Test    |
        | Mode             |
        +------------------+
```

The exact hosting provider is flexible.

The deployment goal is to demonstrate the integrated system, not enterprise infrastructure.

---

# What Demo Deployment Should Prove

A deployed demonstration should prove:

* frontend production build works
* backend starts in deployment configuration
* persistent PostgreSQL works
* migrations succeed
* merchant flow works
* buyer AI flow works
* Razorpay Test Mode integration works
* payment verification works
* audit trail is visible
* one failure is handled safely
* MCP can use the same trusted commerce services

---

# What This Project Does Not Need to Claim

A successful demo does not automatically mean:

```text
Enterprise Production Ready
```

The project does not need to claim:

* Kubernetes readiness
* multi-region availability
* enterprise SSO
* enterprise disaster recovery
* production payment credentials
* high-scale autoscaling
* full enterprise observability
* production SLA guarantees

The goal is:

> a real, secure-enough, reproducible agentic-commerce demo with trusted financial boundaries.

---

# Security Model

Important security boundaries include:

* authoritative prices come from trusted catalog/backend state
* AI cannot authorize itself
* buyer and merchant decisions are separate
* identity comes from trusted authenticated context
* financial state cannot be controlled by the frontend
* MCP cannot bypass transaction rules
* MCP cannot provide financial authorization
* provider order creation is not treated as payment success
* final payment success requires trusted provider evidence
* idempotency reduces duplicate financial effects
* tenant ownership is enforced at trusted boundaries
* audit events reconstruct financial decisions
* raw AI conversation is not financial authority

---

# Design Philosophy

The system follows a simple authority model:

```text
PRODUCT FACTS
    |
    v
Merchant / Trusted Catalog

PRICE
    |
    v
Trusted Backend

PRODUCT SELECTION
    |
    v
Buyer AI May Choose

PURCHASE PROPOSAL
    |
    v
AI Requests
Backend Constructs

BUYER CONSENT
    |
    v
Human Buyer

MERCHANT CONSENT
    |
    v
Merchant Policy / Merchant Human

EXECUTION REQUEST
    |
    v
AI May Initiate

EXECUTION PERMISSION
    |
    v
Trusted Transaction Core

PAYMENT EXECUTION
    |
    v
Razorpay Adapter

PAYMENT TRUTH
    |
    v
Razorpay + Backend Verification

FINAL STATE
    |
    v
Trusted State Machine

EXPLANATION
    |
    v
Structured Audit Trail
```

---

# Project Goal

AI Commerce Gateway demonstrates an approach to agentic commerce where:

> AI handles intent, discovery, selection, and orchestration, while trusted systems retain identity, authorization, merchant policy, payment execution, and final financial truth.

The target experience is:

```text
Merchant
   |
   v
AI-Assisted Catalog
   |
   v
Trusted Publication
   |
   v
Buyer AI Discovery
   |
   v
AI Product Selection
   |
   v
Trusted Proposal
   |
   v
Buyer Authorization
   |
   v
Merchant Gate
   |
   v
AI Requests Execution
   |
   v
Trusted Transaction Core
   |
   v
Razorpay Test Mode
   |
   v
Provider Verification
   |
   v
Audit Trail
```

---

# Core Challenge Statement

The system is designed around the requirement:

> **Every money action should be explainable, bounded, and gated.**

That means:

```text
EXPLAINABLE
Who requested it?
Why?
For what amount?
What authorization existed?
What did the provider return?

BOUNDED
Which product?
Which merchant?
Which quantity?
Which amount?
Which currency?
Which authorization?

GATED
Buyer authorized?
Merchant authorized?
Proposal valid?
Transaction valid?
Idempotency satisfied?
Provider execution allowed?
```

---

# Final Demo Scope

The intended final demonstration includes:

```text
1. Merchant creates a product with AI.

2. Merchant reviews and publishes it.

3. Buyer gives natural-language purchase intent.

4. Buyer AI discovers and selects the product.

5. Trusted backend creates the proposal.

6. Human buyer approves the bounded purchase.

7. Merchant policy is evaluated independently.

8. AI requests transaction execution.

9. Trusted backend executes through Razorpay Test Mode.

10. Backend verifies provider truth.

11. Buyer sees final status.

12. Structured audit reconstructs the money flow.

13. One failure is demonstrated safely.

14. MCP demonstrates the same commerce services through an external AI interface.
```

---

# Documentation

Detailed project documentation is stored in:

```text
/docs
```

This includes:

* architecture
* API design
* data model
* security model
* evaluation scenarios
* workstream documentation
* audit results
* testing evidence
* demo planning

---

# Status and Evidence

Claims such as:

```text
LOCAL E2E VERIFIED
MCP E2E VERIFIED
DEPLOYED E2E VERIFIED
DEMO DEPLOYMENT READY
```

should only be used when supported by the latest audit and runtime evidence for the exact submitted commit.

The project should not rely on documentation alone as proof of implementation.

The evidence chain is:

```text
CLAIMED
   |
   v
IMPLEMENTED
   |
   v
TESTED
   |
   v
ADVERSARIALLY TESTED
   |
   v
E2E VERIFIED
```

These levels are intentionally not treated as equivalent.

---

# Summary

AI Commerce Gateway is an AI-native commerce system where:

```text
AI understands the request.
AI discovers the product.
AI selects the product.
AI prepares the purchase.

            BUT

AI does not control the money.

Trusted systems control:
- price
- buyer authorization
- merchant authorization
- execution permission
- Razorpay interaction
- payment verification
- final state

            AND

the complete decision chain is auditable.
```

The result is a commerce flow designed to make merchants transactable by AI buyers end to end while preserving trusted financial boundaries.

> **AI orchestrates. Humans authorize. Trusted systems enforce. Razorpay settles the payment truth.**
