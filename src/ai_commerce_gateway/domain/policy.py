"""MerchantPolicy domain entity.

Data/domain foundation only; policy *evaluation* logic belongs to the
Transaction Core workstream (B2).  This entity represents persisted policy
configuration owned by the merchant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_commerce_gateway.domain.enums import PolicyMode, RecordStatus
from ai_commerce_gateway.domain.product import MoneyMinor


@dataclass(frozen=True, slots=True)
class MerchantPolicyEntity:
    """Read-only snapshot of a MerchantPolicy record.

    Version is included so that policy evaluation in B2 can capture the
    exact policy version at the time of a merchant decision.
    """

    id: str
    merchant_id: str
    mode: PolicyMode
    # auto_accept_max is only meaningful for AUTO_BELOW_LIMIT mode.
    auto_accept_max: MoneyMinor | None
    version: int  # >= 1
    status: RecordStatus
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("policy version must be >= 1")
        if self.mode is PolicyMode.AUTO_BELOW_LIMIT and self.auto_accept_max is None:
            raise ValueError("AUTO_BELOW_LIMIT requires auto_accept_max")
        if self.mode is not PolicyMode.AUTO_BELOW_LIMIT and self.auto_accept_max is not None:
            raise ValueError("auto_accept_max is only valid for AUTO_BELOW_LIMIT mode")

    def belongs_to(self, merchant_id: str) -> bool:
        return self.merchant_id == merchant_id
