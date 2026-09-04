# Reference Buyer Chat — UI Specification

## Purpose

Reference Buyer Chat is the primary buyer-facing demonstration surface for the AI Commerce Gateway.

It demonstrates how a human buyer can:

1. express natural-language shopping intent;
2. discover products from a participating merchant;
3. inspect a product;
4. receive a trusted purchase proposal;
5. explicitly authorize that proposal;
6. see merchant acceptance as a separate gate;
7. continue to payment;
8. observe payment verification;
9. understand recovery when provider truth is uncertain;
10. receive a final verified outcome.

This is NOT:

* a marketplace;
* an Amazon-style storefront;
* a generic AI chatbot;
* an MCP interface;
* a merchant administration interface;
* a payment engine.

MCP terminology must not appear in the normal buyer experience.

---

# 1. Visual personality

The buyer experience should feel:

**Conversational · Trustworthy · Calm · Premium · Financially Precise**

It should visually belong to the same product as the Merchant Dashboard while being clearly optimized for a buyer rather than an operator.

Use:

* clean neutral background;
* centered conversation canvas;
* restrained chat bubbles;
* rich product cards;
* authoritative transaction/proposal cards;
* clear status progression;
* strong typography for money;
* subtle borders;
* minimal animation.

Avoid:

* marketplace grids;
* endless product feeds;
* promotional banners;
* aggressive upselling;
* neon AI styling;
* robot illustrations;
* excessive gradients;
* fake AI-thinking animations.

---

# 2. Page structure

Desktop layout:

```text
┌───────────────────────────────────────────────────────────────┐
│ AI Commerce Gateway                     Demo Buyer   Test Mode│
├───────────────────────────────────────────────────────────────┤
│                                                               │
│                  Reference Buyer Chat                         │
│                                                               │
│   ┌───────────────────────────────────────────────────────┐   │
│   │ Conversation                                          │   │
│   │                                                       │   │
│   │ Buyer message                                        │   │
│   │ AI response                                          │   │
│   │ Product result                                       │   │
│   │ Purchase proposal                                    │   │
│   │ Authorization / transaction progress                 │   │
│   │                                                       │   │
│   └───────────────────────────────────────────────────────┘   │
│                                                               │
│   [ Ask about products...                              ] [→]  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

An optional transaction-progress side panel may appear after a proposal exists.

Do not show this panel before it becomes useful.

---

# 3. Initial state

The initial screen should immediately explain what the buyer can do.

Example:

```text
Shop with AI

Tell me what you're looking for from Demo Electronics.

Try:
"Find me a USB-C charger under ₹1,000."

[ Find me a USB-C charger under ₹1,000 ]
```

Keep onboarding short.

Do not explain MCP, APIs or backend architecture.

---

# 4. Buyer message

Example:

```text
You

Find me a USB-C charger under ₹1,000.
```

Buyer messages should be visually distinct but restrained.

---

# 5. AI search state

Use a subtle temporary state:

```text
Searching Demo Electronics catalog…
```

Do not use theatrical "AI is thinking deeply" animations.

The buyer should understand that the AI is searching merchant catalog information.

---

# 6. Product result

Example:

```text
I found a matching product from Demo Electronics.

┌──────────────────────────────────────────┐
│ [Product image]                          │
│                                          │
│ 65W USB-C Charger                        │
│ Demo Electronics                         │
│                                          │
│ ₹899                                     │
│ In stock · 10 available                  │
│                                          │
│ 65W fast charging · USB-C                │
│                                          │
│ [View details]             [Buy for ₹899]│
└──────────────────────────────────────────┘
```

Product result should display:

* image;
* title;
* merchant;
* formatted trusted price;
* stock/availability;
* short descriptive metadata;
* primary purchase action.

Do not present dozens of marketplace controls.

---

# 7. Product details

If opened, show:

* image gallery;
* title;
* description;
* category;
* merchant;
* trusted price;
* availability;
* relevant descriptive attributes.

Do not expose internal IDs/version information prominently.

Technical information can be available in secondary details if needed for the demo.

---

# 8. Purchase proposal

After the buyer chooses the product, create a visually stronger object than an ordinary chat response.

Example:

```text
Purchase Proposal

65W USB-C Charger
Demo Electronics

Quantity                         1
Unit price                    ₹899
─────────────────────────────────
Trusted total                ₹899

✓ Price derived from the merchant catalog

Proposal expires in 09:42

Buyer approval required

