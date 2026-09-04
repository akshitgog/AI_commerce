
## D-008 — Add merchant_id to CatalogService.get_product (A3 Contract Change)

Status: ACTIVE
Date: 2026-09-04
Branch: feature/merchant-catalog
Owner: Project team

### Decision

Update the frozen CatalogService.get_product contract to require merchant_id:
def get_product(self, merchant_id: str, product_id: str, actor: ActorContext) -> ProductView: ...

### Why

Invariant 19 mandates that all database queries be tenant-scoped at the SQL level (using merchant_id). Buyer contexts do not inherently possess a list of merchant_ids to iterate over, making it impossible to perform a tenant-scoped lookup using only product_id. The client must provide the merchant_id when reading a product.

### Alternatives Considered

- Using an unscoped DB query (explicitly rejected in Phase A2 review).
- Iterating over all merchants (unscalable and impossible).

### Consequences

Workstream C (Buyer/MCP) must supply the merchant_id when fetching a product (this data is already available via the search result). MerchantCatalogService.get_product remains unchanged as it can safely iterate the actor's authorized merchant_ids.

### Evidence / Trigger

Phase A3 escalation during implementation of buyer-safe reads.

### Supersedes

None.
