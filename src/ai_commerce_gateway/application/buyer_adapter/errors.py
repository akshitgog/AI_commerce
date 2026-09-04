from ai_commerce_gateway.contracts.models import ErrorBody, ErrorEnvelope
from ai_commerce_gateway.core.errors import AppError, ErrorCode


def map_app_error(exc: AppError, correlation_id: str) -> ErrorEnvelope:
    """Maps an internal application exception to a safe public ErrorEnvelope."""
    return ErrorEnvelope(
        error=ErrorBody(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
        correlation_id=correlation_id,
    )


def map_unknown_error(exc: Exception, correlation_id: str) -> ErrorEnvelope:
    """Maps an unknown exception to a safe public ErrorEnvelope, hiding internal details."""
    return ErrorEnvelope(
        error=ErrorBody(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred.",
            details={},
        ),
        correlation_id=correlation_id,
    )
