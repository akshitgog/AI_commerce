"""Unit tests for product storage services and image metadata lifecycle."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.buyer_catalog_service import ApplicationCatalogService
from ai_commerce_gateway.application.catalog_service import ApplicationMerchantCatalogService
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    AddProductImageCommand,
    CatalogSearchQuery,
    CreateMerchantCommand,
    CreateProductCommand,
    DeleteProductImageCommand,
    Money,
    SetProductPublicationCommand,
    UpdateProductCommand,
)
from ai_commerce_gateway.core.errors import AppError
from ai_commerce_gateway.domain.enums import ActorType, MerchantRole
from ai_commerce_gateway.infrastructure.database.merchant_repositories import (
    SqlAlchemyMerchantRepository,
    SqlAlchemyProductImageRepository,
    SqlAlchemyProductRepository,
)
from ai_commerce_gateway.infrastructure.database.models import Base
from ai_commerce_gateway.storage.local import LocalStorageService
from ai_commerce_gateway.storage.memory import InMemoryStorageService


@pytest.fixture
def memory_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    session = session_factory()
    yield session
    session.close()
    engine.dispose()


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _setup_merchant_and_product(session: Session):
    m_repo = SqlAlchemyMerchantRepository(session)
    p_repo = SqlAlchemyProductRepository(session)
    img_repo = SqlAlchemyProductImageRepository(session)
    storage = InMemoryStorageService(base_url="https://cdn.example.com")
    catalog_svc = ApplicationMerchantCatalogService(
        merchant_repo=m_repo,
        product_repo=p_repo,
        image_repo=img_repo,
        storage_svc=storage,
    )

    sys_actor = ActorContext(
        actor_id="sys1",
        actor_type=ActorType.SYSTEM,
        correlation_id="cor1",
    )
    m_view = catalog_svc.create_merchant(
        CreateMerchantCommand(name="Acme Corp", idempotency_key="ik_m1"),
        actor=sys_actor,
    )
    session.commit()

    admin_actor = ActorContext(
        actor_id="admin1",
        actor_type=ActorType.MERCHANT_USER,
        correlation_id="cor2",
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.ADMIN]),
    )
    p_view = catalog_svc.create_product(
        CreateProductCommand(
            merchant_id=m_view.id,
            sku="SKU-IMAGE-TEST",
            title="Widget with Images",
            description="Testing image lifecycle",
            price=Money(amount_minor=2500, currency="USD"),
            available_quantity=10,
            idempotency_key="ik_p1",
        ),
        actor=admin_actor,
    )
    session.commit()

    return m_repo, p_repo, img_repo, storage, catalog_svc, m_view, p_view, admin_actor


# ---------------------------------------------------------------------------
# Storage Adapters Unit Tests
# ---------------------------------------------------------------------------


def test_in_memory_storage_service():
    storage = InMemoryStorageService(base_url="https://media.test.com")
    content = b"fake-image-bytes-jpeg"
    stored = storage.upload_product_image(
        merchant_id="mer_1",
        product_id="prod_1",
        filename="photo 1/test.jpg",
        content_type="image/jpeg",
        content=content,
    )

    assert "merchants/mer_1/products/prod_1/" in stored.storage_path
    assert stored.public_url == f"https://media.test.com/{stored.storage_path}"
    assert storage.exists(stored.storage_path) is True
    assert storage.get_content(stored.storage_path) == content

    # Delete
    storage.delete_product_image(storage_path=stored.storage_path)
    assert storage.exists(stored.storage_path) is False
    assert storage.get_content(stored.storage_path) is None


def test_local_storage_service(tmp_path: Path):
    storage = LocalStorageService(base_directory=tmp_path, base_url="/media")
    content = b"test-png-bytes"
    stored = storage.upload_product_image(
        merchant_id="mer_2",
        product_id="prod_2",
        filename="banner.png",
        content_type="image/png",
        content=content,
    )

    assert stored.storage_path.startswith("merchants/mer_2/products/prod_2/")
    assert stored.public_url == f"/media/{stored.storage_path}"
    assert storage.exists(stored.storage_path) is True

    disk_path = tmp_path / stored.storage_path
    assert disk_path.is_file()
    assert disk_path.read_bytes() == content

    # Delete
    storage.delete_product_image(storage_path=stored.storage_path)
    assert storage.exists(stored.storage_path) is False
    assert not disk_path.exists()

    # Deleting non-existent does not raise
    storage.delete_product_image(storage_path="nonexistent/path.png")


# ---------------------------------------------------------------------------
# ApplicationMerchantCatalogService Image Operations
# ---------------------------------------------------------------------------


def test_add_product_images_happy_path(memory_session: Session):
    (
        _,
        _,
        img_repo,
        storage,
        catalog_svc,
        m_view,
        p_view,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    # 1. Add first image (sort_order 0)
    img1 = catalog_svc.add_product_image(
        AddProductImageCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            filename="front.jpg",
            content_type="image/jpeg",
            content=b"front-view-jpeg-bytes",
            alt_text="Front View",
            sort_order=0,
            idempotency_key="ik_img1",
        ),
        actor=admin_actor,
    )
    memory_session.commit()

    assert img1.sort_order == 0
    assert img1.alt_text == "Front View"
    assert "https://cdn.example.com/" in img1.url

    # 2. Add second image (sort_order 1)
    img2 = catalog_svc.add_product_image(
        AddProductImageCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            filename="back.png",
            content_type="image/png",
            content=b"back-view-png-bytes",
            alt_text="Back View",
            sort_order=1,
            idempotency_key="ik_img2",
        ),
        actor=admin_actor,
    )
    memory_session.commit()

    # 3. Add third image (sort_order 2)
    img3 = catalog_svc.add_product_image(
        AddProductImageCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            filename="detail.webp",
            content_type="image/webp",
            content=b"detail-webp-bytes",
            alt_text="Detail View",
            sort_order=2,
            idempotency_key="ik_img3",
        ),
        actor=admin_actor,
    )
    memory_session.commit()

    assert img_repo.count_for_product(m_view.id, p_view.id) == 3

    # Product view should have 3 ordered images
    fetched_p = catalog_svc.get_product(p_view.id, actor=admin_actor)
    assert len(fetched_p.images) == 3
    assert fetched_p.images[0].id == img1.id
    assert fetched_p.images[0].sort_order == 0
    assert fetched_p.images[1].id == img2.id
    assert fetched_p.images[1].sort_order == 1
    assert fetched_p.images[2].id == img3.id
    assert fetched_p.images[2].sort_order == 2

    # Verify storage contains 3 items
    assert len(storage._files) == 3


def test_add_product_image_max_3_limit(memory_session: Session):
    (
        _,
        _,
        _,
        _,
        catalog_svc,
        m_view,
        p_view,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    for i in range(3):
        catalog_svc.add_product_image(
            AddProductImageCommand(
                merchant_id=m_view.id,
                product_id=p_view.id,
                filename=f"img_{i}.jpg",
                content_type="image/jpeg",
                content=f"bytes_{i}".encode(),
                sort_order=i,
                idempotency_key=f"ik_{i}",
            ),
            actor=admin_actor,
        )
    memory_session.commit()

    # Attempt 4th image (even if sort_order were somehow valid, count limit stops it)
    with pytest.raises(AppError) as exc_info:
        catalog_svc.add_product_image(
            AddProductImageCommand(
                merchant_id=m_view.id,
                product_id=p_view.id,
                filename="extra.jpg",
                content_type="image/jpeg",
                content=b"overflow",
                sort_order=2,
                idempotency_key="ik_extra",
            ),
            actor=admin_actor,
        )
    assert exc_info.value.status_code == 400
    assert "Maximum of 3 images allowed" in str(exc_info.value)


def test_add_product_image_duplicate_sort_order(memory_session: Session):
    (
        _,
        _,
        _,
        _,
        catalog_svc,
        m_view,
        p_view,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    catalog_svc.add_product_image(
        AddProductImageCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            filename="first.jpg",
            content_type="image/jpeg",
            content=b"first-bytes",
            sort_order=0,
            idempotency_key="ik_1",
        ),
        actor=admin_actor,
    )
    memory_session.commit()

    # Adding duplicate sort_order 0 should raise 409
    with pytest.raises(AppError) as exc_info:
        catalog_svc.add_product_image(
            AddProductImageCommand(
                merchant_id=m_view.id,
                product_id=p_view.id,
                filename="second.jpg",
                content_type="image/jpeg",
                content=b"second-bytes",
                sort_order=0,
                idempotency_key="ik_2",
            ),
            actor=admin_actor,
        )
    assert exc_info.value.status_code == 409
    assert "already exists" in str(exc_info.value)


def test_add_product_image_content_type_validation(memory_session: Session):
    (
        _,
        _,
        _,
        _,
        catalog_svc,
        m_view,
        p_view,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    for invalid_type in ["application/pdf", "text/plain", "video/mp4", "image/bmp"]:
        with pytest.raises(AppError) as exc_info:
            catalog_svc.add_product_image(
                AddProductImageCommand(
                    merchant_id=m_view.id,
                    product_id=p_view.id,
                    filename="bad.file",
                    content_type=invalid_type,
                    content=b"some-bytes",
                    sort_order=0,
                    idempotency_key=f"ik_{invalid_type}",
                ),
                actor=admin_actor,
            )
        assert exc_info.value.status_code == 400
        assert "Unsupported content type" in str(exc_info.value)


def test_add_product_image_size_validation(memory_session: Session):
    (
        _,
        _,
        _,
        _,
        catalog_svc,
        m_view,
        p_view,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    # Empty content
    with pytest.raises(AppError) as exc_info:
        catalog_svc.add_product_image(
            AddProductImageCommand(
                merchant_id=m_view.id,
                product_id=p_view.id,
                filename="empty.jpg",
                content_type="image/jpeg",
                content=b"",
                sort_order=0,
                idempotency_key="ik_empty",
            ),
            actor=admin_actor,
        )
    assert exc_info.value.status_code == 400
    assert "cannot be empty" in str(exc_info.value)

    # Content exceeding 5MB
    large_content = b"x" * (5 * 1024 * 1024 + 1)
    with pytest.raises(AppError) as exc_info:
        catalog_svc.add_product_image(
            AddProductImageCommand(
                merchant_id=m_view.id,
                product_id=p_view.id,
                filename="huge.jpg",
                content_type="image/jpeg",
                content=large_content,
                sort_order=0,
                idempotency_key="ik_huge",
            ),
            actor=admin_actor,
        )
    assert exc_info.value.status_code == 400
    assert "exceeds 5MB" in str(exc_info.value)


def test_add_product_image_role_permissions(memory_session: Session):
    (
        _,
        _,
        _,
        _,
        catalog_svc,
        m_view,
        p_view,
        _,
    ) = _setup_merchant_and_product(memory_session)

    # EDITOR role can add image
    editor_actor = ActorContext(
        actor_id="ed1",
        actor_type=ActorType.MERCHANT_USER,
        correlation_id="cor_ed",
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.EDITOR]),
    )
    img = catalog_svc.add_product_image(
        AddProductImageCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            filename="editor.png",
            content_type="image/png",
            content=b"editor-bytes",
            sort_order=0,
            idempotency_key="ik_ed",
        ),
        actor=editor_actor,
    )
    assert img.sort_order == 0

    # VIEWER role is denied
    viewer_actor = ActorContext(
        actor_id="view1",
        actor_type=ActorType.MERCHANT_USER,
        correlation_id="cor_view",
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.VIEWER]),
    )
    with pytest.raises(AppError) as exc_info:
        catalog_svc.add_product_image(
            AddProductImageCommand(
                merchant_id=m_view.id,
                product_id=p_view.id,
                filename="viewer.png",
                content_type="image/png",
                content=b"viewer-bytes",
                sort_order=1,
                idempotency_key="ik_view",
            ),
            actor=viewer_actor,
        )
    assert exc_info.value.status_code == 403

    # APPROVER role is denied
    approver_actor = ActorContext(
        actor_id="app1",
        actor_type=ActorType.MERCHANT_USER,
        correlation_id="cor_app",
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.APPROVER]),
    )
    with pytest.raises(AppError) as exc_info:
        catalog_svc.add_product_image(
            AddProductImageCommand(
                merchant_id=m_view.id,
                product_id=p_view.id,
                filename="app.png",
                content_type="image/png",
                content=b"app-bytes",
                sort_order=1,
                idempotency_key="ik_app",
            ),
            actor=approver_actor,
        )
    assert exc_info.value.status_code == 403


def test_add_product_image_cross_tenant_denial(memory_session: Session):
    (
        _,
        _,
        _,
        _,
        catalog_svc,
        m_view,
        p_view,
        _,
    ) = _setup_merchant_and_product(memory_session)

    # Actor belongs to another merchant
    other_actor = ActorContext(
        actor_id="other1",
        actor_type=ActorType.MERCHANT_USER,
        correlation_id="cor_oth",
        merchant_ids=frozenset(["other_merchant_id"]),
        roles=frozenset([MerchantRole.ADMIN]),
    )

    with pytest.raises(AppError) as exc_info:
        catalog_svc.add_product_image(
            AddProductImageCommand(
                merchant_id=m_view.id,
                product_id=p_view.id,
                filename="cross.png",
                content_type="image/png",
                content=b"cross-bytes",
                sort_order=0,
                idempotency_key="ik_cross",
            ),
            actor=other_actor,
        )
    assert exc_info.value.status_code == 403


def test_add_product_image_nonexistent_product(memory_session: Session):
    (
        _,
        _,
        _,
        _,
        catalog_svc,
        m_view,
        _,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    with pytest.raises(AppError) as exc_info:
        catalog_svc.add_product_image(
            AddProductImageCommand(
                merchant_id=m_view.id,
                product_id="prod_nonexistent",
                filename="test.png",
                content_type="image/png",
                content=b"test-bytes",
                sort_order=0,
                idempotency_key="ik_nonex",
            ),
            actor=admin_actor,
        )
    assert exc_info.value.status_code == 404
    assert "Product not found" in str(exc_info.value)


def test_add_product_image_cleanup_on_repo_failure(memory_session: Session):
    (
        _,
        _,
        img_repo,
        storage,
        catalog_svc,
        m_view,
        p_view,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    # Mock img_repo.add to fail after storage upload
    mock_add = MagicMock(side_effect=RuntimeError("DB write failure"))
    img_repo.add = mock_add

    with pytest.raises(RuntimeError, match="DB write failure"):
        catalog_svc.add_product_image(
            AddProductImageCommand(
                merchant_id=m_view.id,
                product_id=p_view.id,
                filename="fail.png",
                content_type="image/png",
                content=b"fail-bytes",
                sort_order=0,
                idempotency_key="ik_fail",
            ),
            actor=admin_actor,
        )

    # Verify storage file was cleaned up and is empty
    assert len(storage._files) == 0


def test_delete_product_image_happy_path(memory_session: Session):
    (
        _,
        _,
        img_repo,
        storage,
        catalog_svc,
        m_view,
        p_view,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    img = catalog_svc.add_product_image(
        AddProductImageCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            filename="del_me.jpg",
            content_type="image/jpeg",
            content=b"del-me-bytes",
            sort_order=0,
            idempotency_key="ik_del1",
        ),
        actor=admin_actor,
    )
    memory_session.commit()

    assert img_repo.count_for_product(m_view.id, p_view.id) == 1
    assert len(storage._files) == 1

    # Delete image
    catalog_svc.delete_product_image(
        DeleteProductImageCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            image_id=img.id,
            idempotency_key="ik_del_cmd",
        ),
        actor=admin_actor,
    )
    memory_session.commit()

    assert img_repo.count_for_product(m_view.id, p_view.id) == 0
    assert len(storage._files) == 0

    # Verify product view now has 0 images
    fetched_p = catalog_svc.get_product(p_view.id, actor=admin_actor)
    assert len(fetched_p.images) == 0


def test_delete_product_image_not_found(memory_session: Session):
    (
        _,
        _,
        _,
        _,
        catalog_svc,
        m_view,
        p_view,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    # Image not found
    with pytest.raises(AppError) as exc_info:
        catalog_svc.delete_product_image(
            DeleteProductImageCommand(
                merchant_id=m_view.id,
                product_id=p_view.id,
                image_id="img_nonexistent",
                idempotency_key="ik_del_missing",
            ),
            actor=admin_actor,
        )
    assert exc_info.value.status_code == 404
    assert "Product image not found" in str(exc_info.value)

    # Product not found
    with pytest.raises(AppError) as exc_info:
        catalog_svc.delete_product_image(
            DeleteProductImageCommand(
                merchant_id=m_view.id,
                product_id="prod_missing",
                image_id="img_any",
                idempotency_key="ik_del_missing_p",
            ),
            actor=admin_actor,
        )
    assert exc_info.value.status_code == 404
    assert "Product not found" in str(exc_info.value)


def test_delete_product_image_role_denial(memory_session: Session):
    (
        _,
        _,
        _,
        _,
        catalog_svc,
        m_view,
        p_view,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    img = catalog_svc.add_product_image(
        AddProductImageCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            filename="locked.jpg",
            content_type="image/jpeg",
            content=b"locked-bytes",
            sort_order=0,
            idempotency_key="ik_lock",
        ),
        actor=admin_actor,
    )
    memory_session.commit()

    viewer_actor = ActorContext(
        actor_id="viewer1",
        actor_type=ActorType.MERCHANT_USER,
        correlation_id="cor_v",
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.VIEWER]),
    )

    with pytest.raises(AppError) as exc_info:
        catalog_svc.delete_product_image(
            DeleteProductImageCommand(
                merchant_id=m_view.id,
                product_id=p_view.id,
                image_id=img.id,
                idempotency_key="ik_del_v",
            ),
            actor=viewer_actor,
        )
    assert exc_info.value.status_code == 403


def test_service_unconfigured_storage_raises_500(memory_session: Session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    bare_svc = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(
        actor_id="sys1",
        actor_type=ActorType.SYSTEM,
        correlation_id="cor1",
    )
    m = bare_svc.create_merchant(
        CreateMerchantCommand(name="Bare Corp", idempotency_key="ik_b1"),
        actor=sys_actor,
    )
    admin_actor = ActorContext(
        actor_id="adm",
        actor_type=ActorType.MERCHANT_USER,
        correlation_id="cor2",
        merchant_ids=frozenset([m.id]),
        roles=frozenset([MerchantRole.ADMIN]),
    )
    p = bare_svc.create_product(
        CreateProductCommand(
            merchant_id=m.id,
            sku="BARE-1",
            title="Bare Product",
            description="No image service",
            price=Money(amount_minor=1000, currency="USD"),
            available_quantity=5,
            idempotency_key="ik_bp1",
        ),
        actor=admin_actor,
    )
    memory_session.commit()

    # Calling add_product_image without storage_svc or image_repo raises 500
    with pytest.raises(AppError) as exc_info:
        bare_svc.add_product_image(
            AddProductImageCommand(
                merchant_id=m.id,
                product_id=p.id,
                filename="test.png",
                content_type="image/png",
                content=b"test",
                sort_order=0,
                idempotency_key="ik_bare_img",
            ),
            actor=admin_actor,
        )
    assert exc_info.value.status_code == 500

    # Calling delete_product_image without storage_svc or image_repo raises 500
    with pytest.raises(AppError) as exc_info:
        bare_svc.delete_product_image(
            DeleteProductImageCommand(
                merchant_id=m.id,
                product_id=p.id,
                image_id="img_123",
                idempotency_key="ik_bare_del",
            ),
            actor=admin_actor,
        )
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Integration with Buyer Catalog & Lifecycle Actions
# ---------------------------------------------------------------------------


def test_images_preserved_across_product_lifecycle(memory_session: Session):
    (
        _,
        _,
        _,
        _,
        catalog_svc,
        m_view,
        p_view,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    # Add 2 images
    img1 = catalog_svc.add_product_image(
        AddProductImageCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            filename="img0.jpg",
            content_type="image/jpeg",
            content=b"img0",
            sort_order=0,
            idempotency_key="ik_0",
        ),
        actor=admin_actor,
    )
    img2 = catalog_svc.add_product_image(
        AddProductImageCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            filename="img1.jpg",
            content_type="image/jpeg",
            content=b"img1",
            sort_order=1,
            idempotency_key="ik_1",
        ),
        actor=admin_actor,
    )
    memory_session.commit()

    # 1. Update product: images should still be present in view
    updated_p = catalog_svc.update_product(
        UpdateProductCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            expected_version=p_view.version,
            title="Updated Title",
            idempotency_key="ik_upd",
        ),
        actor=admin_actor,
    )
    memory_session.commit()
    assert len(updated_p.images) == 2
    assert updated_p.images[0].id == img1.id
    assert updated_p.images[1].id == img2.id

    # 2. Publish product: images present
    pub_p = catalog_svc.publish_product(
        SetProductPublicationCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            expected_version=updated_p.version,
            idempotency_key="ik_pub",
        ),
        actor=admin_actor,
    )
    memory_session.commit()
    assert len(pub_p.images) == 2

    # 3. List products: images present
    page = catalog_svc.list_products(merchant_id=m_view.id, actor=admin_actor)
    assert len(page.items) == 1
    assert len(page.items[0].images) == 2

    # 4. Unpublish product: images present
    unpub_p = catalog_svc.unpublish_product(
        SetProductPublicationCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            expected_version=pub_p.version,
            idempotency_key="ik_unpub",
        ),
        actor=admin_actor,
    )
    memory_session.commit()
    assert len(unpub_p.images) == 2


def test_buyer_catalog_service_images(memory_session: Session):
    (
        _,
        p_repo,
        img_repo,
        _,
        merchant_svc,
        m_view,
        p_view,
        admin_actor,
    ) = _setup_merchant_and_product(memory_session)

    # Add images to product
    merchant_svc.add_product_image(
        AddProductImageCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            filename="buyer_view.png",
            content_type="image/png",
            content=b"buyer-view-bytes",
            alt_text="Front Graphic",
            sort_order=0,
            idempotency_key="ik_b_img",
        ),
        actor=admin_actor,
    )
    # Publish product
    merchant_svc.publish_product(
        SetProductPublicationCommand(
            merchant_id=m_view.id,
            product_id=p_view.id,
            expected_version=p_view.version,
            idempotency_key="ik_pub_b",
        ),
        actor=admin_actor,
    )
    memory_session.commit()

    buyer_svc = ApplicationCatalogService(product_repo=p_repo, image_repo=img_repo)
    buyer_actor = ActorContext(
        actor_id="buyer1",
        actor_type=ActorType.BUYER,
        correlation_id="cor_buyer",
    )

    # Buyer get_product
    prod = buyer_svc.get_product(
        merchant_id=m_view.id,
        product_id=p_view.id,
        actor=buyer_actor,
    )
    assert len(prod.images) == 1
    assert prod.images[0].alt_text == "Front Graphic"
    assert prod.images[0].sort_order == 0
    assert "https://cdn.example.com/" in prod.images[0].url

    # Buyer search
    search_res = buyer_svc.search(
        CatalogSearchQuery(
            merchant_id=m_view.id,
            query="Widget",
        ),
        actor=buyer_actor,
    )
    assert len(search_res.items) == 1
    assert len(search_res.items[0].images) == 1
    assert search_res.items[0].images[0].alt_text == "Front Graphic"