[Cancel]                 [Approve ₹899]
```

The proposal card should communicate that the AI has proposed a purchase but has NOT authorized it.

Important information:

* product;
* merchant;
* quantity;
* trusted unit price;
* trusted total;
* expiry;
* buyer authorization state.

The UI formats trusted backend values.

It does not establish authoritative money.

---

# 9. Buyer authorization

Before approval:

```text
Buyer authorization

○ Approval required

This purchase has not been authorized yet.
```

After the human presses `Approve ₹899`:

```text
Buyer authorization

✓ Approved by you
₹899 · Quantity 1
```

The AI must never visually appear to approve its own purchase request.

Typing:

```text
buy it
```

may cause the system to prepare or display the proposal, but must not visually imply that payment moved without the required authorization mechanism.

---

# 10. Merchant acceptance

Merchant acceptance must always appear separately from buyer authorization.

Example automatic acceptance:

```text
Merchant acceptance

✓ Accepted

Demo Electronics automatically accepts
eligible purchases up to ₹1,000.

This purchase: ₹899
```

Example manual review:

```text
Merchant acceptance

○ Merchant review required

Demo Electronics needs to review this purchase.

We'll update this transaction when the merchant responds.
```

Example denial:

```text
Merchant acceptance

× Not accepted

The merchant's current policy does not allow
this purchase.
```

Never use one generic `Approved` badge for both gates.

---

# 11. Ready state

Only when both gates are satisfied:

```text
Ready for payment

✓ Buyer authorized
✓ Merchant accepted

Trusted total
₹899

[Continue to secure payment]
```

The buyer should understand why payment is now allowed.

---

# 12. Payment handoff

Display a clean payment handoff state:

```text
Secure payment

65W USB-C Charger
Demo Electronics

Total
₹899

You'll continue to Razorpay Test Mode to
complete the payment.

[Continue to payment]
```

The frontend must not pretend that clicking this button itself means payment succeeded.

---

# 13. Payment pending

After checkout submission:

```text
Payment submitted

We're waiting for payment confirmation.

● Payment submitted
○ Verification
○ Final confirmation
```

Provider-order creation or checkout initiation must never appear as final success.

---

# 14. Verification

Example:

```text
Verifying payment

We're confirming the payment provider's
authoritative result.

✓ Payment submitted
● Verification in progress
○ Final confirmation
```

Use calm progress treatment.

---

# 15. Recovering

Recovery is a first-class state.

Example:

```text
Recovering payment status

The payment provider's result is temporarily
uncertain.

We're checking the provider for the
authoritative result.

No duplicate payment will be attempted.

Last checked: a few seconds ago

◌ Checking payment status…
```

Important:

* do not show `Pay Again`;
* do not label the transaction Failed;
* do not panic the user;
* explain that provider truth is being resolved.

---

# 16. Success

Only show success after backend/provider verification.

Example:

```text
✓ Payment verified

Purchase completed successfully.

65W USB-C Charger
Demo Electronics

Total paid
₹899

Transaction
TXN-8F21A

[View transaction details]
```

---

# 17. Failure

Example:

```text
Payment unsuccessful

The payment was not completed.

No successful payment was recorded for this
transaction.

[View details]
```

Only offer another payment attempt when the trusted backend says doing so is safe.

---

# 18. Expired proposal

Example:

```text
Proposal expired

The purchase proposal is no longer valid.

Product price, stock or availability may have
changed.

[Create new proposal]
```

Never silently reuse stale authorization.

---

# 19. Transaction progress component

After proposal creation, an optional desktop side panel can show:

```text
Purchase progress

✓ Product selected
✓ Proposal created
✓ Buyer authorized
✓ Merchant accepted
● Payment
○ Verification
○ Complete
```

Buyer authorization and merchant acceptance must remain separate rows.

---

# 20. Responsive behavior

Desktop:

* centered chat;
* optional progress side panel.

Tablet:

* slightly wider conversation;
* progress card below current transaction.

Mobile:

* single column;
* full-width product/proposal cards;
* sticky composer where appropriate;
* payment and authorization actions remain reachable.

---

# 21. Trust rules

The buyer UI must never imply:

* AI can authorize spending itself;
* AI controls trusted price;
* buyer authorization equals merchant acceptance;
* checkout initiation equals payment success;
* provider order creation equals payment success;
* an uncertain payment can safely be retried blindly;
* MCP is part of the normal buyer interaction;
* client-calculated values are authoritative.

The central visual principle is:

**AI proposes. Human authorizes. Merchant accepts. Trusted backend executes and verifies.**
