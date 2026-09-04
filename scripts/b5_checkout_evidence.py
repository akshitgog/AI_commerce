#!/usr/bin/env python3
"""B5 Checkout Evidence Harness — self-contained Test Mode payment proof.

Usage:
    1. Set env vars RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET (or config/local.yaml)
    2. uv run python scripts/b5_checkout_evidence.py
    3. Open http://localhost:8000/checkout in your browser
    4. Complete payment with test card 4111 1111 1111 1111, any CVV, any future expiry
    5. Observe SUCCEEDED evidence in the browser and console

No webhook, ngrok, PostgreSQL, or interactive configuration required.
"""

from __future__ import annotations

import os
import sys
import textwrap
from datetime import UTC, datetime, timedelta

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker

# Adjust path so we can import from the project
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ai_commerce_gateway.application.provider_verification import (
    ProviderVerificationApplicationService,
)
from ai_commerce_gateway.contracts.models import (
    CreateProviderOrderCommand,
    Money,
    VerifyCheckoutCommand,
)
from ai_commerce_gateway.infrastructure.database import models
from ai_commerce_gateway.infrastructure.database.provider_verification import (
    SqlAlchemyVerificationUnitOfWork,
)
from ai_commerce_gateway.providers.razorpay import RazorpayAdapter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AMOUNT_MINOR = 100  # INR 1.00 — minimum Razorpay test amount
CURRENCY = "INR"
HARNESS_PORT = 8000

# Try env vars first, fall back to config/local.yaml
KEY_ID = os.getenv("RAZORPAY_KEY_ID")
KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not KEY_ID or not KEY_SECRET:
    try:
        from ai_commerce_gateway.core.config import get_settings
        settings = get_settings()
        KEY_ID = settings.razorpay_key_id
        KEY_SECRET = (
            settings.razorpay_key_secret.get_secret_value()
            if settings.razorpay_key_secret
            else None
        )
    except Exception:
        pass

if not KEY_ID or not KEY_SECRET:
    print("ERROR: Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET env vars or config/local.yaml")
    sys.exit(1)

assert KEY_ID.startswith("rzp_test_"), "Only Test Mode keys are accepted"

# ---------------------------------------------------------------------------
# SQLite database with full schema
# ---------------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(__file__), "..", ".b5_evidence.db")
DB_URL = f"sqlite:///{os.path.abspath(DB_PATH)}"

engine = create_engine(DB_URL, echo=False)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_conn, _):  # type: ignore[no-untyped-def]
    dbapi_conn.execute("PRAGMA foreign_keys=ON")
    dbapi_conn.execute("PRAGMA journal_mode=WAL")


models.Base.metadata.create_all(engine)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

# ---------------------------------------------------------------------------
# Seed minimal prerequisite records
# ---------------------------------------------------------------------------

MERCHANT_ID = "merch_b5_evidence"
BUYER_ID = "buyer_b5_evidence"
PRODUCT_ID = "prod_b5_evidence"
PROPOSAL_ID = "prop_b5_evidence"
TRANSACTION_ID = "txn_b5_evidence"
ATTEMPT_ID = "pay_b5_evidence"

now = datetime.now(UTC)
far_future = now + timedelta(days=30)


def _seed() -> None:
    with SessionFactory() as session:
        if session.get(models.Transaction, TRANSACTION_ID) is not None:
            # Already seeded from a previous run — drop and recreate
            session.close()
            models.Base.metadata.drop_all(engine)
            models.Base.metadata.create_all(engine)
            session2 = SessionFactory()
        else:
            session2 = session

        with session2:
            session2.add(models.Merchant(id=MERCHANT_ID, name="B5 Evidence Merchant"))
            session2.add(
                models.Buyer(id=BUYER_ID, external_identity="b5-evidence-buyer")
            )
            session2.add(
                models.Product(
                    id=PRODUCT_ID,
                    merchant_id=MERCHANT_ID,
                    sku="B5-TEST",
                    title="B5 Evidence Product",
                    description="Test product for B5 checkout evidence",
                    price_minor=AMOUNT_MINOR,
                    currency=CURRENCY,
                    available_quantity=100,
                    status="PUBLISHED",
                    version=1,
                )
            )
            session2.add(
                models.PurchaseProposal(
                    id=PROPOSAL_ID,
                    buyer_id=BUYER_ID,
                    merchant_id=MERCHANT_ID,
                    product_id=PRODUCT_ID,
                    product_version=1,
                    quantity=1,
                    unit_price_minor=AMOUNT_MINOR,
                    total_minor=AMOUNT_MINOR,
                    currency=CURRENCY,
                    proposal_hash="sha256:b5-evidence-hash",
                    status="ACCEPTED",
                    expires_at=far_future,
                )
            )
            session2.commit()


