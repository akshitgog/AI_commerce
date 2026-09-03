# Canonical data model

All identifiers are opaque. Money is integer minor units plus explicit currency. Timestamps are UTC. Mutable business records include version or updated timestamp for concurrency control.

## Merchant and catalog

### Merchant

`id`, `name`, `status`, `created_at`, `updated_at`

### MerchantUser

`id`, `merchant_id`, `user_id`, `role`, `created_at`

Unique membership: `(merchant_id, user_id)`.

### Product

`id`, `merchant_id`, `sku`, `title`, `description`, `category`, `price_minor`, `currency`, `available_quantity`, `status`, `version`, `created_at`, `updated_at`

Unique merchant SKU: `(merchant_id, sku)`. Buyer discovery returns only `PUBLISHED` records.

### ProductMetadata

`product_id`, `tags`, `attributes_json`, `search_text`, `source`, `review_status`, `updated_at`

AI enrichment can change descriptive metadata only after merchant review; it cannot change price, currency, stock or publication status.

### MerchantPolicy

`id`, `merchant_id`, `mode`, `auto_accept_max_minor`, `currency`, `version`, `status`, `created_at`, `updated_at`

V1 modes: `MANUAL_ALL`, `AUTO_BELOW_LIMIT`, `DENY_ALL`.

## Buyer consent and merchant acceptance

### Buyer

`id`, `external_identity`, `status`, `created_at`

### PurchaseProposal

`id`, `buyer_id`, `merchant_id`, `product_id`, `product_version`, `quantity`, `unit_price_minor`, `total_minor`, `currency`, `proposal_hash`, `status`, `expires_at`, `created_at`

The commercial snapshot is immutable.

### BuyerAuthorization

`id`, `buyer_id`, `proposal_id`, `proposal_hash`, `merchant_id`, `product_id`, `max_quantity`, `max_amount_minor`, `currency`, `authorized_by`, `status`, `expires_at`, `created_at`

`authorized_by` must resolve to an authenticated human-controlled approval surface or an already established bounded mandate—not the requesting AI identity.

### MerchantDecision

`id`, `proposal_id`, `merchant_id`, `policy_id`, `policy_version`, `decision`, `reason_code`, `decided_by`, `expires_at`, `created_at`

Decision is `ALLOW`, `DENY` or `REVIEW_REQUIRED`; a later authenticated manual decision records the merchant operator.

## Transaction and provider

### Transaction

`id`, `proposal_id`, `buyer_authorization_id`, `merchant_decision_id`, `merchant_id`, `buyer_id`, `amount_minor`, `currency`, `state`, `created_at`, `updated_at`

### IdempotencyRecord

`id`, `actor_id`, `operation`, `idempotency_key`, `request_fingerprint`, `resource_type`, `resource_id`, `response_code`, `response_body_hash`, `created_at`

Unique: `(actor_id, operation, idempotency_key)`.

### PaymentAttempt

`id`, `transaction_id`, `attempt_number`, `provider`, `provider_request_fingerprint`, `provider_order_id`, `provider_payment_id`, `provider_order_state`, `provider_payment_state`, `capture_state`, `last_verified_at`, `created_at`, `updated_at`

V1 normally permits one creation attempt per logical transaction. A controlled retry requires confirmed non-creation/failure and a distinct recorded attempt.

### ProviderWebhook

`id`, `provider`, `provider_event_id`, `signature_valid`, `payload_hash`, `transaction_id`, `processing_status`, `received_at`, `processed_at`

Unique: `(provider, provider_event_id)`.

### TransactionEvent

`id`, `transaction_id`, `event_type`, `actor_type`, `actor_id`, `reason_code`, `previous_state`, `new_state`, `correlation_id`, `provider_reference_redacted`, `metadata_json`, `created_at`

Append-only. Metadata cannot contain secrets or unredacted sensitive payment data.

## Required invariants

1. Merchant-owned records cannot be accessed across tenant boundaries.
2. Proposal money and product version come from server-side product state.
3. Buyer authorization matches the exact proposal and never expands its scope.
4. Merchant acceptance is separate from buyer consent.
5. Transaction money equals the revalidated proposal or execution is rejected.
6. One logical execution maps to at most one unambiguously live provider order.
7. Every valid transaction-state mutation appends an event atomically.
8. `SUCCEEDED` requires verified provider payment/capture truth.
