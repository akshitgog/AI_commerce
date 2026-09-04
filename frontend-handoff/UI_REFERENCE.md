# UI reference

## Product and actors

- The merchant is the primary customer. They publish products, maintain price and stock, choose an
  acceptance policy, review proposals and inspect transaction evidence.
- The human buyer owns purchase consent. An AI may discover, explain and propose, but cannot approve
  for the buyer.
- The trusted backend derives totals from current catalog data, evaluates gates, owns transaction
  state, calls the provider through its adapter and writes audit events.
- Reference Buyer Chat is the primary buyer demo. MCP is a separate external interoperability
  adapter over the same application services. Normal buyer screens must not expose MCP concepts.

## Commerce concepts

- A proposal is an immutable, expiring snapshot containing product/version, quantity, trusted unit
  price, total and proposal hash.
- Buyer authorization binds the human buyer to that exact proposal and bounded amount/quantity.
- Merchant acceptance is a separate gate, produced by merchant policy or manual review.
- Money is always an integer minor-unit amount plus explicit currency. The UI formats server values;
  it does not establish them.
- Product price, currency, stock, merchant identity and publication are authoritative. AI-suggested
  description, tags and similar metadata are descriptive only.

## Lifecycle

Canonical transaction states are `PROPOSED`, `BUYER_AUTH_REQUIRED`, `MERCHANT_POLICY_PENDING`,
`MERCHANT_REVIEW_REQUIRED`, `READY`, `EXECUTING`, `PAYMENT_PENDING`, `UNKNOWN`, `VERIFYING`,
`RECONCILING`, `SUCCEEDED`, `FAILED`, `CANCELLED` and `EXPIRED`.

`UNKNOWN` and `RECONCILING` should be presented as **Recovering**. They mean provider truth is being
resolved safely, not that payment definitively failed. Creating a provider order is initiation, not
success.

Audit is a causal timeline: actor, action, reason, previous/new state, time, correlation ID and only
redacted provider references.

Every merchant screen must remain scoped to the authenticated merchant. Never imply that switching
a client-side merchant ID grants access.

## The UI must never imply

- that an AI or MCP tool can approve or move money autonomously;
- that buyer consent equals merchant acceptance;
- that a displayed/client-calculated price is authoritative;
- that provider order creation equals success;
- that an uncertain outcome is safe to retry blindly;
- that draft products are buyer-discoverable;
- that one merchant can inspect another merchant's records;
- that mock IDs or statuses are real Razorpay evidence.

