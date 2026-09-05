from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.catalog_service import ApplicationMerchantCatalogService
from ai_commerce_gateway.application.policy_service import ApplicationMerchantPolicyService
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CreateMerchantCommand,
    CreateProductCommand,
    EvaluateMerchantPolicyCommand,
    Money,
    RecordMerchantDecisionCommand,
    UpdateMerchantPolicyCommand,
)
from ai_commerce_gateway.core.errors import AppError
from ai_commerce_gateway.domain.enums import (
    ActorType,
    MerchantDecisionValue,
    MerchantRole,
    PolicyMode,
    ProposalStatus,
    RecordStatus,
)
from ai_commerce_gateway.infrastructure.database import models as orm
from ai_commerce_gateway.infrastructure.database.merchant_repositories import (
    SqlAlchemyMerchantPolicyRepository,
    SqlAlchemyMerchantRepository,
    SqlAlchemyProductRepository,
)
from ai_commerce_gateway.infrastructure.database.models import Base


@pytest.fixture
def memory_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session_local()
    yield session
    session.close()
    engine.dispose()


def _now() -> datetime:
    return datetime.now(tz=UTC)


def test_merchant_policy_crud_and_modes(memory_session: Session) -> None:
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    pol_repo = SqlAlchemyMerchantPolicyRepository(memory_session)
    cat_svc = ApplicationMerchantCatalogService(m_repo, p_repo)
    pol_svc = ApplicationMerchantPolicyService(pol_repo, memory_session)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id="c1")
    m = cat_svc.create_merchant(
        CreateMerchantCommand(name="Policy Store", idempotency_key="ik1"), sys_actor
    )
    memory_session.commit()

    admin_actor = ActorContext(
        actor_id="u_admin",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id="c2",
    )

    # 1. Initially no policy exists -> 404
    with pytest.raises(AppError) as exc_nf:
        pol_svc.get_policy(m.id, admin_actor)
    assert exc_nf.value.status_code == 404

    # 2. Create initial policy in MANUAL_ALL mode -> version=1
    cmd1 = UpdateMerchantPolicyCommand(
        merchant_id=m.id,
        mode=PolicyMode.MANUAL_ALL,
        auto_accept_max=None,
        expected_version=None,
        idempotency_key="pk1",
    )
    p_view1 = pol_svc.update_policy(cmd1, admin_actor)
    memory_session.commit()

    assert p_view1.merchant_id == m.id
    assert p_view1.mode == PolicyMode.MANUAL_ALL
    assert p_view1.auto_accept_max is None
    assert p_view1.version == 1

    # Read back policy
    p_get = pol_svc.get_policy(m.id, admin_actor)
    assert p_get.id == p_view1.id
    assert p_get.version == 1

    # 3. Update policy to AUTO_BELOW_LIMIT mode -> version=2
    cmd2 = UpdateMerchantPolicyCommand(
        merchant_id=m.id,
        mode=PolicyMode.AUTO_BELOW_LIMIT,
        auto_accept_max=Money(amount_minor=50000, currency="INR"),
        expected_version=1,
        idempotency_key="pk2",
    )
    p_view2 = pol_svc.update_policy(cmd2, admin_actor)
    memory_session.commit()

    assert p_view2.mode == PolicyMode.AUTO_BELOW_LIMIT
    assert p_view2.auto_accept_max is not None
    assert p_view2.auto_accept_max.amount_minor == 50000
    assert p_view2.auto_accept_max.currency == "INR"
    assert p_view2.version == 2

    # 4. Update policy to DENY_ALL mode -> version=3
    cmd3 = UpdateMerchantPolicyCommand(
        merchant_id=m.id,
        mode=PolicyMode.DENY_ALL,
        auto_accept_max=None,
        expected_version=2,
        idempotency_key="pk3",
    )
    p_view3 = pol_svc.update_policy(cmd3, admin_actor)
    memory_session.commit()

    assert p_view3.mode == PolicyMode.DENY_ALL
    assert p_view3.auto_accept_max is None
    assert p_view3.version == 3


