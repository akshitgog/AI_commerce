"""FastAPI dependencies for buyer chat routes.

The transport layer is responsible for generating Invocation Context from
request headers. The AI/tool layer never sees idempotency keys or correlation IDs.
"""

from typing import cast
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Request

from ai_commerce_gateway.application.buyer_adapter.schemas import InvocationContext
from ai_commerce_gateway.contracts.models import ActorContext
from ai_commerce_gateway.domain.enums import ActorType


def get_correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", f"corr_{uuid4().hex}")


def get_invocation_context(
    correlation_id: str = Depends(get_correlation_id),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> InvocationContext:
    """Extract InvocationContext from HTTP headers.

    The transport, not the AI, provides these values.
    idempotency_key comes from the `Idempotency-Key` header for mutating operations.
    """
    return InvocationContext(
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        request_id=f"req_{uuid4().hex}",
    )


def get_buyer_actor(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
) -> ActorContext:
    """Derive buyer actor from server-validated session/token.

    In C2, actor_id comes from a header for demo purposes.
    C3/C6 will replace with real authentication middleware.
    The actor is never derived from body fields.
    """
    actor_context = getattr(request.state, "actor_context", None)
    if not actor_context or actor_context.actor_type != ActorType.BUYER:
        raise HTTPException(status_code=401, detail="Unauthorized: Buyer session required")
    return cast(ActorContext, actor_context)
