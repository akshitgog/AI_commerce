from pydantic import BaseModel, ConfigDict, Field


class InvocationContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    correlation_id: str
    idempotency_key: str | None = None
    request_id: str | None = None


class SearchCatalogRequest(BaseModel):
    merchant_id: str
    query: str | None = None
    category: str | None = None
    min_price_minor: int | None = Field(default=None, ge=0)
    max_price_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class GetProductRequest(BaseModel):
    product_id: str


class CreatePurchaseProposalRequest(BaseModel):
    merchant_id: str
    product_id: str
    quantity: int = Field(default=1, ge=1)


class RequestAuthorizationRequest(BaseModel):
    proposal_id: str


class ExecuteTransactionRequest(BaseModel):
    # Depending on how the buyer interacts, they may just provide the proposal_id
    # and the adapter will create the transaction and execute it.
    proposal_id: str


class GetTransactionStatusRequest(BaseModel):
    transaction_id: str


class GetTransactionAuditRequest(BaseModel):
    transaction_id: str
    cursor: str | None = None
