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

## Provisional

The provider port, provider commands and provider observations are provisional until the Razorpay Test Mode truth spike. They are owned by Workstream 04 and consumed only by Workstream 03. Provider observations never decide platform `SUCCEEDED`.

The product-image URL policy remains provisional: `StoredImage.public_url` is optional until public versus signed delivery is selected.

## Change process

1. Document the reason and affected consumers.
2. Obtain integrator approval.
3. Update canonical API/data documentation.
4. Update contract tests and implementation together.
5. Notify every affected workstream before merging.

No workstream may silently change a frozen contract.