def test_merchant_policy_stale_write_and_version_mismatches(
    memory_session: Session,
) -> None:
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    pol_repo = SqlAlchemyMerchantPolicyRepository(memory_session)
    cat_svc = ApplicationMerchantCatalogService(m_repo, p_repo)
    pol_svc = ApplicationMerchantPolicyService(pol_repo, memory_session)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id="c1")
    m = cat_svc.create_merchant(
        CreateMerchantCommand(name="Policy Stale Store", idempotency_key="ik_stale"),
        sys_actor,
    )
    memory_session.commit()

    admin_actor = ActorContext(
        actor_id="u_admin",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id="c2",
    )

    # Initial creation with expected_version > 1 when policy doesn't exist -> 409
    cmd_err = UpdateMerchantPolicyCommand(
        merchant_id=m.id,
        mode=PolicyMode.MANUAL_ALL,
        expected_version=2,
        idempotency_key="pk_err",
    )
    with pytest.raises(AppError) as exc_v:
        pol_svc.update_policy(cmd_err, admin_actor)
    assert exc_v.value.status_code == 409

    # Create initial policy (version 1)
    cmd_init = UpdateMerchantPolicyCommand(
        merchant_id=m.id,
        mode=PolicyMode.MANUAL_ALL,
        expected_version=1,
        idempotency_key="pk_init",
    )
    pol_svc.update_policy(cmd_init, admin_actor)
    memory_session.commit()

    # Update with stale expected_version (e.g. expected 99 vs actual 1) -> 409
    cmd_stale = UpdateMerchantPolicyCommand(
        merchant_id=m.id,
        mode=PolicyMode.DENY_ALL,
        expected_version=99,
        idempotency_key="pk_stale",
    )
    with pytest.raises(AppError) as exc_stale:
        pol_svc.update_policy(cmd_stale, admin_actor)
    assert exc_stale.value.status_code == 409


def test_merchant_policy_role_and_tenant_denials(memory_session: Session) -> None:
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    pol_repo = SqlAlchemyMerchantPolicyRepository(memory_session)
    cat_svc = ApplicationMerchantCatalogService(m_repo, p_repo)
    pol_svc = ApplicationMerchantPolicyService(pol_repo, memory_session)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id="c1")
    m1 = cat_svc.create_merchant(
        CreateMerchantCommand(name="M1 Policy", idempotency_key="ik_m1"), sys_actor
    )
    m2 = cat_svc.create_merchant(
        CreateMerchantCommand(name="M2 Policy", idempotency_key="ik_m2"), sys_actor
    )
    memory_session.commit()

    admin_m1 = ActorContext(
        actor_id="u_admin_m1",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m1.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id="c_adm1",
    )
    editor_m1 = ActorContext(
        actor_id="u_editor_m1",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m1.id]),
        roles=frozenset([MerchantRole.EDITOR]),
        correlation_id="c_ed1",
    )
    viewer_m1 = ActorContext(
        actor_id="u_viewer_m1",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m1.id]),
        roles=frozenset([MerchantRole.VIEWER]),
        correlation_id="c_vi1",
    )
    approver_m1 = ActorContext(
        actor_id="u_approver_m1",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m1.id]),
        roles=frozenset([MerchantRole.APPROVER]),
        correlation_id="c_ap1",
    )
    admin_m2 = ActorContext(
        actor_id="u_admin_m2",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m2.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id="c_adm2",
    )
    buyer_actor = ActorContext(actor_id="buyer1", actor_type=ActorType.BUYER, correlation_id="c_b")

    # Initial policy on M1 by ADMIN
    pol_svc.update_policy(
        UpdateMerchantPolicyCommand(
            merchant_id=m1.id,
            mode=PolicyMode.MANUAL_ALL,
            idempotency_key="pk_init_m1",
        ),
        admin_m1,
    )
    memory_session.commit()

    # 1. Cross-tenant get_policy denied (403)
    with pytest.raises(AppError) as exc_ct_get:
        pol_svc.get_policy(m1.id, admin_m2)
    assert exc_ct_get.value.status_code == 403

    # Buyer cannot get_policy (403)
    with pytest.raises(AppError) as exc_b_get:
        pol_svc.get_policy(m1.id, buyer_actor)
    assert exc_b_get.value.status_code == 403

    # 2. Members with VIEWER, EDITOR, APPROVER can get_policy
    assert pol_svc.get_policy(m1.id, viewer_m1).mode == PolicyMode.MANUAL_ALL
    assert pol_svc.get_policy(m1.id, editor_m1).mode == PolicyMode.MANUAL_ALL
    assert pol_svc.get_policy(m1.id, approver_m1).mode == PolicyMode.MANUAL_ALL

    # 3. Non-admin roles denied update_policy (403)
    cmd_up = UpdateMerchantPolicyCommand(
        merchant_id=m1.id,
        mode=PolicyMode.DENY_ALL,
        idempotency_key="pk_deny_role",
    )
    for non_admin_actor in [editor_m1, viewer_m1, approver_m1, admin_m2, buyer_actor]:
        with pytest.raises(AppError) as exc_role:
            pol_svc.update_policy(cmd_up, non_admin_actor)
        assert exc_role.value.status_code == 403

    # 4. Cross-tenant list_reviews denied (403)
    with pytest.raises(AppError) as exc_ct_rev:
        pol_svc.list_reviews(m1.id, admin_m2)
    assert exc_ct_rev.value.status_code == 403


