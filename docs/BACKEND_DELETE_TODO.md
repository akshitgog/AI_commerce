# Backend Product Deletion - Implementation Guide

## Current State
- Product deletion is **frontend-only** (just removes from local state)
- No backend `DELETE /products/{id}` endpoint exists
- Only product **images** can be deleted via backend API

## Why Not Implemented Now
Adding full product deletion requires:
1. New `DeleteProductCommand` contract model
2. `delete_product()` method in catalog service
3. Business logic to handle:
   - Can only delete DRAFT/UNPUBLISHED products
   - Cleanup of associated product images
   - Audit trail for deletion
4. API endpoint with proper authorization
5. Risk of breaking existing transaction/review references

## Safe Implementation Steps (TODO)

### 1. Add Contract Model
File: `src/ai_commerce_gateway/contracts/models.py`

```python
class DeleteProductCommand(ContractModel):
    merchant_id: str
    product_id: str
    expected_version: int = Field(ge=1, strict=True)
    idempotency_key: str = Field(min_length=1, max_length=255)
```

### 2. Add Service Method
File: `src/ai_commerce_gateway/application/catalog_service.py`

```python
def delete_product(self, command: DeleteProductCommand, actor: ActorContext) -> None:
    """Delete a DRAFT product. Only unpublished products can be deleted."""
    product = self._repo.get_product(command.merchant_id, command.product_id)
    
    if not product:
        raise NotFoundError(...)
    
    if product.status != ProductStatus.UNPUBLISHED:
        raise BusinessError("Cannot delete published products. Unpublish first.")
    
    # Delete associated images first
    for image in product.images:
        self._storage_svc.delete_product_image(storage_path=image.storage_path)
    
    # Delete product
    self._repo.delete_product(command.merchant_id, command.product_id)
    
    # Audit trail
    self._audit_writer.record_event(...)
```

### 3. Add API Endpoint
File: `src/ai_commerce_gateway/api/merchant/router.py`

```python
@router.delete("/{merchant_id}/products/{product_id}", status_code=204)
def delete_product(
    merchant_id: str,
    product_id: str,
    expected_version: int = Header(..., alias="X-Expected-Version"),
    idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    catalog: CatalogSvc,
    actor: MerchantActor,
) -> None:
    """Delete a DRAFT product. Published products cannot be deleted."""
    _require_roles(actor, _CATALOG_WRITE_ROLES)
    
    command = DeleteProductCommand(
        merchant_id=merchant_id,
        product_id=product_id,
        expected_version=expected_version,
        idempotency_key=idempotency_key,
    )
    catalog.delete_product(command, actor)
```

### 4. Update Frontend Service
File: `frontend/src/lib/api/client.ts`

```typescript
async deleteProduct(merchantId: string, productId: string, version: number): Promise<void> {
  await this.request(`/merchants/${merchantId}/products/${productId}`, {
    method: "DELETE",
    headers: {
      ...this.merchantHeaders(),
      "X-Expected-Version": version.toString(),
      "X-Idempotency-Key": crypto.randomUUID(),
    },
  });
}
```

### 5. Wire Frontend
File: `frontend/src/lib/services/store.ts`

```typescript
async deleteDraft(productId) {
  const product = state.products.find(p => p.id === productId);
  if (!product) return;
  
  await apiClient.deleteProduct("mer_demo", productId, product.version);
  setState({ products: state.products.filter(p => p.id !== productId) });
}
```

## Current Workaround
- Frontend shows delete button only for DRAFT products
- Deletion removes from local state only
- User must refresh page to see it's not actually deleted on backend
- Better UX: Show warning "Delete only removes from view. Refresh to see actual products."

## Recommendation
Implement full backend deletion OR remove delete button entirely and explain products cannot be deleted, only unpublished.