_seed()

# ---------------------------------------------------------------------------
# Create real Razorpay order
# ---------------------------------------------------------------------------

adapter = RazorpayAdapter(key_id=KEY_ID, key_secret=KEY_SECRET)

unique = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
order_command = CreateProviderOrderCommand(
    transaction_id=TRANSACTION_ID,
    attempt_id=ATTEMPT_ID,
    amount=Money(amount_minor=AMOUNT_MINOR, currency=CURRENCY),
    receipt=TRANSACTION_ID[:40],
    request_fingerprint=f"sha256:b5-evidence-{unique}",
)
observation = adapter.create_order(order_command)
checkout_options = adapter.build_checkout_options(
    order_command, observation, description="B5 Test Mode evidence"
)

print(f"\n✓ Razorpay Test Mode order created: ...{observation.provider_order_id[-6:]}")
print(f"  State: {observation.provider_order_state}")
print(f"  Amount: {AMOUNT_MINOR} {CURRENCY}")

# ---------------------------------------------------------------------------
# Seed transaction and payment attempt with real order ID
# ---------------------------------------------------------------------------

with SessionFactory() as session:
    session.add(
        models.Transaction(
            id=TRANSACTION_ID,
            proposal_id=PROPOSAL_ID,
            merchant_id=MERCHANT_ID,
            buyer_id=BUYER_ID,
            amount_minor=AMOUNT_MINOR,
            currency=CURRENCY,
            state="PAYMENT_PENDING",
        )
    )
    session.add(
        models.PaymentAttempt(
            id=ATTEMPT_ID,
            transaction_id=TRANSACTION_ID,
            attempt_number=1,
            provider="razorpay",
            provider_request_fingerprint=f"sha256:b5-{unique}",
            provider_order_id=observation.provider_order_id,
            provider_order_state="created",
        )
    )
    session.commit()

print(f"✓ Transaction {TRANSACTION_ID} seeded in PAYMENT_PENDING with order ...{observation.provider_order_id[-6:]}")

# ---------------------------------------------------------------------------
# Wire the real verification service
# ---------------------------------------------------------------------------


def _uow_factory() -> SqlAlchemyVerificationUnitOfWork:
    return SqlAlchemyVerificationUnitOfWork(SessionFactory)


verification_service = ProviderVerificationApplicationService(
    unit_of_work_factory=_uow_factory,
    provider_service=adapter,
)

# ---------------------------------------------------------------------------
# FastAPI harness
# ---------------------------------------------------------------------------

app = FastAPI(title="B5 Checkout Evidence Harness")

