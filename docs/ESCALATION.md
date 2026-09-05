# Escalation: Shared Contract Change Required for Phase A3

**Contract that needs changing:**
CatalogService.get_product in src/ai_commerce_gateway/contracts/services.py
Currently: def get_product(self, product_id: str, actor: ActorContext) -> ProductView: ...
Proposed: def get_product(self, merchant_id: str, product_id: str, actor: ActorContext) -> ProductView: ...

**Reason:**
The Phase A2 review strictly enforced Invariant 19 (Tenant Isolation), rejecting get_by_id_unscoped and requiring that ALL repository queries be tenant-scoped at the SQL level (meaning they must include merchant_id). 
However, the frozen CatalogService.get_product contract only receives product_id. Since a buyer's ActorContext does not contain merchant_ids to iterate over, it is mathematically impossible to call ProductRepository.get_by_id(merchant_id, product_id) without knowing the merchant_id. We are forbidden from bypassing the tenant scope at the DB level, which means the client MUST supply the merchant_id when querying for a product.

**Affected workstreams:**
- 02 (Catalog & Merchant Domain): Implementing the service.
- 05 (Buyer / MCP adapters): Calling the service.

**Proposed change:**
Modify the CatalogService Protocol in contracts/services.py:
`python
    def get_product(self, merchant_id: str, product_id: str, actor: ActorContext) -> ProductView: ...
`

**Compatibility impact:**
Any buyer adapters (Dashboard/MCP) calling CatalogService.get_product will need to pass the merchant_id alongside the product_id (which they will naturally have from the CatalogSearchResult). 
