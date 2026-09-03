# AI Commerce Gateway

## Track and one-line idea

This project targets **Razorpay Track 1 — AI Growth & Agentic Commerce, AI-buyer branch**.

It helps a nontechnical merchant publish an agent-readable catalog and become transactable through a reference AI buyer chat, while every money action remains explainable, bounded, gated and auditable and is executed using Razorpay Test Mode. A remote MCP server separately proves that compatible external AI applications can reuse the same commerce services.

## Why this product exists

A local merchant should not need to understand JSON schemas, MCP, LLM tool design, idempotency or payment reconciliation. The merchant uses a dashboard to publish products and choose acceptance policies. An authorized AI client can then discover those products and initiate a purchase without receiving unrestricted payment authority.

```text
Merchant onboarding
→ product creation/import
→ merchant review and publication
→ agent-readable catalog
→ reference buyer-chat discovery
→ AI purchase proposal
→ buyer authorization
→ merchant policy/approval
→ server-side revalidation
→ Razorpay Test Mode checkout
→ provider verification or reconciliation
→ final state and causal audit timeline
```

## Product surfaces

### Merchant dashboard

The demonstrated merchant can:

- sign in;
- create, edit and publish products;
- configure automatic acceptance limits or manual review;
- view proposals, transactions and payment state;
- approve a purchase when merchant review is required;
- inspect rejection and recovery reasons;
- inspect the structured financial audit timeline.

### AI-buyer interfaces

The reference buyer chat is the primary guaranteed demo path. It can:

- search the published catalog;
- read current product data;
- create an immutable purchase proposal;
- request buyer authorization;
- initiate an already authorized and merchant-accepted transaction;
- read transaction status and the redacted audit trail.

The remote MCP server is a separate interoperability adapter exposing the same narrow operations to compatible external AI applications. MCP is not a payment engine and is not a prerequisite for the primary buyer demo. Reference chat, MCP and HTTP all call the same application services.

### Transaction authority

The backend:

- calculates money from trusted catalog records;
- binds authorization to a specific proposal and limits;
- evaluates merchant policy separately from buyer consent;
- revalidates price, version and stock immediately before execution;
- creates at most one provider order for one logical transaction;
- verifies Razorpay payment state;
- reconciles ambiguous outcomes before permitting another attempt;
- records an append-only causal event history.

## Roles and authority

| Actor | Can do | Cannot do |
|---|---|---|
| Merchant | Own catalog, price, stock and merchant acceptance policy | Grant buyer consent |
| Human buyer | Approve a proposal or grant a bounded mandate | Override merchant policy or trusted price |
| AI buyer | Discover, explain, propose and invoke narrow tools | Approve itself, set trusted money or call Razorpay directly |
| Backend | Enforce gates, execute, verify and record state | Invent buyer consent |
| Razorpay | Report Test Mode provider state | Define platform authorization or merchant policy |

## Razorpay completion rule

Creating a Razorpay order is only payment initiation. It does not mean the purchase succeeded. The platform enters `SUCCEEDED` only after the implemented Test Mode payment/capture condition has been independently verified through a validated checkout response, verified webhook and/or provider lookup.

## Scope boundary

V1 demonstrates one merchant through the reference buyer chat and separately proves one external MCP client integration. A second merchant fixture proves tenant isolation. The system is not a marketplace and does not scrape, compare or route across open-web merchants.

AI-assisted catalog enrichment is optional and may suggest descriptive metadata only. Price, currency, stock and publication status remain merchant-controlled structured fields.

## Definition of done

A judge can:

1. publish a product from the merchant dashboard;
2. discover it through the reference buyer chat;
3. create and approve a proposal;
4. complete a Razorpay Test Mode checkout;
5. see verified success rather than only an order ID;
6. observe a buyer-limit or merchant-policy gate;
7. replay execution without creating another provider order;
8. inject one timeout and watch safe reconciliation;
9. reconstruct every consequential action from the audit timeline.

Separately, a judge can see an MCP-capable external application discover the same catalog and create a proposal through the same backend services.

## Explicit non-goals

- Revenue campaigns, upsell or cross-sell engines.
- Cross-merchant ranking, price comparison or marketplace routing.
- Web scraping or universal merchant discovery.
- Multiple buyer-channel integrations.
- Full ACP, AP2, UAP or x402 implementations.
- Multiple payment providers or real-money production use.
- Native applications, microservice breadth or production-scale infrastructure.

## Evidence status

These documents specify intended behavior. They do not prove implementation. Actual test results belong only in [TESTED.md](TESTED.md), with `PASS`, `FAIL`, `NOT RUN` or `BLOCKED` status and reproducible evidence.
