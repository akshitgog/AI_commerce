"""Unit tests for the buyer application composition root.

Verifies the P0-1 requirements:
- the app factory has a single explicit composition seam;
- there is no stub fallback anywhere in production composition;
- in-process composition fails fast with actionable guidance on a
  single-lane checkout;
- remote composition requires configured trusted service base URLs;
- the human buyer approval verifier binds approval to the authenticated
  buyer session.
"""

from types import SimpleNamespace

import pytest
from pydantic import SecretStr
from pytest import MonkeyPatch

import ai_commerce_gateway.infrastructure.database.session as session_module
from ai_commerce_gateway.api import composition
from ai_commerce_gateway.api.composition import (
    BuyerServiceBundle,
    SessionBuyerApprovalVerifier,
    compose_default_buyer_services_factory,
    compose_in_process_buyer_services_factory,
    compose_remote_buyer_services_factory,
    static_bundle_factory,
)
from ai_commerce_gateway.contracts.models import ActorContext
from ai_commerce_gateway.core.config import Settings
from ai_commerce_gateway.core.errors import AppError
from ai_commerce_gateway.domain.enums import ActorType
from tests.unit.application.buyer_adapter.fakes import (
    FakeAuthorizationService,
    FakeCatalogService,
    FakeProposalService,
    FakeTransactionService,
)


def _fake_bundle() -> BuyerServiceBundle:
    return BuyerServiceBundle(
        catalog=FakeCatalogService(),
        proposal=FakeProposalService(),
        auth=FakeAuthorizationService(),
        transaction=FakeTransactionService(),
    )


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "razorpay_key_id": "rzp_test_key",
        "razorpay_key_secret": SecretStr("rzp_test_secret"),
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_static_bundle_factory_yields_bundle_each_call() -> None:
    factory = static_bundle_factory(_fake_bundle())
    with factory() as bundle_one:
        assert isinstance(bundle_one, BuyerServiceBundle)
    with factory() as bundle_two:
        assert bundle_two is bundle_one


def test_remote_factory_requires_base_urls() -> None:
    with pytest.raises(RuntimeError, match="catalog_base_url"):
        compose_remote_buyer_services_factory(_settings(buyer_services_mode="remote"))


def test_default_factory_selects_remote_mode_and_validates() -> None:
    with pytest.raises(RuntimeError, match="remote"):
        compose_default_buyer_services_factory(_settings(buyer_services_mode="remote"))


def test_default_factory_rejects_unknown_mode() -> None:
    settings = _settings()
    settings.buyer_services_mode = "nonsense"  # type: ignore[assignment]
    with pytest.raises(RuntimeError, match="Unknown buyer_services.mode"):
        compose_default_buyer_services_factory(settings)


def test_in_process_factory_fails_fast_without_integrated_modules(
    monkeypatch: MonkeyPatch,
) -> None:
    def _missing() -> object:
        raise ImportError("No module named 'ai_commerce_gateway.application.proposal_gates'")

    monkeypatch.setattr(composition, "_import_integrated_services", _missing)
    with pytest.raises(RuntimeError) as excinfo:
        compose_in_process_buyer_services_factory(_settings())
    message = str(excinfo.value)
    assert "integrated repository" in message
    assert "remote" in message
    assert "never" in message  # no stub fallback ever


def test_in_process_factory_requires_provider_credentials(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        composition,
        "_import_integrated_services",
        lambda: SimpleNamespace(),
    )
    with pytest.raises(RuntimeError, match="Razorpay"):
        compose_in_process_buyer_services_factory(
            _settings(razorpay_key_id=None, razorpay_key_secret=None)
        )


