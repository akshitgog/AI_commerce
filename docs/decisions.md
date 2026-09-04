# decisions.md — Architectural and Product Decisions

## D-008 — Add merchant_id to CatalogService.get_product (A3 Contract Change)

Status: APPROVED
Date: 2026-09-04
Branch: phase/a3-catalog-publication
Owner: Human Integrator Approval

### Approval
Integrator / human approval granted:
"APPROVED — Shared Contract Change A3: Approve changing CatalogService.get_product to get_product(merchant_id: str, product_id: str, actor: ActorContext) -> ProductView. Rationale: resolves conflict between frozen contract and Invariant 19. No unscoped repository lookup may be introduced. Requirements: merchant_id is a lookup/tenant scope, not authentication. Repository lookup must remain SQL-scoped by merchant_id. Buyer reads must enforce publication/visibility rules. Merchant/private operations must verify actor-to-merchant authorization. Do not restore get_by_id_unscoped. Update the canonical contract and its contract tests. Update all current call sites and mocks/fixtures. Record the approved decision in the project decision/change documentation. Notify Workstream C that get_product now requires merchant_id. Do not make unrelated shared-contract changes."

### Decision

Update the frozen CatalogService.get_product contract to require merchant_id:
`def get_product(self, merchant_id: str, product_id: str, actor: ActorContext) -> ProductView: ...`

MerchantCatalogService.get_product remains strictly unchanged as `def get_product(self, product_id: str, actor: ActorContext) -> ProductView: ...` since merchant actors possess explicit tenant context (`actor.merchant_ids`).

### Why

Invariant 19 mandates that all database queries be tenant-scoped at the SQL level (using merchant_id). Buyer contexts do not inherently possess a list of merchant_ids to iterate over, making it impossible to perform a tenant-scoped lookup using only product_id. The client must provide the merchant_id when reading a product.

### Alternatives Considered

- Using an unscoped DB query (explicitly rejected in Phase A2 review as violating SQL-level tenant isolation).
- Iterating over all merchants (unscalable and impossible).

### Consequences

Workstream C (Buyer/MCP) must supply the merchant_id when fetching a product (this data is already available via the search result). MerchantCatalogService.get_product remains unchanged as it safely scopes to the actor's authorized merchant_ids.

### Evidence / Trigger

Phase A3 escalation during implementation of buyer-safe reads. Gate approved by human integrator.

### Supersedes

None.
