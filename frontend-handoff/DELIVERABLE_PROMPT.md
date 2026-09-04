# Portable frontend-generation prompt

Create a cohesive, production-quality visual prototype for an **AI Commerce Gateway** using
Next.js, TypeScript, React, Tailwind CSS, shadcn/ui and Lucide React. Use Recharts only if a chart
materially improves an operational merchant decision. Centralize mock data and types, use reusable
components, and place all data access behind a replaceable mock service/API layer.

The product lets a merchant publish an AI-readable catalog and safely become transactable by an AI
buyer. It is not a marketplace, Amazon clone, shopping-comparison site, revenue-analytics dashboard,
crypto product, or MCP administration dashboard.

## Build two distinct surfaces

### A. Merchant Dashboard

Navigation: Overview, Products, Policy, Review Queue, Transactions, Audit, Settings.

Prioritize these cohesive screens:

1. Overview with AI-ready published products, proposals awaiting action, processing and recovering
   transactions, and recent operational activity. Avoid vanity metrics.
2. Products with image, title, SKU, category, trusted price/currency, stock, publication status and
   version. Include Create, Edit, Publish, Unpublish, View and Delete Draft interactions. Product
   create/edit supports one to three images.
3. Optional “Suggest description” assistance may propose descriptive metadata, but it must never
   alter price, currency, stock, merchant identity or publication state silently.
4. Policy with only `MANUAL_ALL`, `AUTO_BELOW_LIMIT` and `DENY_ALL`. Show a currency/amount threshold
   only for `AUTO_BELOW_LIMIT`; do not create a generic rule builder.
5. Review Queue showing product/image, quantity, buyer reference, trusted total, buyer-authorization
   status, expiry, review reason, Approve, Deny and View Details.
6. Transactions with ID, product, buyer reference, amount, buyer authorization, merchant
   policy/decision, user-facing status, provider/payment phase and timestamp.
7. Transaction Detail with proposal summary, trusted amount, separate buyer and merchant gates,
   platform status, payment status, recovery information and structured audit timeline.
8. Audit as a causal timeline of actor, action, status change, reason, time, correlation reference
   and redacted provider reference—not raw server logs.

### B. Reference Buyer Chat

Create a polished conversational shopping UI where a buyer can say “Find me a USB-C charger under
₹1,000.” Show buyer messages, assistant responses, rich product cards, product images, merchant
identity, trusted price, stock, authoritative proposal cards, approval controls, transaction
progress, payment handoff, verification, recovery and final outcome.

A proposal should be visually stronger than an ordinary message:

```text
65W USB-C Charger
₹899 · In stock
Quantity: 1
Trusted total: ₹899

Buyer approval required
[Approve ₹899] [Cancel]
```

Typing “buy it” must not appear to move money. The AI proposes; the human buyer authorizes; merchant
policy or a merchant accepts; the trusted backend executes and determines the outcome.

The normal buyer UI must not mention MCP. MCP is separate external interoperability infrastructure,
not the buyer experience.

## Required journey and status presentation

```text
buyer intent → catalog search → product → proposal → buyer authorization
→ merchant acceptance/policy → payment handoff → verification → final outcome
```

Keep **Buyer authorization** and **Merchant acceptance** visibly separate. Use human labels:
Awaiting buyer approval, Awaiting merchant approval, Ready, Processing payment, Payment pending,
Recovering, Succeeded, Failed, Cancelled and Expired. Raw canonical states may appear only in a
technical detail area. Recovering is an active, first-class state and must not look like a normal
failure.

## Visual direction

Aim for modern fintech: professional, trustworthy, minimal, calm, precise and information-dense.
Use restrained neutral surfaces, subtle borders, strong typography, compact tables, purposeful
cards, clear spacing, status badges and excellent loading/empty/error states. Make it responsive and
accessible. Avoid neon AI, cyberpunk, crypto styling, huge gradients, excessive motion, robot art,
stock photography, marketplace language, and copying Razorpay branding.

## Non-negotiable architecture constraints

- React is presentation and interaction only.
- Never calculate an authoritative total, approve a buyer, accept for a merchant, infer payment
  success, or mutate transaction truth client-side.
- Never treat provider-order creation as success.
- Never call Razorpay directly from arbitrary UI components.
- Never place MCP business logic in the frontend.
- Do not invent backend endpoints. Name mock service operations after the supplied backend contract
  and make replacement straightforward.
- Render server-provided trusted values and state.

Use this separation:

```text
UI components → frontend service layer → backend API/application services
```

Read the frontend handoff in layers:

1. Start with `UI_REFERENCE.md` and `DESIGN_SYSTEM.md` for shared product, trust, and visual rules.
2. Read the specifications under `shared/` for shared UI rules, reusable components, and demo data.
3. For the merchant surface, read the specifications under `merchant/`.
4. For the buyer surface, read the specifications under `buyer/`.
5. Finally validate the complete prototype against `SCREEN_FLOWS.md` and `ACCEPTANCE_CHECKLIST.md`.

Deliver one cohesive, navigable prototype containing both the Merchant Dashboard and Reference Buyer
Chat rather than disconnected mock screens. Normal buyer UX must not expose MCP concepts.