def test_in_process_factory_composes_integrated_services(
    monkeypatch: MonkeyPatch,
) -> None:
    """With the integrated modules present, composition builds the factory."""

    class FakeProductRepo:
        def __init__(self, session: object) -> None:
            self.session = session

    class FakeImageRepo:
        def __init__(self, session: object) -> None:
            self.session = session

    class FakeGateRepo:
        def __init__(self, session: object) -> None:
            self.session = session

    class FakeCatalogService:
        def __init__(self, products: object, images: object) -> None:
            self.products = products
            self.images = images

    class FakeProposalService:
        def __init__(self, gates: object) -> None:
            self.gates = gates

    class FakeAuthorizationService:
        def __init__(self, gates: object, verifier: object) -> None:
            self.gates = gates
            self.verifier = verifier

    class FakeMerchantGateService:
        def __init__(self, gates: object) -> None:
            self.gates = gates

    fake_session = SimpleNamespace(name="fake-session")
    fake_txn = SimpleNamespace(request_session=fake_session)

    class FakeTransactionRoot:
        session_factory = SimpleNamespace(name="fake-session-factory")
        provider_service = SimpleNamespace(name="fake-provider")

        def for_request(self, request_session: object) -> object:
            assert request_session is fake_session
            return SimpleNamespace(transactions=fake_txn)

    fake_root = FakeTransactionRoot()

    monkeypatch.setattr(
        composition,
        "_import_integrated_services",
        lambda: SimpleNamespace(
            ApplicationCatalogService=FakeCatalogService,
            TransactionCompositionRoot=SimpleNamespace(from_settings=lambda s: fake_root),
            AuthorizationApplicationService=FakeAuthorizationService,
            MerchantGateApplicationService=FakeMerchantGateService,
            ProposalApplicationService=FakeProposalService,
            SqlAlchemyProductImageRepository=FakeImageRepo,
            SqlAlchemyProductRepository=FakeProductRepo,
            SqlAlchemyProposalGateRepository=FakeGateRepo,
        ),
    )
    monkeypatch.setattr(
        session_module,
        "session_scope",
        lambda factory: _null_context(fake_session),
    )

    factory = compose_in_process_buyer_services_factory(_settings())
    assert callable(factory)
    assert factory.transaction_root is fake_root  # type: ignore[attr-defined]
    with factory() as bundle:
        assert isinstance(bundle.catalog, FakeCatalogService)
        assert isinstance(bundle.proposal, FakeProposalService)
        assert isinstance(bundle.auth, FakeAuthorizationService)
        assert isinstance(bundle.auth.verifier, SessionBuyerApprovalVerifier)
        assert isinstance(bundle.merchant_gates, FakeMerchantGateService)
        assert bundle.transaction is fake_txn


class _null_context:
    def __init__(self, value: object) -> None:
        self.value = value

    def __enter__(self) -> object:
        return self.value

    def __exit__(self, *args: object) -> None:
        return None


def _buyer_actor(actor_id: str = "buyer_123") -> ActorContext:
    return ActorContext(
        actor_id=actor_id,
        actor_type=ActorType.BUYER,
        correlation_id="corr_test",
    )


def test_approval_verifier_accepts_owning_buyer() -> None:
    verifier = SessionBuyerApprovalVerifier()
    assert verifier.verify(actor=_buyer_actor("buyer_123"), buyer_id="buyer_123") == (
        "buyer_123"
    )


def test_approval_verifier_rejects_other_buyer() -> None:
    verifier = SessionBuyerApprovalVerifier()
    with pytest.raises(AppError) as excinfo:
        verifier.verify(actor=_buyer_actor("buyer_999"), buyer_id="buyer_123")
    assert excinfo.value.status_code == 403


def test_approval_verifier_rejects_non_buyer_actor() -> None:
    verifier = SessionBuyerApprovalVerifier()
    merchant_actor = ActorContext(
        actor_id="usr_1",
        actor_type=ActorType.MERCHANT_USER,
        correlation_id="corr_test",
    )
    with pytest.raises(AppError) as excinfo:
        verifier.verify(actor=merchant_actor, buyer_id="buyer_123")
    assert excinfo.value.status_code == 403