def test_merchant_review_queue_and_deferred_evaluation(memory_session: Session) -> None:
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    pol_repo = SqlAlchemyMerchantPolicyRepository(memory_session)
    cat_svc = ApplicationMerchantCatalogService(m_repo, p_repo)
    pol_svc = ApplicationMerchantPolicyService(pol_repo, memory_session)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id="c1")
    m = cat_svc.create_merchant(
        CreateMerchantCommand(name="Review Store", idempotency_key="ik_rev"), sys_actor
    )
    admin_actor = ActorContext(
        actor_id="u_admin",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id="c2",
    )

    # Empty reviews
    page = pol_svc.list_reviews(m.id, admin_actor)
    assert len(page.items) == 0
    assert page.next_cursor is None

    # Populate a policy, product, proposal, authorization, and review-required decision
    pol_entity = pol_svc.update_policy(
        UpdateMerchantPolicyCommand(
            merchant_id=m.id,
            mode=PolicyMode.MANUAL_ALL,
            idempotency_key="pk_pol",
        ),
        admin_actor,
    )
    prod = cat_svc.create_product(
        CreateProductCommand(
            merchant_id=m.id,
            sku="SKU-REV",
            title="Item For Review",
            description="Needs manual review",
            price=Money(amount_minor=1000, currency="USD"),
            available_quantity=5,
            idempotency_key="ik_prod",
        ),
        admin_actor,
    )
    memory_session.commit()

    # Insert proposal, authorization, and decision with REVIEW_REQUIRED
    now = _now()
    buyer = orm.Buyer(id="buy_1", external_identity="buyer_ext_1", status=RecordStatus.ACTIVE.value)
    memory_session.add(buyer)

    proposal = orm.PurchaseProposal(
        id="prop_1",
        buyer_id=buyer.id,
        merchant_id=m.id,
        product_id=prod.id,
        product_version=prod.version,
        quantity=1,
        unit_price_minor=1000,
        total_minor=1000,
        currency="USD",
        proposal_hash="hash_123",
        status=ProposalStatus.PROPOSED.value,
        expires_at=now + timedelta(hours=1),
        created_at=now,
    )
    memory_session.add(proposal)

    authorization = orm.BuyerAuthorization(
        id="auth_1",
        buyer_id=buyer.id,
        proposal_id=proposal.id,
        proposal_hash=proposal.proposal_hash,
        merchant_id=m.id,
        product_id=prod.id,
        max_quantity=1,
        max_amount_minor=1000,
        currency="USD",
        authorized_by="buyer_ext_1",
        status="APPROVED",
        expires_at=now + timedelta(hours=1),
        created_at=now,
    )
    memory_session.add(authorization)

    decision = orm.MerchantDecision(
        id="dec_1",
        proposal_id=proposal.id,
        merchant_id=m.id,
        policy_id=pol_entity.id,
        policy_version=pol_entity.version,
        decision=MerchantDecisionValue.REVIEW_REQUIRED.value,
        reason_code="MANUAL_REVIEW_REQUIRED_BY_POLICY",
        decided_by="policy_engine",
        expires_at=now + timedelta(hours=1),
        created_at=now,
    )
    memory_session.add(decision)
    memory_session.commit()

    # list_reviews now returns the review item
    page_with_items = pol_svc.list_reviews(m.id, admin_actor)
    assert len(page_with_items.items) == 1
    review = page_with_items.items[0]
    assert review.proposal.id == proposal.id
    assert review.authorization.id == authorization.id
    assert review.review_reason == "MANUAL_REVIEW_REQUIRED_BY_POLICY"

    # Test list_reviews with session=None
    pol_svc_no_sess = ApplicationMerchantPolicyService(pol_repo, session=None)
    page_no_sess = pol_svc_no_sess.list_reviews(m.id, admin_actor)
    assert len(page_no_sess.items) == 0

    # Add second proposal & decision to test cursor pagination
    proposal2 = orm.PurchaseProposal(
        id="prop_2",
        buyer_id=buyer.id,
        merchant_id=m.id,
        product_id=prod.id,
        product_version=prod.version,
        quantity=1,
        unit_price_minor=2000,
        total_minor=2000,
        currency="USD",
        proposal_hash="hash_456",
        status=ProposalStatus.PROPOSED.value,
        expires_at=now + timedelta(hours=1),
        created_at=now + timedelta(seconds=10),
    )
    memory_session.add(proposal2)

    authorization2 = orm.BuyerAuthorization(
        id="auth_2",
        buyer_id=buyer.id,
        proposal_id=proposal2.id,
        proposal_hash=proposal2.proposal_hash,
        merchant_id=m.id,
        product_id=prod.id,
        max_quantity=1,
        max_amount_minor=2000,
        currency="USD",
        authorized_by="buyer_ext_1",
        status="APPROVED",
        expires_at=now + timedelta(hours=1),
        created_at=now + timedelta(seconds=10),
    )
    memory_session.add(authorization2)

    decision2 = orm.MerchantDecision(
        id="dec_2",
        proposal_id=proposal2.id,
        merchant_id=m.id,
        policy_id=pol_entity.id,
        policy_version=pol_entity.version,
        decision=MerchantDecisionValue.REVIEW_REQUIRED.value,
        reason_code="HIGH_VALUE_REVIEW",
        decided_by="policy_engine",
        expires_at=now + timedelta(hours=1),
        created_at=now + timedelta(seconds=10),
    )
    memory_session.add(decision2)
    memory_session.commit()

    # Paginated review list with cursor
    p_cursor = pol_svc.list_reviews(m.id, admin_actor, cursor="dec_1")
    assert len(p_cursor.items) == 1
    assert p_cursor.items[0].proposal.id == "prop_2"

    # 4. Deferred operations to B2 raise NotImplementedError
    with pytest.raises(NotImplementedError) as exc_ev:
        pol_svc.evaluate(EvaluateMerchantPolicyCommand(proposal_id=proposal.id), admin_actor)
    assert "Transaction Core (B2)" in str(exc_ev.value)

    with pytest.raises(NotImplementedError) as exc_rec:
        pol_svc.record_manual_decision(
            RecordMerchantDecisionCommand(
                proposal_id=proposal.id,
                decision=MerchantDecisionValue.ALLOW,
                reason_code="MANUAL_ALLOW",
                idempotency_key="ik_dec",
            ),
            admin_actor,
        )
    assert "Transaction Core (B2)" in str(exc_rec.value)


def test_update_merchant_policy_command_validation() -> None:
    # 1. AUTO_BELOW_LIMIT requires auto_accept_max
    with pytest.raises(ValueError, match="AUTO_BELOW_LIMIT requires auto_accept_max"):
        UpdateMerchantPolicyCommand(
            merchant_id="mer_1",
            mode=PolicyMode.AUTO_BELOW_LIMIT,
            auto_accept_max=None,
            idempotency_key="ik1",
        )

    # 2. MANUAL_ALL cannot have auto_accept_max
    with pytest.raises(ValueError, match="auto_accept_max is valid only for AUTO_BELOW_LIMIT"):
        UpdateMerchantPolicyCommand(
            merchant_id="mer_1",
            mode=PolicyMode.MANUAL_ALL,
            auto_accept_max=Money(amount_minor=100, currency="USD"),
            idempotency_key="ik2",
        )
