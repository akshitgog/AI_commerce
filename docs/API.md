# API and MCP contract — v1

## Conventions

- Base path: `/v1`.
- JSON request and response bodies.
- Money: `{ "amount_minor": 50000, "currency": "INR" }`.
- Authenticated actor context comes from the server-validated session/token, never a trusted body field.
- All responses include `correlation_id`.
- Mutating creation/execution operations require `Idempotency-Key`.
- Client-supplied totals, provider states and merchant ownership are never authoritative.

## Stable error envelope

```json
{
  "error": {
    "code": "AUTHORIZATION_REQUIRED",
    "message": "Buyer authorization is required.",
    "details": {}
  },
  "correlation_id": "corr_..."
}
```

Core codes: `UNAUTHENTICATED`, `FORBIDDEN`, `NOT_FOUND`, `VALIDATION_ERROR`, `PRODUCT_UNAVAILABLE`, `PROPOSAL_STALE`, `AUTHORIZATION_REQUIRED`, `AUTHORIZATION_INVALID`, `MERCHANT_REVIEW_REQUIRED`, `POLICY_DENIED`, `INVALID_STATE`, `IDEMPOTENCY_KEY_REUSED`, `PROVIDER_OUTCOME_UNKNOWN`, `PROVIDER_ERROR`.

## Merchant routes

| Method and path | Actor | Purpose |
|---|---|---|
| `POST /merchants` | Platform/demo onboarding | Create merchant |
| `GET /merchants/{merchant_id}` | Merchant member | Read own merchant profile |
| `POST /merchants/{merchant_id}/products` | Merchant editor | Create draft product |
| `GET /merchants/{merchant_id}/products/{product_id}` | Merchant member | Read product including draft state |
| `PATCH /merchants/{merchant_id}/products/{product_id}` | Merchant editor | Update product and increment version |
| `POST /merchants/{merchant_id}/products/{product_id}/publish` | Merchant editor | Publish reviewed version |
| `POST /merchants/{merchant_id}/products/{product_id}/unpublish` | Merchant editor | Remove from buyer discovery |
| `POST /merchants/{merchant_id}/catalog/import` | Merchant editor | Validate/import CSV |
| `POST /merchants/{merchant_id}/products/{product_id}/enrich` | Merchant editor | Suggest descriptive metadata only |
| `GET /merchants/{merchant_id}/policy` | Merchant member | Read purchase policy |
| `PUT /merchants/{merchant_id}/policy` | Merchant admin | Replace/version purchase policy |
| `GET /merchants/{merchant_id}/reviews` | Merchant member | List pending manual reviews |
| `POST /merchants/{merchant_id}/reviews/{proposal_id}/decide` | Merchant approver | Record allow/deny decision |

Every route verifies the authenticated user's membership and role for the path merchant.

## Buyer catalog routes

| Method and path | Purpose |
|---|---|
| `GET /catalog/search?merchant_id=&query=&category=&min_price_minor=&max_price_minor=&currency=&cursor=` | Search published products for the selected merchant |
| `GET /catalog/products/{product_id}` | Read current published product |

V1 requires `merchant_id`; it does not perform global cross-merchant ranking.

## Proposal and authorization routes

`POST /purchase-proposals`

```json
{
  "merchant_id": "mer_123",
  "product_id": "prod_123",
  "quantity": 1
}
```

The authenticated buyer is derived from actor context. The response contains the immutable proposal ID/hash, trusted unit price and total, expiry and next required gate.

| Method and path | Actor | Purpose |
|---|---|---|
| `POST /purchase-proposals/{id}/authorization-requests` | Buyer client/AI | Create an approval request; never approves it |
| `POST /purchase-proposals/{id}/buyer-approval` | Authenticated human buyer | Approve the exact proposal |
| `GET /purchase-proposals/{id}` | Authorized buyer/merchant | Read proposal and gate status |

## Transaction routes

| Method and path | Purpose |
|---|---|
| `POST /transactions` | Create/reuse a logical transaction from a ready proposal |
| `POST /transactions/{id}/execute` | Revalidate gates and create/reuse provider checkout attempt |
| `GET /transactions/{id}` | Read platform state and redacted provider phase |
| `POST /transactions/{id}/reconcile` | Request safe provider lookup; never blind retry |
| `GET /transactions/{id}/events?cursor=` | Read redacted causal audit events |

`execute` can return `PAYMENT_PENDING`; it does not promise immediate `SUCCEEDED`.

## Provider callbacks

| Method and path | Purpose |
|---|---|
| `POST /webhooks/razorpay` | Verify signature, deduplicate event, map reference and update state |
| `POST /checkout/razorpay/verify` | Verify supported checkout-return signature/data for the selected integration |

Exact required fields are finalized from the Razorpay Test Mode spike and isolated inside the adapter contract.

## MCP tools

| Tool | Maps to | Financial effect |
|---|---|---|
| `search_catalog` | Catalog search | None |
| `get_product` | Published product read | None |
| `create_purchase_proposal` | Proposal creation | None; immutable proposal only |
| `request_authorization` | Authorization request | None; cannot approve |
| `execute_transaction` | Transaction create/execute | May initiate provider order only after gates |
| `get_transaction_status` | Transaction read | None |
| `get_transaction_audit` | Event read | None |

MCP schemas accept business identifiers and quantities only. They never accept provider credentials, arbitrary trusted prices, forced states or a flag that bypasses approval.
