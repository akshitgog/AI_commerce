# Shared Contracts

This file records only the cross-workstream contract freeze. Architecture and business rationale remain in the canonical project documents.

## Frozen

| Contract group | Owner | Consumers |
|---|---|---|
| Money, IDs, errors, actor and merchant-role vocabulary | Integrator | A, B, C |
| Published product/catalog reads | Workstream 02 | A, B, C |
| Merchant, product, image and policy write contracts | Workstream 02 | A |
| Proposal and next-gate contracts | Workstream 03 | B, C |
| Buyer authorization and merchant decision contracts | Workstream 03 | A, B, C |
| Transaction service/read/audit contracts and canonical states | Workstream 03 | A, B, C |
| Product-image storage port | Workstream 06 with Workstream 02 | A |

Frozen means another branch may implement against the contract. It does not mean the behavior is already implemented or proven.

The required merchant MCP extension is additive at the adapter/auth boundary. It reuses the frozen
`MerchantCatalogService`, command DTOs, `ActorContext` and existing `IdempotencyRecord`. Transport
metadata supplies the command idempotency key, authenticated server context supplies `merchant_id`,
and the publication confirmation token is verified and stripped before command construction. No
frozen DTO, enum, service method or persistence table changes for A7/C7.

## Provisional

### Provider contract resolution

The provider method and M0 DTO shapes remain unchanged. B4 resolved `provider.create_order`: one
non-retried create call returns order evidence only, and a `created` order can advance the platform
no further than `PAYMENT_PENDING`. B5 resolves checkout, webhook and lookup semantics inside
Workstream 04. Webhook event identity remains HTTP transport metadata. B5-owned evidence adds
provider amount/currency internally so the transaction authority can compare it with trusted
transaction money without expanding the frozen `ProviderObservation` DTO.

A valid checkout signature or webhook is authenticity evidence, not success by itself. The
platform requires correlated provider payment `captured`, provider order `paid`, exact money and
stored attempt identity before the canonical state machine may enter `SUCCEEDED`. B6 remains the
owner of uncertain-outcome reconciliation.

### Other provisional behavior

The product-image URL policy remains provisional: `StoredImage.public_url` is optional until public versus signed delivery is selected.

## Change process

1. Document the reason and affected consumers.
2. Obtain integrator approval.
3. Update canonical API/data documentation.
4. Update contract tests and implementation together.
5. Notify every affected workstream before merging.

No workstream may silently change a frozen contract.
