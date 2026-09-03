"""Provisional provider boundary.

This module is intentionally not re-exported from ``contracts``. Its result semantics remain
provisional until the Razorpay Test Mode truth spike; it never decides platform transaction state.
"""

from typing import Protocol

from ai_commerce_gateway.contracts.models import (
    CreateProviderOrderCommand,
    HandleWebhookCommand,
    ProviderLookupCommand,
    ProviderObservation,
    VerifyCheckoutCommand,
)


class ProviderService(Protocol):
    def create_order(self, command: CreateProviderOrderCommand) -> ProviderObservation: ...
    def verify_checkout(self, command: VerifyCheckoutCommand) -> ProviderObservation: ...
    def handle_webhook(self, command: HandleWebhookCommand) -> ProviderObservation: ...
    def lookup_order(self, command: ProviderLookupCommand) -> ProviderObservation: ...
    def lookup_payment(self, command: ProviderLookupCommand) -> ProviderObservation: ...