CHECKOUT_HTML = textwrap.dedent(f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>B5 Test Mode Checkout</title>
  <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
  <style>
    body {{ font-family: system-ui; max-width: 640px; margin: 60px auto; }}
    #result {{ margin-top: 20px; padding: 16px; border-radius: 8px; white-space: pre-wrap;
               font-family: monospace; font-size: 14px; }}
    .success {{ background: #d4edda; border: 1px solid #28a745; }}
    .error {{ background: #f8d7da; border: 1px solid #dc3545; }}
    .pending {{ background: #fff3cd; border: 1px solid #ffc107; }}
    button {{ padding: 12px 24px; font-size: 16px; cursor: pointer;
             background: #528ff0; color: white; border: none; border-radius: 6px; }}
    button:hover {{ background: #3d6fd0; }}
  </style>
</head>
<body>
  <h1>B5 Test Mode Checkout</h1>
  <p>Amount: ₹{AMOUNT_MINOR / 100:.2f} ({CURRENCY})</p>
  <p>Order: ...{observation.provider_order_id[-6:]}</p>
  <p>Transaction: {TRANSACTION_ID}</p>
  <button onclick="openCheckout()">Pay with Test Card</button>
  <p style="color: #666; font-size: 13px; margin-top: 8px;">
    Use card <b>4111 1111 1111 1111</b>, any future expiry, any CVV
  </p>
  <div id="result" class="pending" style="display:none;"></div>

  <script>
    function openCheckout() {{
      var options = {{
        key: "{checkout_options.key}",
        amount: {checkout_options.amount},
        currency: "{checkout_options.currency}",
        order_id: "{checkout_options.order_id}",
        name: "{checkout_options.name}",
        description: "B5 Test Mode evidence",
        handler: function(response) {{
          document.getElementById("result").style.display = "block";
          document.getElementById("result").className = "pending";
          document.getElementById("result").textContent =
            "Checkout complete. Verifying with server...\\n" +
            "order: ..." + response.razorpay_order_id.slice(-6) + "\\n" +
            "payment: ..." + response.razorpay_payment_id.slice(-6);

          fetch("/verify", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              transaction_id: "{TRANSACTION_ID}",
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature
            }})
          }})
          .then(r => r.json())
          .then(data => {{
            var el = document.getElementById("result");
            el.style.display = "block";
            if (data.state === "SUCCEEDED") {{
              el.className = "success";
              el.textContent = "✓ PLATFORM SUCCEEDED\\n" + JSON.stringify(data, null, 2);
            }} else {{
              el.className = "error";
              el.textContent = "State: " + (data.state || "error") + "\\n" + JSON.stringify(data, null, 2);
            }}
          }})
          .catch(err => {{
            var el = document.getElementById("result");
            el.style.display = "block";
            el.className = "error";
            el.textContent = "Verification error: " + err.message;
          }});
        }},
        modal: {{ ondismiss: function() {{
          document.getElementById("result").style.display = "block";
          document.getElementById("result").className = "error";
          document.getElementById("result").textContent = "Checkout dismissed by user.";
        }}}}
      }};
      var rzp = new Razorpay(options);
      rzp.open();
    }}
  </script>
</body>
</html>
""")


@app.get("/checkout", response_class=HTMLResponse)
def checkout_page() -> str:
    return CHECKOUT_HTML


@app.post("/verify")
def verify_checkout(request_data: dict) -> dict:  # type: ignore[type-arg]
    """Verify checkout callback through the real B5 verification pipeline."""
    try:
        command = VerifyCheckoutCommand(
            transaction_id=request_data["transaction_id"],
            provider_order_id=request_data["razorpay_order_id"],
            provider_payment_id=request_data["razorpay_payment_id"],
            signature=request_data["razorpay_signature"],
        )
        result = verification_service.verify_checkout(
            command, correlation_id=f"b5-evidence-{unique}"
        )
        result_dict = result.model_dump(mode="json")

        # Log redacted evidence to console
        print("\n" + "=" * 60)
        print("B5 CHECKOUT VERIFICATION EVIDENCE")
        print("=" * 60)
        print(f"  Transaction:     {result.id}")
        print(f"  State:           {result.state.value}")
        print(f"  Amount:          {result.amount.amount_minor} {result.amount.currency}")
        if result.provider_phase:
            print(f"  Order state:     {result.provider_phase.order_state}")
            print(f"  Payment state:   {result.provider_phase.payment_state}")
            print(f"  Capture state:   {result.provider_phase.capture_state}")
            print(f"  Last verified:   {result.provider_phase.last_verified_at}")
        print(f"  Order ID:        ...{request_data['razorpay_order_id'][-6:]}")
        print(f"  Payment ID:      ...{request_data['razorpay_payment_id'][-6:]}")
        print(f"  Signature:       {request_data['razorpay_signature'][:8]}...{request_data['razorpay_signature'][-4:]}")
        print("=" * 60)

        # Query and print audit events
        with SessionFactory() as session:
            events = list(
                session.execute(
                    select(models.TransactionEvent)
                    .where(models.TransactionEvent.transaction_id == TRANSACTION_ID)
                    .order_by(models.TransactionEvent.created_at)
                ).scalars()
            )
            print(f"\n  Audit trail ({len(events)} events):")
            for evt in events:
                print(f"    {evt.previous_state} → {evt.new_state}  [{evt.reason_code}]  ref={evt.provider_reference_redacted}")

        print("\n✓ B5 evidence complete. Copy the above to docs/RAZORPAY_TEST_MODE.md")
        print("  Remember: do NOT commit credentials, full order/payment IDs, or raw signatures.\n")

        return result_dict

    except Exception as exc:
        print(f"\n✗ Verification failed: {exc}")
        return JSONResponse(
            status_code=400,
            content={"error": str(exc), "state": "FAILED"},
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"\n→ Open http://localhost:{HARNESS_PORT}/checkout in your browser")
    print("  Use test card 4111 1111 1111 1111, any future expiry, any CVV\n")
    uvicorn.run(app, host="127.0.0.1", port=HARNESS_PORT, log_level="warning")
