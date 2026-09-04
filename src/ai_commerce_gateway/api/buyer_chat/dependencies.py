"""FastAPI dependencies for buyer chat routes.

The transport layer is responsible for generating Invocation Context from
request headers. The AI/tool layer never sees idempotency keys or correlation IDs.
Buyer identity is derived exclusively from the server-trusted session set by
the application middleware.
"""

from typing import cast
from uuid import uuid4

from fastapi import Depends, Header, Request

from ai_commerce_gateway.application.buyer_adapter.schemas import InvocationContext
from ai_commerce_gateway.contracts.models import ActorContext
from ai_commerce_gateway.core.errors import AppError, ErrorCode
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
    """Derive the buyer actor exclusively from the server-trusted session.

    The session middleware populates ``request.state.actor_context`` only
    after verifying the HMAC session token. Identity is never taken from
    request bodies, query parameters or arbitrary headers.
    """
    actor_context = getattr(request.state, "actor_context", None)
    if not actor_context or actor_context.actor_type != ActorType.BUYER:
        raise AppError(
            ErrorCode.UNAUTHENTICATED,
            "A valid buyer session is required.",
            status_code=401,
        )
    return cast(ActorContext, actor_context)
