import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from ai_commerce_gateway.infrastructure.database.models import (
    Base,
    Buyer,
    Merchant,
    MerchantPolicy,
    MerchantUser,
    Product,
)

database_url = os.getenv("DATABASE_URL", "sqlite:///e2e_test.db")
parsed_url = make_url(database_url)
if parsed_url.drivername != "sqlite" or parsed_url.database is None:
    raise RuntimeError("The E2E seed script only accepts a dedicated SQLite database.")
if os.path.basename(parsed_url.database) != "e2e_test.db":
    raise RuntimeError("Refusing to reset a SQLite database not named e2e_test.db.")

engine = create_engine(database_url)
Base.metadata.drop_all(engine)  # Start fresh every time.
Base.metadata.create_all(engine)

with Session(engine) as session:
    # 1. Create Demo Merchant
    merchant = Merchant(id="mer_demo", name="Demo Merchant")

    # 2. Create User for merchant
    merchant_user = MerchantUser(
        id="mu_001",
        user_id="user_1",
        merchant_id="mer_demo",
        role="ADMIN",
    )

    # 2b. Create Demo Buyer (required: proposal creation enforces buyer_is_active)
    buyer = Buyer(id="buyer_1", external_identity="ext_buyer_1", status="ACTIVE")

    # 3. Create Policy for merchant (required for proposals)
    policy = MerchantPolicy(
        id="pol_001",
        merchant_id="mer_demo",
        mode="AUTO_BELOW_LIMIT",
        auto_accept_max_minor=200000,
        currency="INR",
        version=1,
    )

    # 4. Create Product (coffee maker for the E2E test)
    product = Product(
        id="prod_001",
        merchant_id="mer_demo",
        sku="SKU-COFFEE",
        title="Premium Coffee Maker",
        description="A premium coffee maker that brews delicious coffee.",
        category="Home & Kitchen",
        price_minor=100000,  # INR 1000.00
        currency="INR",
        available_quantity=50,
        status="PUBLISHED",
        version=1,
    )

    session.add_all([merchant, merchant_user, buyer, policy, product])
    session.commit()

print("E2E database seeded successfully at e2e_test.db")
