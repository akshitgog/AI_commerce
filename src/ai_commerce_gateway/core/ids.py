from secrets import token_urlsafe
from typing import Final, Literal

EntityPrefix = Literal[
    "mer",
    "musr",
    "prod",
    "pimg",
    "pol",
    "buy",
    "prop",
    "auth",
    "mdec",
    "txn",
    "idem",
    "pay",
    "pwh",
    "tevt",
]
_TOKEN_BYTES: Final = 16


def new_id(prefix: EntityPrefix) -> str:
    """Return an opaque, type-prefixed identifier safe for URLs and logs."""
    return f"{prefix}_{token_urlsafe(_TOKEN_BYTES)}"
